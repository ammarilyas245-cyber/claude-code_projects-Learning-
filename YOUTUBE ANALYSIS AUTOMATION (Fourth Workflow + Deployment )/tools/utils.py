"""Shared helpers for the YouTube analysis tools."""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/presentations",
    "https://www.googleapis.com/auth/drive.file",
]


def load_env() -> None:
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)


def get_env(key_name: str, required: bool = True) -> str:
    load_env()
    value = os.getenv(key_name, "")
    if required and not value:
        raise ValueError(f"Missing {key_name}. Fill it in .env")
    return value


def load_config(name: str) -> dict:
    return json.loads((PROJECT_ROOT / "config" / name).read_text(encoding="utf-8"))


def save_config(name: str, data: dict) -> None:
    (PROJECT_ROOT / "config" / name).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def ensure_tmp_dir() -> Path:
    tmp = PROJECT_ROOT / ".tmp"
    tmp.mkdir(exist_ok=True)
    return tmp


def niche_title_pattern(terms: list[str]) -> re.Pattern:
    alternatives = "|".join(re.escape(t) for t in terms)
    return re.compile(rf"\b(?:{alternatives})\b", re.IGNORECASE)


def chunks(items: list, size: int = 50):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


SECRET_PARAM = re.compile(
    r"((?:key|access_token|refresh_token|client_secret)=)[^&\s'\"]+", re.I
)
SECRET_TOKENS = re.compile(
    r"AIza[0-9A-Za-z_-]{30,}|GOCSPX-[0-9A-Za-z_-]{10,}|ya29\.[0-9A-Za-z_-]{20,}|1//[0-9A-Za-z_-]{30,}"
)


def redact(text: str) -> str:
    """Remove API keys and tokens from text before it is logged or emailed."""
    text = SECRET_PARAM.sub(r"\1<redacted>", text)
    return SECRET_TOKENS.sub("<redacted>", text)


def youtube_get(endpoint: str, **params) -> dict:
    headers = {"X-Goog-Api-Key": get_env("YOUTUBE_API_KEY")}
    for attempt in range(3):
        resp = requests.get(
            f"{YOUTUBE_API}/{endpoint}", params=params, headers=headers, timeout=30
        )
        if resp.status_code in (429, 500, 503) and attempt < 2:
            time.sleep(2**attempt)
            continue
        if not resp.ok:
            raise RuntimeError(
                redact(
                    f"YouTube {endpoint} failed {resp.status_code}: {resp.text[:300]}"
                )
            )
        return resp.json()


def get_google_credentials():
    """OAuth credentials for Gmail, Sheets, Slides and Drive.

    Local runs use token.json (browser consent once). Modal runs set GOOGLE_TOKEN_JSON
    instead and never open a browser.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    token_json = os.getenv("GOOGLE_TOKEN_JSON", "")
    if token_json:
        creds = Credentials.from_authorized_user_info(
            json.loads(token_json), GOOGLE_SCOPES
        )
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
        if not creds.valid:
            raise RuntimeError(
                "Google token is invalid. Re-run auth locally, then update GOOGLE_TOKEN_JSON in the Modal secret."
            )
        return creds

    token_path = PROJECT_ROOT / "token.json"
    client_config = {
        "installed": {
            "client_id": get_env("GOOGLE_CLIENT_ID"),
            "client_secret": get_env("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    creds = (
        Credentials.from_authorized_user_file(str(token_path), GOOGLE_SCOPES)
        if token_path.exists()
        else None
    )
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_config(client_config, GOOGLE_SCOPES)
        creds = flow.run_local_server(
            port=8080, access_type="offline", prompt="consent"
        )
    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds
