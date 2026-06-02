"""
Main UI definitions (KV lang) for RamilConnect Kivy App.
"""

KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

ScreenManager:
    LoginScreen:
    RegisterScreen:
    ChatScreen:
    ProfileScreen:

<LoginScreen@MDScreen>:
    name: 'login'
    md_bg_color: get_color_from_hex("#0f0f1a")

    MDBoxLayout:
        orientation: 'vertical'
        padding: "24dp"
        spacing: "24dp"
        pos_hint: {"center_x": .5, "center_y": .5}
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "💖"
            halign: "center"
            font_size: "48sp"
            size_hint_y: None
            height: self.texture_size[1]

        MDLabel:
            text: "RamilConnect"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("#e8e8f0")
            bold: True
            size_hint_y: None
            height: self.texture_size[1]

        MDLabel:
            text: "Your AI Soulmate Companion"
            halign: "center"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("#a0a0c0")
            size_hint_y: None
            height: self.texture_size[1]
            
        Widget:
            size_hint_y: None
            height: "16dp"

        MDTextField:
            id: email_field
            hint_text: "Email"
            icon_right: "email"
            mode: "rectangle"
            text_color_normal: get_color_from_hex("#e8e8f0")
            hint_text_color_normal: get_color_from_hex("#6a6a8a")

        MDTextField:
            id: password_field
            hint_text: "Password"
            icon_right: "eye-off"
            mode: "rectangle"
            password: True
            text_color_normal: get_color_from_hex("#e8e8f0")
            hint_text_color_normal: get_color_from_hex("#6a6a8a")

        MDRaisedButton:
            text: "LOG IN"
            pos_hint: {"center_x": .5}
            size_hint_x: 1
            md_bg_color: get_color_from_hex("#e84393")
            on_release: app.do_login(email_field.text, password_field.text)

        MDFlatButton:
            text: "Don't have an account? Sign up"
            pos_hint: {"center_x": .5}
            theme_text_color: "Custom"
            text_color: get_color_from_hex("#6c5ce7")
            on_release: app.root.current = 'register'


<RegisterScreen@MDScreen>:
    name: 'register'
    md_bg_color: get_color_from_hex("#0f0f1a")

    MDBoxLayout:
        orientation: 'vertical'
        padding: "24dp"
        spacing: "16dp"
        pos_hint: {"center_x": .5, "center_y": .5}
        size_hint_y: None
        height: self.minimum_height

        MDLabel:
            text: "Create Account"
            halign: "center"
            font_style: "H4"
            theme_text_color: "Custom"
            text_color: get_color_from_hex("#e8e8f0")
            bold: True
            size_hint_y: None
            height: self.texture_size[1]

        MDTextField:
            id: reg_name_field
            hint_text: "Name"
            icon_right: "account"
            mode: "rectangle"

        MDTextField:
            id: reg_email_field
            hint_text: "Email"
            icon_right: "email"
            mode: "rectangle"

        MDTextField:
            id: reg_password_field
            hint_text: "Password"
            icon_right: "eye-off"
            mode: "rectangle"
            password: True

        MDRaisedButton:
            text: "SIGN UP"
            pos_hint: {"center_x": .5}
            size_hint_x: 1
            md_bg_color: get_color_from_hex("#e84393")
            on_release: app.do_register(reg_name_field.text, reg_email_field.text, reg_password_field.text)

        MDFlatButton:
            text: "Already have an account? Log in"
            pos_hint: {"center_x": .5}
            theme_text_color: "Custom"
            text_color: get_color_from_hex("#6c5ce7")
            on_release: app.root.current = 'login'


<ChatScreen@MDScreen>:
    name: 'chat'
    md_bg_color: get_color_from_hex("#0f0f1a")

    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Companion"
            anchor_title: "left"
            md_bg_color: get_color_from_hex("#16213e")
            specific_text_color: get_color_from_hex("#e8e8f0")
            left_action_items: [["account-circle", lambda x: setattr(app.root, 'current', 'profile')]]
            right_action_items: [["refresh", lambda x: app.load_chat_history()]]

        ScrollView:
            id: scroll_view
            do_scroll_x: False
            MDBoxLayout:
                id: chat_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "16dp"
                spacing: "12dp"

        MDBoxLayout:
            size_hint_y: None
            height: "60dp"
            padding: ["8dp", "8dp", "8dp", "8dp"]
            spacing: "8dp"
            md_bg_color: get_color_from_hex("#16213e")

            MDTextField:
                id: msg_input
                hint_text: "Message..."
                mode: "round"
                fill_color_normal: get_color_from_hex("#1a1a2e")
                on_text_validate: app.send_message(msg_input.text)

            MDIconButton:
                icon: "send"
                theme_text_color: "Custom"
                text_color: get_color_from_hex("#e84393")
                on_release: app.send_message(msg_input.text)


<ProfileScreen@MDScreen>:
    name: 'profile'
    md_bg_color: get_color_from_hex("#0f0f1a")

    MDBoxLayout:
        orientation: 'vertical'

        MDTopAppBar:
            title: "Profile"
            anchor_title: "left"
            md_bg_color: get_color_from_hex("#16213e")
            specific_text_color: get_color_from_hex("#e8e8f0")
            left_action_items: [["arrow-left", lambda x: setattr(app.root, 'current', 'chat')]]

        ScrollView:
            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: "24dp"
                spacing: "16dp"

                MDLabel:
                    id: profile_name
                    text: "User Name"
                    font_style: "H5"
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("#e8e8f0")
                    halign: "center"
                    size_hint_y: None
                    height: self.texture_size[1]

                MDLabel:
                    id: profile_stats
                    text: "Stats loading..."
                    theme_text_color: "Custom"
                    text_color: get_color_from_hex("#a0a0c0")
                    halign: "center"
                    size_hint_y: None
                    height: self.texture_size[1]

                Widget:
                    size_hint_y: None
                    height: "24dp"

                MDRaisedButton:
                    text: "LOGOUT"
                    pos_hint: {"center_x": .5}
                    md_bg_color: get_color_from_hex("#ff7675")
                    on_release: app.do_logout()
'''
