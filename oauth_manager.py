import os
import secrets
import hashlib
import base64
from typing import Tuple, Dict
import requests


class AnthropicOAuthManager:
    """Manages Anthropic Console OAuth 2.0 flow with PKCE."""

    # Anthropic Console OAuth endpoints
    AUTH_URL = "https://console.anthropic.com/oauth/authorize"
    TOKEN_URL = "https://console.anthropic.com/v1/oauth/token"
    API_KEY_CREATE_URL = "https://console.anthropic.com/api/v1/api_keys"

    # OAuth configuration
    CLIENT_ID = os.environ.get("ANTHROPIC_OAUTH_CLIENT_ID")
    REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "http://localhost:5000/oauth/callback")
    SCOPES = ["org:create_api_key"]  # Required scope for API key creation

    @staticmethod
    def generate_pkce_params() -> Tuple[str, str]:
        """Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate code_verifier (43-128 chars, base64url)
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')

        # Generate code_challenge = base64url(sha256(verifier))
        challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')

        return code_verifier, code_challenge

    @staticmethod
    def generate_state() -> str:
        """Generate random state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """Build authorization URL with PKCE challenge.

        Args:
            state: Random state for CSRF protection
            code_challenge: PKCE code challenge

        Returns:
            Full authorization URL to redirect user to
        """
        params = {
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(self.SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        query_string = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        return f"{self.AUTH_URL}?{query_string}"

    def exchange_code_for_token(self, code: str, code_verifier: str) -> Dict:
        """Exchange authorization code for access token.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            Dict with access_token, refresh_token, expires_in

        Raises:
            requests.HTTPError: If token exchange fails
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.CLIENT_ID,
            "redirect_uri": self.REDIRECT_URI,
            "code_verifier": code_verifier,
        }

        response = requests.post(
            self.TOKEN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()

    def create_api_key(self, access_token: str, key_name: str = "MTG Tagger") -> str:
        """Create a permanent API key using the access token.

        Args:
            access_token: OAuth access token
            key_name: Name for the created API key

        Returns:
            The created API key string

        Raises:
            requests.HTTPError: If API key creation fails
        """
        response = requests.post(
            self.API_KEY_CREATE_URL,
            json={"name": key_name},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        return data.get("key")

    def refresh_access_token(self, refresh_token: str) -> Dict:
        """Refresh an expired access token.

        Args:
            refresh_token: Refresh token from previous token exchange

        Returns:
            Dict with new access_token, refresh_token, expires_in

        Raises:
            requests.HTTPError: If refresh fails
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.CLIENT_ID,
        }

        response = requests.post(
            self.TOKEN_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()
