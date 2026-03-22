"""
gmail_auth.py — Google OAuth2 authentication flow.

First run: opens browser for consent, saves token.json.
Subsequent runs: loads token.json (refreshing silently when expired).
"""

import os
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

# Paths are resolved relative to the directory that contains this module.
_BASE_DIR        = Path(__file__).parent
CREDENTIALS_PATH = _BASE_DIR / "credentials.json"
TOKEN_PATH       = _BASE_DIR / "token.json"


class AuthError(Exception):
    """Raised when OAuth2 authentication fails."""


def get_credentials() -> Credentials:
    """
    Load or obtain OAuth2 credentials.

    Flow:
      1. If token.json exists and is valid → use it.
      2. If token.json has an expired access token but a valid refresh token → refresh.
      3. Otherwise → open browser consent flow and save new token.json.

    Raises AuthError if credentials.json is missing or auth fails.
    """
    if not CREDENTIALS_PATH.exists():
        raise AuthError(
            f"credentials.json not found at {CREDENTIALS_PATH}.\n"
            "Please download it from Google Cloud Console and place it "
            "in the same directory as the application."
        )

    creds: Optional[Credentials] = None

    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception as exc:
            logger.warning("Failed to load token.json: %s — re-authenticating.", exc)
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            return creds
        except Exception as exc:
            logger.warning("Token refresh failed: %s — re-authenticating.", exc)
            creds = None

    # Full browser consent flow
    try:
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True)
    except Exception as exc:
        raise AuthError(f"OAuth2 authentication failed: {exc}") from exc

    _save_token(creds)
    return creds


def get_gmail_service(creds: Optional[Credentials] = None):
    """
    Return an authorised Gmail API service object.
    Obtains credentials automatically if not provided.
    """
    if creds is None:
        creds = get_credentials()
    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except HttpError as exc:
        raise AuthError(f"Failed to build Gmail service: {exc}") from exc


def get_authenticated_email(creds: Optional[Credentials] = None) -> str:
    """Return the Gmail address associated with the credentials."""
    service = get_gmail_service(creds)
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "Unknown")
    except HttpError as exc:
        logger.error("Could not fetch Gmail profile: %s", exc)
        return "Unknown"


def revoke_credentials() -> None:
    """Delete the saved token.json to force re-authentication."""
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        logger.info("token.json removed — credentials revoked.")


def is_authenticated() -> bool:
    """Quick check: does a valid (or refreshable) token exist?"""
    if not TOKEN_PATH.exists():
        return False
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        return creds.valid or bool(creds.refresh_token)
    except Exception:
        return False


# ── Private ───────────────────────────────────────────────────────────────────

def _save_token(creds: Credentials) -> None:
    try:
        TOKEN_PATH.write_text(creds.to_json())
        logger.info("token.json saved to %s", TOKEN_PATH)
    except OSError as exc:
        logger.error("Could not save token.json: %s", exc)
