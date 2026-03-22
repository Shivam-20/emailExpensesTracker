"""
core/gmail_auth.py — Google OAuth2 authentication + Gmail label listing.
"""

import logging
from pathlib import Path
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# credentials.json lives next to main.py (parent of core/)
_APP_DIR         = Path(__file__).parent.parent
CREDENTIALS_PATH = _APP_DIR / "credentials.json"


class AuthError(Exception):
    """Raised when OAuth2 authentication fails."""


def get_credentials(data_dir: Path) -> Credentials:
    """
    Load or obtain OAuth2 credentials from *data_dir*/token.json.
    Raises AuthError on failure.
    """
    token_path = data_dir / "token.json"

    if not CREDENTIALS_PATH.exists():
        raise AuthError(
            f"credentials.json not found at {CREDENTIALS_PATH}.\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    creds: Optional[Credentials] = None
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        except Exception as exc:
            logger.warning("Failed to load token.json: %s", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds, token_path)
            return creds
        except Exception as exc:
            logger.warning("Token refresh failed: %s — re-authenticating.", exc)
            creds = None

    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    except Exception as exc:
        raise AuthError(f"OAuth2 authentication failed: {exc}") from exc

    _save_token(creds, token_path)
    return creds


def get_gmail_service(data_dir: Path, creds: Optional[Credentials] = None):
    if creds is None:
        creds = get_credentials(data_dir)
    try:
        return build("gmail", "v1", credentials=creds)
    except HttpError as exc:
        raise AuthError(f"Failed to build Gmail service: {exc}") from exc


def get_authenticated_email(data_dir: Path) -> str:
    service = get_gmail_service(data_dir)
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "Unknown")
    except HttpError as exc:
        logger.error("Profile fetch failed: %s", exc)
        return "Unknown"


def get_gmail_labels(data_dir: Path) -> list[dict]:
    """
    Return list of dicts: [{"id": "...", "name": "..."}, ...]
    Sorted: system labels first, then user labels alphabetically.
    """
    service = get_gmail_service(data_dir)
    try:
        result = service.users().labels().list(userId="me").execute()
        labels = result.get("labels", [])

        system_order = ["INBOX", "SENT", "DRAFT", "SPAM", "TRASH",
                        "CATEGORY_PROMOTIONS", "CATEGORY_UPDATES",
                        "CATEGORY_FORUMS", "CATEGORY_SOCIAL",
                        "CATEGORY_PERSONAL"]

        def sort_key(lbl):
            name = lbl.get("name", "")
            try:
                return (0, system_order.index(name))
            except ValueError:
                return (1, name.lower())

        labels.sort(key=sort_key)
        return [{"id": l["id"], "name": l["name"]} for l in labels]
    except HttpError as exc:
        logger.error("Label fetch failed: %s", exc)
        return []


def revoke_credentials(data_dir: Path) -> None:
    token_path = data_dir / "token.json"
    if token_path.exists():
        token_path.unlink()
        logger.info("token.json removed.")


def is_authenticated(data_dir: Path) -> bool:
    token_path = data_dir / "token.json"
    if not token_path.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        return creds.valid or bool(creds.refresh_token)
    except Exception:
        return False


def _save_token(creds: Credentials, path: Path) -> None:
    try:
        path.write_text(creds.to_json())
    except OSError as exc:
        logger.error("Could not save token.json: %s", exc)
