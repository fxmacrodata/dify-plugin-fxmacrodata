"""Unit tests for the FXMacroData tools. HTTP is mocked; nothing hits the network."""

from __future__ import annotations

import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))


def _ensure_stub_modules() -> None:
    """Stub dify_plugin when the SDK is not installed, so the tests run anywhere."""
    try:
        import dify_plugin  # noqa: F401
        import dify_plugin.errors.tool  # noqa: F401
        return
    except ImportError:
        pass

    sdk = types.ModuleType("dify_plugin")

    class _Base:
        pass

    sdk.Tool = _Base
    sdk.ToolProvider = _Base
    entities = types.ModuleType("dify_plugin.entities")
    tool_entities = types.ModuleType("dify_plugin.entities.tool")
    tool_entities.ToolInvokeMessage = type("ToolInvokeMessage", (), {})
    errors = types.ModuleType("dify_plugin.errors")
    tool_errors = types.ModuleType("dify_plugin.errors.tool")
    tool_errors.ToolProviderCredentialValidationError = type(
        "ToolProviderCredentialValidationError", (Exception,), {}
    )
    sys.modules.update(
        {
            "dify_plugin": sdk,
            "dify_plugin.entities": entities,
            "dify_plugin.entities.tool": tool_entities,
            "dify_plugin.errors": errors,
            "dify_plugin.errors.tool": tool_errors,
        }
    )


_ensure_stub_modules()

from dify_plugin.errors.tool import ToolProviderCredentialValidationError  # noqa: E402

from provider.fxmacrodata import FXMacroDataProvider  # noqa: E402
from tools import _client  # noqa: E402
from tools.data_catalogue import DataCatalogueTool  # noqa: E402
from tools.forex_rates import ForexRatesTool  # noqa: E402
from tools.indicator_history import IndicatorHistoryTool  # noqa: E402
from tools.release_calendar import ReleaseCalendarTool  # noqa: E402

BASE = "https://api.fxmacrodata.com/v1"


class _FakeResponse:
    def __init__(self, body, status_code=200):
        self._body = body
        self.status_code = status_code

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def _make_tool(cls, credentials=None):
    tool = object.__new__(cls)
    tool.runtime = SimpleNamespace(credentials=credentials or {})
    tool.create_text_message = lambda text: ("text", text)
    tool.create_json_message = lambda json: ("json", json)
    return tool


def _run(cls, params, credentials=None, response=None):
    tool = _make_tool(cls, credentials)
    fake_get = mock.Mock(return_value=response or _FakeResponse({}))
    with mock.patch.object(_client.requests, "get", fake_get):
        messages = list(tool._invoke(params))
    return messages, fake_get


INFLATION = {
    "currency": "USD",
    "indicator": "inflation",
    "name": "Inflation (CPI)",
    "source": "BLS",
    "latest_available_date": "2026-08-31",
    "freemium_delay": {
        "applied": True,
        "delay_minutes": 15,
        "withheld_count": 0,
        "message": "Free access is delayed by 15 minutes.",
    },
    "data": [
        {"date": "2026-08-31", "val": 3.4},
        {"date": "2026-07-31", "val": 3.4},
    ],
}


# indicator_history


def test_indicator_history_happy_path_returns_json_unchanged():
    messages, fake_get = _run(
        IndicatorHistoryTool,
        {"currency": "USD", "indicator": "inflation", "limit": 2},
        response=_FakeResponse(INFLATION),
    )
    assert messages[0] == ("json", INFLATION)
    text = messages[1][1]
    assert "Inflation (CPI)" in text
    assert "2026-08-31 = 3.4" in text
    assert "delayed by 15 minutes" in text
    url = fake_get.call_args.args[0]
    assert url == f"{BASE}/announcements/usd/inflation"
    assert fake_get.call_args.kwargs["params"] == {"limit": 2}
    assert fake_get.call_args.kwargs["timeout"] == _client.TIMEOUT_SECONDS


