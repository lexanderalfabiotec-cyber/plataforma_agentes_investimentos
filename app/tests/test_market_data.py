import pytest

from investment_agents.integrations.ticker_client import (
    ProviderError,
    ServiceUnavailableError,
    TickerNotFoundError,
)
from investment_agents.services import market_data
from investment_agents.services.market_data import (
    day_change,
    fetch_histories,
    performance_stats,
    period_change,
)
from tests.conftest import make_candles


def test_day_and_period_change():
    candles = make_candles([100.0, 110.0, 121.0])
    assert day_change(candles) == pytest.approx(10.0)
    assert period_change(candles) == pytest.approx(21.0)


def test_changes_need_two_candles():
    assert day_change(make_candles([100.0])) is None
    assert period_change(make_candles([100.0])) is None


def test_performance_stats_drawdown_uses_peak():
    stats = performance_stats(make_candles([100.0, 200.0, 100.0, 150.0]))
    assert stats.total_return == pytest.approx(50.0)
    assert stats.max_drawdown == pytest.approx(-50.0)
    assert stats.annual_volatility > 0


def test_performance_stats_constant_price_has_no_risk():
    stats = performance_stats(make_candles([10.0, 10.0, 10.0]))
    assert stats.annual_volatility == 0
    assert stats.max_drawdown == 0


def test_performance_stats_needs_two_prices():
    assert performance_stats(make_candles([10.0])) is None


def test_fetch_histories_isolates_each_failure(monkeypatch, history_from):
    errors = {"GONE": TickerNotFoundError("GONE"), "SLOW": ProviderError("502")}

    def fake_get_history(symbol, range, interval):
        if symbol in errors:
            raise errors[symbol]
        return history_from([1.0, 2.0], symbol=symbol)

    monkeypatch.setattr(market_data, "get_history", fake_get_history)
    batch = fetch_histories(["B", "GONE", "A", "SLOW"])

    assert list(batch.histories) == ["B", "A"]  # ordem preservada
    assert batch.not_found == ["GONE"]
    assert batch.provider_failed == ["SLOW"]
    assert batch.service_unavailable is False


def test_fetch_histories_flags_service_down(monkeypatch):
    def fake_get_history(symbol, range, interval):
        raise ServiceUnavailableError("down")

    monkeypatch.setattr(market_data, "get_history", fake_get_history)
    batch = fetch_histories(["A", "B"])
    assert batch.service_unavailable is True
    assert not batch.histories


def test_fetch_histories_runs_in_parallel(monkeypatch, history_from):
    import threading

    barrier = threading.Barrier(3, timeout=5)

    def fake_get_history(symbol, range, interval):
        barrier.wait()  # só passa se as três consultas estiverem ativas ao mesmo tempo
        return history_from([1.0, 2.0], symbol=symbol)

    monkeypatch.setattr(market_data, "get_history", fake_get_history)
    assert len(fetch_histories(["A", "B", "C"]).histories) == 3


def test_fetch_histories_empty():
    batch = fetch_histories([])
    assert not batch.histories and not batch.service_unavailable
