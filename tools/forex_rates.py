from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import (
    FXMacroDataError,
    api_key_from,
    currency_code,
    get_json,
    optional_date,
    optional_limit,
)


class ForexRatesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            base = currency_code(tool_parameters.get("base"), "base")
            quote = currency_code(tool_parameters.get("quote"), "quote")
            params = {
                "start_date": optional_date(tool_parameters.get("start_date"), "start_date"),
                "end_date": optional_date(tool_parameters.get("end_date"), "end_date"),
                "limit": optional_limit(tool_parameters.get("limit")),
            }
        except ValueError as exc:
            yield self.create_text_message(str(exc))
            return

        api_key = api_key_from(self.runtime)
        if not api_key:
            yield self.create_text_message(
                "FX rates need an FXMacroData API key. Add one under Tools > FXMacroData > Authorize. "
                "Plans: https://fxmacrodata.com/subscribe"
            )
            return

        try:
            body = get_json(f"/forex/{base}/{quote}", params=params, api_key=api_key)
        except FXMacroDataError as exc:
            yield self.create_text_message(str(exc))
            if isinstance(exc.body, dict):
                yield self.create_json_message(exc.body)
            return

        yield self.create_json_message(body)
        yield self.create_text_message(summarize(body, base, quote))


def summarize(body: Any, base: str, quote: str) -> str:
    pair = f"{base.upper()}/{quote.upper()}"
    rows = body.get("data") if isinstance(body, dict) else None
    rows = [r for r in (rows or []) if isinstance(r, dict) and r.get("date")]
    if not rows:
        return f"{pair}: no rates in that window."
    latest = max(rows, key=lambda r: r["date"])
    earliest = min(rows, key=lambda r: r["date"])
    return (
        f"{pair}: {len(rows)} daily rate(s) from {earliest['date']} to {latest['date']}. "
        f"Latest {latest['date']} = {latest.get('val')}."
    )
