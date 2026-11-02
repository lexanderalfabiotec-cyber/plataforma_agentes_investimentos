"""Persistência SQLite da lista de ativos acompanhados."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from collections.abc import Iterable

DB_PATH = Path(__file__).resolve().parents[2] / "ativos.db"


def initialize_database() -> None:
    """Cria o arquivo do banco e a tabela de ativos, se ainda não existirem."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ativos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE
            )
            """
        )


def get_tickers() -> list[str]:
    """Retorna os tickers cadastrados, na ordem de inclusão."""
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute("SELECT ticker FROM ativos ORDER BY id").fetchall()
    return [row[0] for row in rows]


def add_ticker(ticker: str) -> bool:
    """Insere um ticker sem duplicar registros e indica se foi incluído."""
    normalized = ticker.strip().upper()
    if not normalized:
        return False
    with sqlite3.connect(DB_PATH) as connection:
        cursor = connection.execute(
            "INSERT OR IGNORE INTO ativos (ticker) VALUES (?)", (normalized,)
        )
    return cursor.rowcount > 0


def replace_tickers(tickers: Iterable[str]) -> None:
    """Sincroniza a tabela com a seleção atual da barra lateral."""
    normalized = list(dict.fromkeys(ticker.strip().upper() for ticker in tickers if ticker.strip()))
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("DELETE FROM ativos")
        connection.executemany(
            "INSERT INTO ativos (ticker) VALUES (?)",
            [(ticker,) for ticker in normalized],
        )
