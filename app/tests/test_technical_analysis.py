import pytest

from investment_agents.services.technical_analysis import _ema_series, _rsi, _sma, analyze_history


def test_sma_uses_last_window_and_requires_enough_data():
    assert _sma([1, 2, 3, 4], 2) == 3.5
    assert _sma([1], 2) is None


def test_ema_starts_from_sma_of_first_period():
    series = _ema_series([1.0, 2.0, 3.0, 4.0], 3)
    assert series[:2] == [None, None]
    assert series[2] == 2.0
    assert series[3] == pytest.approx(3.0)


def test_rsi_limits():
    rising = [float(value) for value in range(1, 30)]
    assert _rsi(rising) == 100.0
    assert _rsi(list(reversed(rising))) == 0.0
    assert _rsi([5.0] * 30) == 50.0
    assert _rsi([1.0] * 14) is None


def test_analyze_history_rising_market(history_from):
    snapshot = analyze_history(history_from([100 * 1.01**i for i in range(250)]))
    assert snapshot.trend == "alta"
    assert snapshot.rsi_status == "sobrecomprado"
    assert snapshot.macd_status == "positivo"
    assert snapshot.close == pytest.approx(100 * 1.01**249)
    assert snapshot.as_of.isoformat() == "2026-09-07"


def test_analyze_history_falling_market(history_from):
    snapshot = analyze_history(history_from([1000 - 0.01 * i**2 for i in range(250)]))
    assert snapshot.trend == "baixa"
    assert snapshot.rsi_status == "sobrevendido"
    assert snapshot.macd_status == "negativo"


def test_analyze_history_short_series_marks_indicators_unavailable(history_from):
    snapshot = analyze_history(history_from([10.0, 11.0]))
    assert snapshot.trend == "indisponível"
    assert snapshot.rsi_status == "indisponível"
    assert snapshot.macd_status == "indisponível"
    assert "MA200=nd" in snapshot.compact_summary()


def test_analyze_history_without_candles_raises(history_from):
    with pytest.raises(ValueError):
        analyze_history(history_from([]))
