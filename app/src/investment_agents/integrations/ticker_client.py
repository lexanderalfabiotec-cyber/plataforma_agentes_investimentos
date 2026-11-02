"""
ticker_client.py
================
Cliente HTTP para consumir a API de tickers do backend Go.

O backend Go expõe:
  GET /api/v1/history?symbol=<ticker>&range=<range>&interval=<interval>
  GET /api/v1/latest?symbol=<ticker>
  GET /health

Variáveis de ambiente:
  BACKEND_URL  – URL base do serviço Go (localhost localmente; backend no Docker)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


def _backend_url() -> str:
    """Usa o DNS do Compose no container e localhost na execução local."""
    configured_url = os.getenv("BACKEND_URL")
    in_docker = os.path.exists("/.dockerenv")
    url = configured_url or ("http://backend:8080" if in_docker else "http://localhost:8080")

    # O nome "backend" só é resolvido pela rede interna do Docker Compose.
    # Se o Streamlit foi iniciado diretamente na máquina, use a porta publicada.
    parsed = urlsplit(url)
    if not in_docker and parsed.hostname == "backend":
        netloc = f"localhost:{parsed.port or 8080}"
        url = urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    return url.rstrip("/")


BACKEND_URL = _backend_url()


# Conexão falha rápido; a leitura precisa cobrir o timeout do backend com o Yahoo.
DEFAULT_TIMEOUT = (3.0, 20.0)
POOL_SIZE = 16


class MarketDataError(Exception):
    """Falha ao obter dados de mercado."""


class TickerNotFoundError(MarketDataError):
    """O ticker é inválido ou não possui dados."""


class ServiceUnavailableError(MarketDataError):
    """O backend de cotações não pode ser alcançado."""


class ProviderError(MarketDataError):
    """O backend respondeu, mas o provedor de cotações falhou."""


def _make_session(retries: int = 1, backoff: float = 0.2) -> requests.Session:
    """Cria uma Session reutilizável, com retry apenas em falhas de conexão.

    Erros de status não são repetidos: um 502 normalmente indica limite de
    requisições do Yahoo, e insistir só atrasa a resposta e agrava o limite.
    """
    session = requests.Session()
    retry = Retry(
        total=retries,
        connect=retries,
        read=0,
        status=0,
        other=0,
        backoff_factor=backoff,
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=POOL_SIZE, pool_maxsize=POOL_SIZE)
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
    def from_dict(cls, d: dict) -> Candle:
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
    def from_dict(cls, d: dict) -> TickerHistory:
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
    def from_dict(cls, d: dict) -> LatestPrice:
        return cls(
            symbol=d["symbol"],
            currency=d["currency"],
            candle=Candle.from_dict(d["candle"]),
        )


# ── Funções públicas ──────────────────────────────────────────────────────────


def _get_json(path: str, params: dict[str, str], timeout: float | tuple[float, float]) -> dict:
    """Executa o GET e traduz falhas para as exceções do módulo."""
    url = f"{BACKEND_URL}{path}"
    logger.debug("GET %s %s", url, params)
    try:
        response = _session.get(url, params=params, timeout=timeout)
    except requests.RequestException as error:
        raise ServiceUnavailableError("backend de cotações indisponível") from error

    # 400 ocorre quando o símbolo tem formato inválido: para o usuário, é o
    # mesmo caso de um ticker inexistente.
    if response.status_code in (400, 404):
        raise TickerNotFoundError(params.get("symbol", ""))
    if not response.ok:
        logger.warning("Backend respondeu %s para %s", response.status_code, params)
        raise ProviderError(f"status {response.status_code}")
    try:
        return response.json()
    except ValueError as error:
        raise ProviderError("resposta inválida do backend") from error


def get_history(
    symbol: str,
    range: str = "1mo",
    interval: str = "1d",
    timeout: float | tuple[float, float] = DEFAULT_TIMEOUT,
) -> TickerHistory:
    """
    Busca o histórico de candles de um ticker via backend Go.

    Args:
        symbol:   Ticker (ex: "PETR4.SA", "AAPL")
        range:    Período (ex: "1d","5d","1mo","3mo","6mo","1y","2y","5y","max")
        interval: Resolução (ex: "1m","5m","15m","1h","1d","1wk","1mo")
        timeout:  Timeout em segundos, ou a tupla (conexão, leitura)

    Raises:
        TickerNotFoundError: ticker inválido ou sem dados
        ProviderError: o provedor de cotações falhou
        ServiceUnavailableError: o backend não está acessível
    """
    params = {"symbol": symbol, "range": range, "interval": interval}
    return TickerHistory.from_dict(_get_json("/api/v1/history", params, timeout))


def get_latest(symbol: str, timeout: float | tuple[float, float] = DEFAULT_TIMEOUT) -> LatestPrice:
    """
    Retorna o último candle (preço mais recente) de um ticker.

    Raises:
        TickerNotFoundError: ticker inválido ou sem dados
        ProviderError: o provedor de cotações falhou
        ServiceUnavailableError: o backend não está acessível
    """
    return LatestPrice.from_dict(_get_json("/api/v1/latest", {"symbol": symbol}, timeout))


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
