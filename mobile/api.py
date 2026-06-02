"""
API Client for RamilConnect Backend.

Handles HTTP requests, JWT token management, and authentication state.
"""
import requests
import json
from typing import Dict, Any, Optional

class APIClient:
    def __init__(self, base_url: str = "http://10.0.2.2:8080/api"):
        # Default to Android emulator localhost (10.0.2.2 maps to host 127.0.0.1)
        self.base_url = base_url
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_data: Optional[Dict[str, Any]] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def set_tokens(self, access: str, refresh: str) -> None:
        self.access_token = access
        self.refresh_token = refresh

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Login and store tokens."""
        response = requests.post(
            f"{self.base_url}/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        if response.status_code == 200:
            self.set_tokens(data["tokens"]["access_token"], data["tokens"]["refresh_token"])
            self.user_data = data["user"]
        return data

    def register(self, name: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user."""
        response = requests.post(
            f"{self.base_url}/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
                "dob": "2000-01-01",  # Defaults for basic registration
                "gender": "prefer_not_to_say"
            },
            headers={"Content-Type": "application/json"}
        )
        data = response.json()
        if response.status_code == 201:
            self.set_tokens(data["tokens"]["access_token"], data["tokens"]["refresh_token"])
            self.user_data = data["user"]
        return data

    def get_profile(self) -> Dict[str, Any]:
        """Fetch the current user profile."""
        response = requests.get(
            f"{self.base_url}/user/profile",
            headers=self._get_headers()
        )
        if response.status_code == 200:
            self.user_data = response.json()
        return response.json()

    def send_message(self, content: str) -> requests.Response:
        """
        Send a message and get the SSE stream response.
        Returns the raw requests.Response object for streaming.
        """
        response = requests.post(
            f"{self.base_url}/companion/message",
            json={"content": content},
            headers=self._get_headers(),
            stream=True
        )
        return response

    def get_history(self) -> Dict[str, Any]:
        """Get chat history."""
        response = requests.get(
            f"{self.base_url}/companion/history",
            headers=self._get_headers()
        )
        return response.json()

    def get_stats(self) -> Dict[str, Any]:
        """Get companion stats."""
        response = requests.get(
            f"{self.base_url}/companion/stats",
            headers=self._get_headers()
        )
        return response.json()

# Global API client instance
api = APIClient()