def test_indicator_history_passes_dates():
    _, fake_get = _run(
        IndicatorHistoryTool,
        {"currency": "usd", "indicator": "gdp", "start_date": "2026-01-01", "end_date": "2026-06-30"},
        response=_FakeResponse(INFLATION),
    )
    assert fake_get.call_args.kwargs["params"] == {"start_date": "2026-01-01", "end_date": "2026-06-30"}


def test_indicator_history_reports_withheld_release():
    body = dict(INFLATION)
    body["freemium_delay"] = {
        "applied": True,
        "delay_minutes": 15,
        "withheld_count": 1,
        "next_available_at_iso": "2026-10-04T12:45:00Z",
    }
    messages, _ = _run(
        IndicatorHistoryTool, {"currency": "USD", "indicator": "inflation"}, response=_FakeResponse(body)
    )
    assert "1 newer release(s)" in messages[1][1]
    assert "2026-10-04T12:45:00Z" in messages[1][1]


def test_indicator_history_reports_history_window():
    body = dict(INFLATION)
    body["freemium_window"] = {"applied": True, "max_days": 90, "message": "Anonymous access returns 90 days."}
    messages, _ = _run(
        IndicatorHistoryTool, {"currency": "USD", "indicator": "inflation"}, response=_FakeResponse(body)
    )
    assert "Anonymous access returns 90 days." in messages[1][1]


@pytest.mark.parametrize(
    "params",
    [
        {"currency": "", "indicator": "inflation"},
        {"currency": "US/D", "indicator": "inflation"},
        {"currency": "USD", "indicator": "../forex"},
        {"currency": "USD", "indicator": "inflation", "start_date": "01/02/2026"},
        {"currency": "USD", "indicator": "inflation", "limit": 500},
    ],
)
def test_indicator_history_bad_input_makes_no_request(params):
    messages, fake_get = _run(IndicatorHistoryTool, params)
    assert fake_get.call_count == 0
    assert messages[0][0] == "text"


def test_indicator_history_api_error_is_surfaced():
    error = {"code": "api_key_required", "detail": "This endpoint requires an API key."}
    messages, _ = _run(
        IndicatorHistoryTool,
        {"currency": "EUR", "indicator": "inflation"},
        response=_FakeResponse(error, status_code=401),
    )
    assert messages[0] == ("text", "FXMacroData returned HTTP 401: This endpoint requires an API key.")
    assert messages[1] == ("json", error)


def test_network_error_is_surfaced():
    tool = _make_tool(IndicatorHistoryTool)
    fake_get = mock.Mock(side_effect=_client.requests.exceptions.ConnectionError("boom"))
    with mock.patch.object(_client.requests, "get", fake_get):
        messages = list(tool._invoke({"currency": "USD", "indicator": "inflation"}))
    assert messages == [("text", "Could not reach api.fxmacrodata.com: ConnectionError")]


# API key handling


def test_api_key_sent_only_as_header():
    _, fake_get = _run(
        IndicatorHistoryTool,
        {"currency": "USD", "indicator": "inflation"},
        credentials={"api_key": "test-key"},
        response=_FakeResponse(INFLATION),
    )
    assert fake_get.call_args.kwargs["headers"]["X-API-Key"] == "test-key"
    assert "test-key" not in fake_get.call_args.args[0]
    assert "api_key" not in fake_get.call_args.kwargs["params"]


def test_no_key_means_no_header():
    _, fake_get = _run(
        IndicatorHistoryTool, {"currency": "USD", "indicator": "inflation"}, response=_FakeResponse(INFLATION)
    )
    assert "X-API-Key" not in fake_get.call_args.kwargs["headers"]


def test_base_url_is_https():
    assert _client.BASE_URL.startswith("https://api.fxmacrodata.com/")


# data_catalogue


