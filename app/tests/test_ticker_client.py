import pytest
import requests

from investment_agents.integrations import ticker_client
from investment_agents.integrations.ticker_client import (
    ProviderError,
    ServiceUnavailableError,
    TickerNotFoundError,
    get_history,
    get_latest,
)
from tests import responses_stub


@pytest.fixture
def backend(monkeypatch):
    stub = responses_stub.SessionStub()
    monkeypatch.setattr(ticker_client, "_session", stub)
    return stub


CANDLE = {"date": "2026-10-30T20:00:00Z", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10}


def test_history_is_parsed(backend):
    backend.reply(200, {"symbol": "A", "currency": "BRL", "candles": [CANDLE]})
    history = get_history("A", range="3mo")
    assert history.candles[0].close == 1.5
    assert history.candles[0].date.date().isoformat() == "2026-10-30"
    assert backend.last_params == {"symbol": "A", "range": "3mo", "interval": "1d"}


def test_latest_is_parsed(backend):
    backend.reply(200, {"symbol": "A", "currency": "USD", "candle": CANDLE})
    assert get_latest("A").currency == "USD"


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (404, {"error": "x"}, TickerNotFoundError),
        (400, {"error": "x"}, TickerNotFoundError),
        (502, {"error": "x"}, ProviderError),
        (502, "<html>proxy</html>", ProviderError),
        (200, "isto não é json", ProviderError),
    ],
)
def test_http_failures_map_to_typed_errors(backend, status, body, expected):
    backend.reply(status, body)
    with pytest.raises(expected):
        get_latest("A")


def test_connection_failure_maps_to_service_unavailable(backend):
    backend.fail(requests.ConnectionError("recusada"))
    with pytest.raises(ServiceUnavailableError):
        get_history("A")


def test_session_does_not_retry_on_status_errors():
    retry = ticker_client._make_session().get_adapter("http://x").max_retries
    assert retry.status_forcelist == frozenset() or not retry.status_forcelist
    assert retry.read == 0
    assert retry.connect == 1
