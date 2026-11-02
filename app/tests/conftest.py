from datetime import UTC, datetime, timedelta

import pytest

from investment_agents.integrations.ticker_client import Candle, TickerHistory


def make_candles(closes, start=datetime(2026, 1, 1, tzinfo=UTC)):
    return [
        Candle(date=start + timedelta(days=i), open=c, high=c, low=c, close=c, volume=100)
        for i, c in enumerate(closes)
    ]


@pytest.fixture
def history_from():
    def build(closes, symbol="TEST", currency="BRL"):
        return TickerHistory(symbol=symbol, currency=currency, candles=make_candles(closes))

    return build
