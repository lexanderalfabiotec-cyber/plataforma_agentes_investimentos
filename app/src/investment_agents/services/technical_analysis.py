"""Indicadores técnicos calculados localmente a partir dos candles do backend."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite

from investment_agents.integrations.ticker_client import TickerHistory, get_history


@dataclass(frozen=True)
class TechnicalSnapshot:
    symbol: str
    currency: str
    as_of: date
    close: float
    sma20: float | None
    sma50: float | None
    sma200: float | None
    rsi14: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    trend: str
    momentum: str

    @property
    def rsi_status(self) -> str:
        if self.rsi14 is None:
            return "indisponível"
        return "sobrecomprado" if self.rsi14 >= 70 else "sobrevendido" if self.rsi14 <= 30 else "neutro"

    @property
    def macd_status(self) -> str:
        if self.macd_histogram is None:
            return "indisponível"
        return "positivo" if self.macd_histogram > 0 else "negativo" if self.macd_histogram < 0 else "neutro"

    def compact_summary(self) -> str:
        """Retorna só os últimos indicadores, sem candles ou histórico extenso."""

        def value(number: float | None) -> str:
            return "nd" if number is None else f"{number:.2f}"

        def versus(average: float | None) -> str:
            # A comparação vai pronta: o modelo erra ao comparar números sozinho.
            if average is None:
                return "nd"
            return f"{value(average)}(px {'acima' if self.close > average else 'abaixo'})"

        return (
            f"{self.symbol} {self.currency} px={value(self.close)} "
            f"MA20={versus(self.sma20)} MA50={versus(self.sma50)} MA200={versus(self.sma200)} "
            f"RSI14={value(self.rsi14)} MACD={value(self.macd)} "
            f"sig={value(self.macd_signal)} hist={value(self.macd_histogram)} "
            f"trend={self.trend} momentum={self.momentum}"
        )

    def as_row(self) -> dict[str, str | float]:
        return {
            "Ticker": self.symbol,
            "Fechamento": self.close,
            "Média 20": round(self.sma20, 2) if self.sma20 is not None else "—",
            "Média 50": round(self.sma50, 2) if self.sma50 is not None else "—",
            "Média 200": round(self.sma200, 2) if self.sma200 is not None else "—",
            "RSI 14": round(self.rsi14, 2) if self.rsi14 is not None else "—",
            "MACD": round(self.macd, 2) if self.macd is not None else "—",
            "Sinal MACD": round(self.macd_signal, 2) if self.macd_signal is not None else "—",
            "Histograma": round(self.macd_histogram, 2) if self.macd_histogram is not None else "—",
            "Tendência": self.trend,
            "Momentum": self.momentum,
        }


def _sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _ema_series(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    if len(values) < period:
        return result

    current = sum(values[:period]) / period
    result[period - 1] = current
    alpha = 2 / (period + 1)
    for index in range(period, len(values)):
        current = values[index] * alpha + current * (1 - alpha)
        result[index] = current
    return result


def _rsi(values: list[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None

    changes = [values[index] - values[index - 1] for index in range(1, len(values))]
    gains = [max(change, 0.0) for change in changes]
    losses = [max(-change, 0.0) for change in changes]
    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for index in range(period, len(changes)):
        average_gain = (average_gain * (period - 1) + gains[index]) / period
        average_loss = (average_loss * (period - 1) + losses[index]) / period

    if average_loss == 0:
        return 100.0 if average_gain else 50.0
    relative_strength = average_gain / average_loss
    return 100 - (100 / (1 + relative_strength))


def analyze_ticker(symbol: str, period: str = "1y") -> TechnicalSnapshot:
    """Busca até um ano de candles e calcula SMA, RSI e MACD localmente."""
    return analyze_history(get_history(symbol, range=period, interval="1d"))


def analyze_history(history: TickerHistory) -> TechnicalSnapshot:
    """Calcula os indicadores a partir de um histórico já obtido."""
    candles = [candle for candle in history.candles if isfinite(candle.close)]
    closes = [candle.close for candle in candles]
    if not closes:
        raise ValueError(f"Sem candles disponíveis para {history.symbol}")

    ema12 = _ema_series(closes, 12)
    ema26 = _ema_series(closes, 26)
    macd_values = [
        fast - slow for fast, slow in zip(ema12, ema26, strict=False) if fast is not None and slow is not None
    ]
    macd_signal_series = _ema_series(macd_values, 9)
    macd = macd_values[-1] if macd_values else None
    macd_signal = macd_signal_series[-1] if macd_signal_series else None
    histogram = macd - macd_signal if macd is not None and macd_signal is not None else None

    sma20 = _sma(closes, 20)
    sma50 = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    close = closes[-1]
    if sma50 is not None and sma200 is not None:
        trend = "alta" if close > sma50 > sma200 else "baixa" if close < sma50 < sma200 else "mista"
    elif sma20 is not None:
        trend = "alta" if close > sma20 else "baixa" if close < sma20 else "mista"
    else:
        trend = "indisponível"

    rsi14 = _rsi(closes)
    momentum = (
        "indisponível"
        if histogram is None
        else "positivo"
        if histogram > 0
        else "negativo"
        if histogram < 0
        else "neutro"
    )
    if rsi14 is not None:
        momentum += ", RSI sobrecomprado" if rsi14 >= 70 else ", RSI sobrevendido" if rsi14 <= 30 else ""

    return TechnicalSnapshot(
        symbol=history.symbol,
        currency=history.currency,
        as_of=candles[-1].date.date(),
        close=close,
        sma20=sma20,
        sma50=sma50,
        sma200=sma200,
        rsi14=rsi14,
        macd=macd,
        macd_signal=macd_signal,
        macd_histogram=histogram,
        trend=trend,
        momentum=momentum,
    )


def compact_analysis(snapshots: list[TechnicalSnapshot]) -> str:
    """Monta uma linha por ação para enviar ao modelo usando poucos tokens."""
    return "\n".join(snapshot.compact_summary() for snapshot in snapshots)
