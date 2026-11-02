"""Persistência SQLite da lista de ativos acompanhados."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.getenv("WATCHLIST_DB_PATH") or Path(__file__).resolve().parents[2] / "ativos.db")


@contextmanager
def _connection() -> Iterator[sqlite3.Connection]:
    """Abre uma conexão com commit automático e garante o fechamento dela."""
    connection = sqlite3.connect(DB_PATH)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_database() -> None:
    """Cria o arquivo do banco e a tabela de ativos, se ainda não existirem."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS ativos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL UNIQUE
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS preferencias (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """
        )


def get_preference(key: str) -> str | None:
    """Retorna uma preferência salva ou None, se ela nunca foi definida."""
    with _connection() as connection:
        row = connection.execute("SELECT valor FROM preferencias WHERE chave = ?", (key,)).fetchone()
    return row[0] if row else None


def set_preference(key: str, value: str) -> None:
    """Salva uma preferência, substituindo o valor anterior."""
    with _connection() as connection:
        connection.execute("INSERT OR REPLACE INTO preferencias (chave, valor) VALUES (?, ?)", (key, value))


def get_tickers() -> list[str]:
    """Retorna os tickers cadastrados, na ordem de inclusão."""
    with _connection() as connection:
        rows = connection.execute("SELECT ticker FROM ativos ORDER BY id").fetchall()
    return [row[0] for row in rows]


def add_ticker(ticker: str) -> bool:
    """Insere um ticker sem duplicar registros e indica se foi incluído."""
    normalized = ticker.strip().upper()
    if not normalized:
        return False
    with _connection() as connection:
        cursor = connection.execute("INSERT OR IGNORE INTO ativos (ticker) VALUES (?)", (normalized,))
    return cursor.rowcount > 0


def delete_ticker(ticker: str) -> bool:
    """Remove um ticker cadastrado pelo símbolo."""
    normalized = ticker.strip().upper()
    if not normalized:
        return False
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM ativos WHERE ticker = ?", (normalized,))
    return cursor.rowcount > 0
