"""
Utility functions for tools.

Common helpers for:
- Environment variable loading
- Error handling and logging
- API interactions
- File operations
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    return env_path.exists()


def get_api_key(key_name: str) -> str:
    """
    Get an API key from environment variables.

    Args:
        key_name: The environment variable name

    Returns:
        The API key value

    Raises:
        ValueError: If the key is not found
    """
    load_env()
    value = os.getenv(key_name)
    if not value:
        raise ValueError(f"Missing environment variable: {key_name}")
    return value


PROJECT_ROOT = Path(__file__).parent.parent
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]


def load_style() -> dict:
    """Load the brand/style config used by every newsletter tool."""
    import json

    return json.loads((PROJECT_ROOT / "config" / "newsletter_style.json").read_text(encoding="utf-8"))


def slugify(text: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:60] or "newsletter"


def extract_json(text: str) -> dict:
    """Parse the first JSON object found in an LLM response."""
    import json

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


def get_google_credentials():
    """Return OAuth credentials for Gmail send + Sheets, running the browser flow if needed."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    load_env()
    token_path = PROJECT_ROOT / os.getenv("GMAIL_TOKEN_PATH", "token.json")
    creds_path = PROJECT_ROOT / "credentials.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            client_id, client_secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
            if client_id and client_secret:
                config = {
                    "installed": {
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"],
                    }
                }
                flow = InstalledAppFlow.from_client_config(config, GOOGLE_SCOPES)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), GOOGLE_SCOPES)
            creds = flow.run_local_server(port=8080, access_type="offline", prompt="consent")
        token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def ensure_tmp_dir() -> Path:
    """Ensure .tmp directory exists and return its path."""
    tmp_dir = Path(__file__).parent.parent / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir
