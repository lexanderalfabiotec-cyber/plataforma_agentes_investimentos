"""
ticker_client.py
================
Cliente HTTP para consumir a API de tickers do backend Go.

O backend Go expõe:
  GET /api/v1/history?symbol=<ticker>&range=<range>&interval=<interval>
  GET /api/v1/latest?symbol=<ticker>
  GET /health

Variáveis de ambiente:
  BACKEND_URL  – URL base do serviço Go (default: http://backend:8080)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# URL base do backend Go (dentro da rede Docker usa o nome do serviço)
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8080").rstrip("/")


def _make_session(retries: int = 3, backoff: float = 0.5) -> requests.Session:
    """Cria uma Session com retry automático em falhas de rede."""
    session = requests.Session()
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


_session = _make_session()


# ── Modelos de dados ──────────────────────────────────────────────────────────

@dataclass
class Candle:
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int

    @classmethod
    def from_dict(cls, d: dict) -> "Candle":
        return cls(
            date=datetime.fromisoformat(d["date"].replace("Z", "+00:00")),
            open=d["open"],
            high=d["high"],
            low=d["low"],
            close=d["close"],
            volume=d["volume"],
        )


@dataclass
class TickerHistory:
    symbol: str
    currency: str
    candles: list[Candle]

    @classmethod
    def from_dict(cls, d: dict) -> "TickerHistory":
        return cls(
            symbol=d["symbol"],
            currency=d["currency"],
            candles=[Candle.from_dict(c) for c in d.get("candles", [])],
        )


@dataclass
class LatestPrice:
    symbol: str
    currency: str
    candle: Candle

    @classmethod
    def from_dict(cls, d: dict) -> "LatestPrice":
        return cls(
            symbol=d["symbol"],
            currency=d["currency"],
            candle=Candle.from_dict(d["candle"]),
        )


# ── Funções públicas ──────────────────────────────────────────────────────────

def get_history(
    symbol: str,
    range: str = "1mo",
    interval: str = "1d",
    timeout: int = 20,
) -> TickerHistory:
    """
    Busca o histórico de candles de um ticker via backend Go.

    Args:
        symbol:   Ticker (ex: "PETR4.SA", "AAPL")
        range:    Período (ex: "1d","5d","1mo","3mo","6mo","1y","2y","5y","max")
        interval: Resolução (ex: "1m","5m","15m","1h","1d","1wk","1mo")
        timeout:  Timeout em segundos

    Returns:
        TickerHistory com lista de Candle

    Raises:
        requests.HTTPError: se o backend retornar erro HTTP
        requests.ConnectionError: se o backend não estiver disponível
    """
    url = f"{BACKEND_URL}/api/v1/history"
    params = {"symbol": symbol, "range": range, "interval": interval}

    logger.info("GET %s %s", url, params)
    resp = _session.get(url, params=params, timeout=timeout)

    if not resp.ok:
        err = resp.json().get("error", resp.text)
        logger.error("Erro do backend: %s", err)
        resp.raise_for_status()

    return TickerHistory.from_dict(resp.json())


def get_latest(symbol: str, timeout: int = 20) -> LatestPrice:
    """
    Retorna o último candle (preço mais recente) de um ticker.

    Args:
        symbol:  Ticker (ex: "PETR4.SA", "AAPL")
        timeout: Timeout em segundos

    Returns:
        LatestPrice com o candle mais recente

    Raises:
        requests.HTTPError: se o backend retornar erro HTTP
        requests.ConnectionError: se o backend não estiver disponível
    """
    url = f"{BACKEND_URL}/api/v1/latest"
    params = {"symbol": symbol}

    logger.info("GET %s %s", url, params)
    resp = _session.get(url, params=params, timeout=timeout)

    if not resp.ok:
        err = resp.json().get("error", resp.text)
        logger.error("Erro do backend: %s", err)
        resp.raise_for_status()

    return LatestPrice.from_dict(resp.json())


def health_check(timeout: int = 5) -> bool:
    """
    Verifica se o backend Go está disponível.

    Returns:
        True se o backend responder com status 200, False caso contrário
    """
    try:
        resp = _session.get(f"{BACKEND_URL}/health", timeout=timeout)
        return resp.ok
    except requests.RequestException as e:
        logger.warning("Backend Go não disponível: %s", e)
        return False
