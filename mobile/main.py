"""
Main entry point for RamilConnect KivyMD Android Application.
"""
import os
import json
import threading
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.utils import get_color_from_hex
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.snackbar import Snackbar

# Import our API client and KV definitions
from api import api
from kv_ui import KV


class ChatBubble(MDCard):
    """Custom widget for chat messages."""
    def __init__(self, text, is_user=True, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.size_hint_x = 0.8
        self.padding = "12dp"
        self.radius = [20, 20, (0 if is_user else 20), (20 if is_user else 0)]
        self.md_bg_color = get_color_from_hex("#e84393" if is_user else "#1a1a2e")
        self.pos_hint = {"right": 1} if is_user else {"x": 0}

        self.label = MDLabel(
            text=text,
            theme_text_color="Custom",
            text_color=get_color_from_hex("#ffffff" if is_user else "#e8e8f0"),
            size_hint_y=None,
        )
        self.label.bind(texture_size=self.update_height)
        self.add_widget(self.label)

    def update_height(self, instance, value):
        self.label.height = value[1]
        self.height = value[1] + dp(24)


class RamilConnectApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Pink"
        self.theme_cls.primary_hue = "500"
        return Builder.load_string(KV)

    def on_start(self):
        # We could try loading cached tokens here
        pass

    def show_error(self, message):
        Snackbar(
            text=message,
            snackbar_x="10dp",
            snackbar_y="10dp",
            bg_color=get_color_from_hex("#ff7675")
        ).open()

    def do_login(self, email, password):
        if not email or not password:
            self.show_error("Please fill in all fields")
            return

        def login_thread():
            try:
                result = api.login(email, password)
                if "user" in result:
                    Clock.schedule_once(lambda dt: self.on_login_success())
                else:
                    Clock.schedule_once(lambda dt: self.show_error("Login failed"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_error(str(e)))
                
        threading.Thread(target=login_thread, daemon=True).start()

    def do_register(self, name, email, password):
        if not name or not email or not password:
            self.show_error("Please fill in all fields")
            return

        def register_thread():
            try:
                result = api.register(name, email, password)
                if "user" in result:
                    Clock.schedule_once(lambda dt: self.on_login_success())
                else:
                    Clock.schedule_once(lambda dt: self.show_error("Registration failed"))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_error(str(e)))
                
        threading.Thread(target=register_thread, daemon=True).start()

    def on_login_success(self):
        self.root.current = 'chat'
        self.load_chat_history()
        self.load_profile()

    def load_profile(self):
        def fetch_profile():
            try:
                profile = api.get_profile()
                stats = api.get_stats()
                Clock.schedule_once(lambda dt: self.update_profile_ui(profile, stats))
            except Exception:
                pass
        threading.Thread(target=fetch_profile, daemon=True).start()

    def update_profile_ui(self, profile, stats):
        screen = self.root.get_screen('profile')
        screen.ids.profile_name.text = profile.get("name", "User")
        
        stat_text = (
            f"Total Messages: {stats.get('total_messages', 0)}\n"
            f"Chat Streak: {stats.get('streak_days', 0)} days\n"
            f"Persona: {profile.get('companion_persona', 'Unknown')}"
        )
        screen.ids.profile_stats.text = stat_text

    def load_chat_history(self):
        def fetch_history():
            try:
                history = api.get_history()
                Clock.schedule_once(lambda dt: self.populate_chat(history.get("messages", [])))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.show_error("Failed to load history"))
        threading.Thread(target=fetch_history, daemon=True).start()

    def populate_chat(self, messages):
        chat_list = self.root.get_screen('chat').ids.chat_list
        chat_list.clear_widgets()
        # Messages come in reverse chronological, so reverse again for UI
        for msg in reversed(messages):
            is_user = msg["role"] == "user"
            chat_list.add_widget(ChatBubble(text=msg["content"], is_user=is_user))
        
        self.scroll_to_bottom()

    def send_message(self, content):
        if not content.strip():
            return
            
        screen = self.root.get_screen('chat')
        screen.ids.msg_input.text = ""
        
        # Add user message immediately
        chat_list = screen.ids.chat_list
        chat_list.add_widget(ChatBubble(text=content, is_user=True))
        self.scroll_to_bottom()

        # Add empty AI bubble to fill via SSE
        ai_bubble = ChatBubble(text="...", is_user=False)
        chat_list.add_widget(ai_bubble)
        self.scroll_to_bottom()

        def stream_thread():
            try:
                response = api.send_message(content)
                full_text = ""
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            data = json.loads(data_str)
                            
                            if "error" in data:
                                Clock.schedule_once(lambda dt, err=data["error"]: self.update_bubble(ai_bubble, f"Error: {err}"))
                                break
                            
                            if "done" in data and data["done"]:
                                break
                                
                            if "content" in data:
                                full_text += data["content"]
                                # Update UI from main thread
                                Clock.schedule_once(lambda dt, text=full_text: self.update_bubble(ai_bubble, text))
            except Exception as e:
                Clock.schedule_once(lambda dt: self.update_bubble(ai_bubble, "Network error"))

        threading.Thread(target=stream_thread, daemon=True).start()

    def update_bubble(self, bubble, text):
        bubble.label.text = text
        self.scroll_to_bottom()

    def scroll_to_bottom(self, *args):
        scroll_view = self.root.get_screen('chat').ids.scroll_view
        scroll_view.scroll_y = 0

    def do_logout(self):
        api.access_token = None
        api.refresh_token = None
        self.root.current = 'login'


if __name__ == '__main__':
    RamilConnectApp().run()
