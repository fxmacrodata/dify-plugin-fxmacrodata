from __future__ import annotations

from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools._client import FXMacroDataError, get_json


class FXMacroDataProvider(ToolProvider):
    """The API key is optional: USD data works without one.

    When a key is supplied it is checked with one small authenticated request.
    """

    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        api_key = str(credentials.get("api_key") or "").strip()
        if not api_key:
            return
        try:
            get_json("/announcements/usd/inflation", params={"limit": 1}, api_key=api_key)
        except FXMacroDataError as exc:
            if exc.status in (401, 403):
                raise ToolProviderCredentialValidationError(
                    "FXMacroData did not accept this API key. Check the key, or leave the field "
                    "empty to use USD data without one."
                ) from None
            raise ToolProviderCredentialValidationError(str(exc)) from None
