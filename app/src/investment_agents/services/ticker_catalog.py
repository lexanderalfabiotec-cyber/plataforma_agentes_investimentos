"""Leitura do catálogo configurável de tickers."""

from __future__ import annotations

import csv
from dataclasses import dataclass
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


def load_ticker_catalog(path: Path = CATALOG_PATH) -> list[TickerOption]:
    """Carrega opções do CSV que contém Papel, Nome e YahooTicker."""
    options: list[TickerOption] = []
    seen: set[str] = set()
    if not path.is_file():
        return options

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
    return options
