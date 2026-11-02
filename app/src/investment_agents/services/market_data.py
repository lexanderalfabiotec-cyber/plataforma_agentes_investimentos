"""Busca paralela de históricos e métricas de desempenho."""

from __future__ import annotations

from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from math import sqrt
from statistics import stdev

from investment_agents.integrations.ticker_client import (
    Candle,
    ServiceUnavailableError,
    TickerHistory,
    TickerNotFoundError,
    get_history,
)

MAX_PARALLEL_REQUESTS = 8
TRADING_DAYS_PER_YEAR = 252


@dataclass
class HistoryBatch:
    """Resultado por ativo: uma falha isolada não derruba os demais."""

    histories: dict[str, TickerHistory] = field(default_factory=dict)
    not_found: list[str] = field(default_factory=list)
    provider_failed: list[str] = field(default_factory=list)
    service_unavailable: bool = False


@dataclass(frozen=True)
class PerformanceStats:
    total_return: float
    annual_volatility: float | None
    max_drawdown: float


def fetch_histories(symbols: Sequence[str], period: str = "1mo", interval: str = "1d") -> HistoryBatch:
    """Consulta os ativos em paralelo, preservando a ordem recebida."""
    batch = HistoryBatch()
    if not symbols:
        return batch

    def fetch(symbol: str) -> TickerHistory:
        return get_history(symbol, range=period, interval=interval)

    with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_REQUESTS, len(symbols))) as pool:
        futures = [(symbol, pool.submit(fetch, symbol)) for symbol in symbols]
        for symbol, future in futures:
            try:
                batch.histories[symbol] = future.result()
            except TickerNotFoundError:
                batch.not_found.append(symbol)
            except ServiceUnavailableError:
                batch.service_unavailable = True
            except Exception:
                batch.provider_failed.append(symbol)
    return batch


def day_change(candles: Sequence[Candle]) -> float | None:
    """Variação percentual do último fechamento sobre o fechamento anterior."""
    if len(candles) < 2 or not candles[-2].close:
        return None
    return (candles[-1].close / candles[-2].close - 1) * 100


def period_change(candles: Sequence[Candle]) -> float | None:
    """Variação percentual entre o primeiro e o último fechamento do período."""
    if len(candles) < 2 or not candles[0].close:
        return None
    return (candles[-1].close / candles[0].close - 1) * 100


def performance_stats(candles: Sequence[Candle]) -> PerformanceStats | None:
    """Calcula retorno, volatilidade anualizada e queda máxima em percentual."""
    closes = [candle.close for candle in candles if candle.close > 0]
    if len(closes) < 2:
        return None

    returns = [current / previous - 1 for previous, current in zip(closes, closes[1:], strict=False)]
    volatility = stdev(returns) * sqrt(TRADING_DAYS_PER_YEAR) * 100 if len(returns) >= 2 else None

    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = min(max_drawdown, close / peak - 1)

    return PerformanceStats(
        total_return=(closes[-1] / closes[0] - 1) * 100,
        annual_volatility=volatility,
        max_drawdown=max_drawdown * 100,
    )
