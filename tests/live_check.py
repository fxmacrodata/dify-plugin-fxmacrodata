"""Call each tool once against the live API without a key (USD only).

    python tests/live_check.py

Needs the dify_plugin SDK and network access. Not part of the unit tests.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from provider.fxmacrodata import FXMacroDataProvider  # noqa: E402
from tools.data_catalogue import DataCatalogueTool  # noqa: E402
from tools.forex_rates import ForexRatesTool  # noqa: E402
from tools.indicator_history import IndicatorHistoryTool  # noqa: E402
from tools.release_calendar import ReleaseCalendarTool  # noqa: E402

CASES = [
    (IndicatorHistoryTool, {"currency": "USD", "indicator": "inflation", "limit": 3}),
    (IndicatorHistoryTool, {"currency": "USD", "indicator": "unemployment", "start_date": "2020-01-01", "limit": 2}),
    (IndicatorHistoryTool, {"currency": "EUR", "indicator": "inflation", "limit": 1}),
    (DataCatalogueTool, {"currency": "USD"}),
    (ReleaseCalendarTool, {"currency": "USD", "timezone": "Europe/London"}),
    (ForexRatesTool, {"base": "EUR", "quote": "USD", "limit": 2}),
]


def main() -> int:
    failures = 0
    object.__new__(FXMacroDataProvider)._validate_credentials({})
    print("provider: no-key validation ok")
    for cls, params in CASES:
        tool = cls.from_credentials({}, user_id="live-check")
        messages = list(tool.invoke(tool_parameters=params))
        kinds = [m.type.value if hasattr(m.type, "value") else str(m.type) for m in messages]
        print(f"=== {cls.__name__} {json.dumps(params)} -> {kinds}")
        for m in messages:
            if "text" in str(m.type):
                print(m.message.text[:600])
            else:
                payload = m.message.json_object
                print(f"  json keys: {sorted(payload)[:12]}{' ...' if len(payload) > 12 else ''}")
        if not messages:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
