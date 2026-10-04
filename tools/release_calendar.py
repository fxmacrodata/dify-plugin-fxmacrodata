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
    indicator_slug,
    optional_date,
    optional_timezone,
)

SUMMARY_ROWS = 10


class ReleaseCalendarTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            currency = currency_code(tool_parameters.get("currency"))
            indicator = tool_parameters.get("indicator")
            params = {
                "indicator": indicator_slug(indicator) if indicator not in (None, "") else None,
                "start_date": optional_date(tool_parameters.get("start_date"), "start_date"),
                "end_date": optional_date(tool_parameters.get("end_date"), "end_date"),
                "timezone": optional_timezone(tool_parameters.get("timezone")),
            }
        except ValueError as exc:
            yield self.create_text_message(str(exc))
            return

        try:
            body = get_json(f"/calendar/{currency}", params=params, api_key=api_key_from(self.runtime))
        except FXMacroDataError as exc:
            yield self.create_text_message(str(exc))
            if isinstance(exc.body, dict):
                yield self.create_json_message(exc.body)
            return

        yield self.create_json_message(body)
        yield self.create_text_message(summarize(body, currency))


def summarize(body: Any, currency: str) -> str:
    rows = body.get("data") if isinstance(body, dict) else None
    rows = [r for r in (rows or []) if isinstance(r, dict)]
    if not rows:
        return f"No scheduled {currency.upper()} releases in that window."
    rows.sort(key=lambda r: r.get("announcement_datetime") or 0)
    lines = [f"{currency.upper()}: {len(rows)} scheduled release(s)."]
    for row in rows[:SUMMARY_ROWS]:
        when = row.get("announcement_datetime_utc") or row.get("announcement_datetime")
        lines.append(f"- {when}  {row.get('name') or row.get('release')} ({row.get('release')})")
    if len(rows) > SUMMARY_ROWS:
        lines.append(f"... and {len(rows) - SUMMARY_ROWS} more in the JSON output.")
    return "\n".join(lines)