def test_data_catalogue_happy_path():
    body = {"gdp": {"name": "GDP", "unit": "USD bn"}, "inflation": {"name": "Inflation (CPI)"}}
    messages, fake_get = _run(DataCatalogueTool, {"currency": "USD"}, response=_FakeResponse(body))
    assert fake_get.call_args.args[0] == f"{BASE}/data_catalogue/usd"
    assert messages[0] == ("json", body)
    assert "2 indicators" in messages[1][1]
    assert "inflation (Inflation (CPI))" in messages[1][1]


# release_calendar


def test_release_calendar_happy_path_sorted_summary():
    body = {
        "currency": "USD",
        "data": [
            {"announcement_datetime": 200, "announcement_datetime_utc": "2026-10-07T15:00:00+00:00",
             "release": "consumer_confidence", "name": "Consumer Confidence"},
            {"announcement_datetime": 100, "announcement_datetime_utc": "2026-10-06T12:30:00+00:00",
             "release": "trade_balance", "name": "Trade Balance"},
        ],
    }
    messages, fake_get = _run(
        ReleaseCalendarTool,
        {"currency": "USD", "indicator": "trade_balance", "timezone": "Europe/London"},
        response=_FakeResponse(body),
    )
    assert fake_get.call_args.args[0] == f"{BASE}/calendar/usd"
    assert fake_get.call_args.kwargs["params"] == {"indicator": "trade_balance", "timezone": "Europe/London"}
    assert messages[0] == ("json", body)
    text = messages[1][1]
    assert text.index("Trade Balance") < text.index("Consumer Confidence")


def test_release_calendar_empty():
    messages, _ = _run(ReleaseCalendarTool, {"currency": "USD"}, response=_FakeResponse({"data": []}))
    assert "No scheduled USD releases" in messages[1][1]


# forex_rates


def test_forex_rates_without_key_makes_no_request():
    messages, fake_get = _run(ForexRatesTool, {"base": "EUR", "quote": "USD"})
    assert fake_get.call_count == 0
    assert "API key" in messages[0][1]


def test_forex_rates_with_key():
    body = {"base": "EUR", "quote": "USD", "data": [{"date": "2026-10-02", "val": 1.17}, {"date": "2026-10-01", "val": 1.16}]}
    messages, fake_get = _run(
        ForexRatesTool,
        {"base": "eur", "quote": "usd", "limit": 2},
        credentials={"api_key": "test-key"},
        response=_FakeResponse(body),
    )
    assert fake_get.call_args.args[0] == f"{BASE}/forex/eur/usd"
    assert fake_get.call_args.kwargs["headers"]["X-API-Key"] == "test-key"
    assert messages[0] == ("json", body)
    assert "EUR/USD: 2 daily rate(s) from 2026-10-01 to 2026-10-02" in messages[1][1]


# provider


def _provider():
    return object.__new__(FXMacroDataProvider)


def test_provider_no_key_skips_http():
    fake_get = mock.Mock(side_effect=AssertionError("no http"))
    with mock.patch.object(_client.requests, "get", fake_get):
        _provider()._validate_credentials({})
        _provider()._validate_credentials({"api_key": "  "})
    assert fake_get.call_count == 0


def test_provider_valid_key():
    fake_get = mock.Mock(return_value=_FakeResponse(INFLATION))
    with mock.patch.object(_client.requests, "get", fake_get):
        _provider()._validate_credentials({"api_key": "test-key"})
    assert fake_get.call_args.kwargs["headers"]["X-API-Key"] == "test-key"
    assert fake_get.call_args.kwargs["params"] == {"limit": 1}


def test_provider_rejected_key():
    fake_get = mock.Mock(return_value=_FakeResponse({"code": "invalid_api_key"}, status_code=401))
    with mock.patch.object(_client.requests, "get", fake_get):
        with pytest.raises(ToolProviderCredentialValidationError):
            _provider()._validate_credentials({"api_key": "wrong"})
