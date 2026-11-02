"""Leitura do catálogo configurável de tickers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[3] / "config" / "ticker.csv"


@dataclass(frozen=True)
class TickerOption:
    papel: str
    nome: str
    yahoo_ticker: str

    @property
    def label(self) -> str:
        description = " — ".join(part for part in (self.papel, self.nome) if part)
        return f"{description} ({self.yahoo_ticker})" if description else self.yahoo_ticker


@lru_cache(maxsize=4)
def load_ticker_catalog(path: Path = CATALOG_PATH) -> tuple[TickerOption, ...]:
    """Carrega uma única vez as opções do CSV com Papel, Nome e YahooTicker."""
    options: list[TickerOption] = []
    seen: set[str] = set()
    if not path.is_file():
        return ()

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        for row in csv.DictReader(csv_file):
            yahoo_ticker = (row.get("YahooTicker") or "").strip().upper()
            if not yahoo_ticker or yahoo_ticker in seen:
                continue
            seen.add(yahoo_ticker)
            options.append(
                TickerOption(
                    papel=(row.get("Papel") or "").strip().upper(),
                    nome=(row.get("Nome") or "").strip(),
                    yahoo_ticker=yahoo_ticker,
                )
            )
    return tuple(options)


def resolve_ticker(text: str, catalog: tuple[TickerOption, ...] | None = None) -> str:
    """Normaliza o texto digitado; 'petr4' vira 'PETR4.SA' quando está no catálogo."""
    normalized = text.strip().upper()
    options = load_ticker_catalog() if catalog is None else catalog
    for option in options:
        if normalized == option.papel:
            return option.yahoo_ticker
    return normalized


def company_name(symbol: str, catalog: tuple[TickerOption, ...] | None = None) -> str:
    """Retorna o nome do catálogo ou uma string vazia para tickers fora dele."""
    options = load_ticker_catalog() if catalog is None else catalog
    return next((option.nome for option in options if option.yahoo_ticker == symbol), "")
