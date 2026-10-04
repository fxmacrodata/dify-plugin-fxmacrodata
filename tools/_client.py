"""Shared HTTP helper and input checks for the FXMacroData tools.

Every request goes to one fixed HTTPS host. The optional API key is sent only
in the X-API-Key header, never in the URL.
"""

from __future__ import annotations

import re
from typing import Any

import requests

BASE_URL = "https://api.fxmacrodata.com/v1"
TIMEOUT_SECONDS = 20
USER_AGENT = "fxmacrodata-dify-plugin/0.0.1"

_CURRENCY_RE = re.compile(r"^[A-Za-z]{3,4}$")
_SLUG_RE = re.compile(r"^[a-z0-9_]{1,64}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIMEZONE_RE = re.compile(r"^[A-Za-z0-9_+\-/]{1,64}$")


class FXMacroDataError(Exception):
    """An API or network failure, with the API's error body when there is one."""

    def __init__(self, message: str, status: int | None = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


def currency_code(value: Any, name: str = "currency") -> str:
    code = str(value or "").strip()
    if not _CURRENCY_RE.match(code):
        raise ValueError(f"{name} must be a currency code such as USD or EUR, got {value!r}.")
    return code.lower()


def indicator_slug(value: Any) -> str:
    slug = str(value or "").strip().lower()
    if not _SLUG_RE.match(slug):
        raise ValueError(
            f"indicator must be a slug such as inflation or policy_rate, got {value!r}. "
            "Use the data_catalogue tool to list valid slugs."
        )
    return slug


def optional_date(value: Any, name: str) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if not _DATE_RE.match(text):
        raise ValueError(f"{name} must use YYYY-MM-DD, got {value!r}.")
    return text


def optional_limit(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        raise ValueError(f"limit must be a whole number from 1 to 100, got {value!r}.") from None
    if not 1 <= number <= 100:
        raise ValueError(f"limit must be from 1 to 100, got {number}.")
    return number


def optional_timezone(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if not _TIMEZONE_RE.match(text):
        raise ValueError(f"timezone must be an IANA name such as Europe/London, got {value!r}.")
    return text


def get_json(path: str, params: dict[str, Any] | None = None, api_key: str | None = None) -> Any:
    """GET ``BASE_URL + path`` and return the decoded JSON body.

    ``path`` is built by the tools from validated parts only. Empty params are
    dropped. Raises FXMacroDataError on network errors and non-2xx replies.
    """
    clean = {k: v for k, v in (params or {}).items() if v is not None and v != ""}
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if api_key:
        headers["X-API-Key"] = api_key
    try:
        response = requests.get(
            f"{BASE_URL}{path}", params=clean, headers=headers, timeout=TIMEOUT_SECONDS
        )
    except requests.exceptions.RequestException as exc:
        raise FXMacroDataError(f"Could not reach api.fxmacrodata.com: {type(exc).__name__}") from None

    try:
        body = response.json()
    except ValueError:
        body = None

    if response.status_code >= 400:
        detail = ""
        if isinstance(body, dict):
            detail = str(body.get("detail") or body.get("error") or "")
        message = f"FXMacroData returned HTTP {response.status_code}"
        if detail:
            message = f"{message}: {detail}"
        raise FXMacroDataError(message, status=response.status_code, body=body)

    if body is None:
        raise FXMacroDataError("FXMacroData returned a response that is not JSON.", status=response.status_code)
    return body


def api_key_from(runtime: Any) -> str | None:
    credentials = getattr(runtime, "credentials", None) or {}
    key = str(credentials.get("api_key") or "").strip()
    return key or None


def free_tier_notes(body: Any) -> list[str]:
    """Plain-text lines for the free-tier delay and history window, if present."""
    if not isinstance(body, dict):
        return []
    notes: list[str] = []
    delay = body.get("freemium_delay")
    if isinstance(delay, dict) and delay.get("applied"):
        withheld = delay.get("withheld_count") or 0
        if withheld:
            when = delay.get("next_available_at_iso") or "shortly"
            notes.append(
                f"{withheld} newer release(s) have been published but are withheld on the free tier "
                f"until {when}. An API key returns them in real time."
            )
        else:
            minutes = delay.get("delay_minutes", 15)
            notes.append(f"Free tier: data is delayed by {minutes} minutes. Nothing is currently withheld.")
    window = body.get("freemium_window")
    if isinstance(window, dict) and window.get("applied"):
        notes.append(
            str(window.get("message") or f"Free tier: history limited to the last {window.get('max_days')} days.")
        )
    return notes
