from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import (
    FXMacroDataError,
    api_key_from,
    currency_code,
    free_tier_notes,
    get_json,
    indicator_slug,
    optional_date,
    optional_limit,
)


class IndicatorHistoryTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            currency = currency_code(tool_parameters.get("currency"))
            indicator = indicator_slug(tool_parameters.get("indicator"))
            params = {
                "start_date": optional_date(tool_parameters.get("start_date"), "start_date"),
                "end_date": optional_date(tool_parameters.get("end_date"), "end_date"),
                "limit": optional_limit(tool_parameters.get("limit")),
            }
        except ValueError as exc:
            yield self.create_text_message(str(exc))
            return

        try:
            body = get_json(
                f"/announcements/{currency}/{indicator}",
                params=params,
                api_key=api_key_from(self.runtime),
            )
        except FXMacroDataError as exc:
            yield self.create_text_message(str(exc))
            if isinstance(exc.body, dict):
                yield self.create_json_message(exc.body)
            return

        yield self.create_json_message(body)
        yield self.create_text_message(summarize(body, currency, indicator))


def summarize(body: Any, currency: str, indicator: str) -> str:
    if not isinstance(body, dict):
        return f"{currency.upper()} {indicator}: unexpected response shape."
    rows = body.get("data") or []
    name = body.get("name") or indicator
    lines = [f"{currency.upper()} {name} ({indicator}): {len(rows)} row(s)."]
    dated = [r for r in rows if isinstance(r, dict) and r.get("date")]
    if dated:
        latest = max(dated, key=lambda r: r["date"])
        lines.append(f"Latest observation: {latest['date']} = {latest.get('val')}.")
    elif body.get("latest_available_date"):
        lines.append(
            f"No rows in the requested window. Latest available date: {body['latest_available_date']}."
        )
    if body.get("source"):
        lines.append(f"Source: {body['source']}.")
    lines.extend(free_tier_notes(body))
    return "\n".join(lines)
