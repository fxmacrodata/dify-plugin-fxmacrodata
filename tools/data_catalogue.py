from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._client import FXMacroDataError, api_key_from, currency_code, get_json


class DataCatalogueTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        try:
            currency = currency_code(tool_parameters.get("currency"))
        except ValueError as exc:
            yield self.create_text_message(str(exc))
            return

        try:
            body = get_json(f"/data_catalogue/{currency}", api_key=api_key_from(self.runtime))
        except FXMacroDataError as exc:
            yield self.create_text_message(str(exc))
            if isinstance(exc.body, dict):
                yield self.create_json_message(exc.body)
            return

        yield self.create_json_message(body)
        yield self.create_text_message(summarize(body, currency))


def summarize(body: Any, currency: str) -> str:
    if not isinstance(body, dict):
        return f"No indicators listed for {currency.upper()}."
    entries = []
    for slug, meta in sorted(body.items()):
        if isinstance(meta, dict):
            entries.append(f"{slug} ({meta.get('name') or slug})")
    if not entries:
        return f"No indicators listed for {currency.upper()}."
    return (
        f"{currency.upper()}: {len(entries)} indicators available. "
        "Pass a slug to indicator_history.\n" + ", ".join(entries)
    )
