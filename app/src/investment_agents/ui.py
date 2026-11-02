"""Componentes compartilhados pela interface Streamlit."""

from __future__ import annotations

import logging

import requests
import streamlit as st

from investment_agents.integrations.ticker_client import get_latest
from investment_agents.services.ticker_catalog import load_ticker_catalog
from investment_agents.watchlist_db import add_ticker, get_tickers, replace_tickers

logger = logging.getLogger(__name__)

BACKEND_UNAVAILABLE_MESSAGE = (
    "Não foi possível conectar ao serviço de cotações. "
    "Verifique se o backend está em execução e tente novamente."
)


def show_backend_unavailable() -> None:
    """Exibe uma mensagem amigável sem expor detalhes técnicos da conexão."""
    st.info(BACKEND_UNAVAILABLE_MESSAGE)


def selected_symbols() -> list[str]:
    """Carrega a lista persistente na sessão do Streamlit."""
    if "selected_symbols" not in st.session_state:
        st.session_state.selected_symbols = get_tickers()
    return st.session_state.selected_symbols


def _persist_selected_symbols() -> None:
    replace_tickers(st.session_state.get("selected_symbols", []))


def _add_ticker_to_watchlist(ticker: str) -> None:
    ticker = ticker.strip().upper()
    if ticker:
        try:
            get_latest(ticker)
        except requests.HTTPError as error:
            status = error.response.status_code if error.response is not None else None
            if status == 404:
                notice = ("error", f"O ticker {ticker} não foi encontrado. Confira o símbolo.")
            else:
                logger.warning("Não foi possível validar o ticker %s", ticker, exc_info=True)
                notice = ("warning", "Não foi possível validar o ticker. Verifique o serviço e tente novamente.")
        except requests.RequestException:
            logger.warning("Backend indisponível ao validar o ticker %s", ticker, exc_info=True)
            notice = ("warning", "O serviço de cotações está indisponível; o ticker não foi salvo.")
        except Exception:
            logger.exception("Erro ao validar o ticker %s", ticker)
            notice = ("error", "Ocorreu um erro ao validar o ticker. Tente novamente.")
        else:
            added = add_ticker(ticker)
            st.session_state["selected_symbols"] = get_tickers()
            notice = (
                "success" if added else "info",
                f"Ticker {ticker} adicionado." if added else f"Ticker {ticker} já está cadastrado.",
            )
        st.session_state["ticker_add_notice"] = notice


def _add_manual_ticker_from_sidebar() -> None:
    _add_ticker_to_watchlist(st.session_state.get("new_ticker", ""))
    st.session_state["new_ticker"] = ""


def _add_catalog_ticker_from_sidebar() -> None:
    _add_ticker_to_watchlist(st.session_state.get("catalog_ticker", ""))


def render_sidebar() -> list[str]:
    st.sidebar.title("📈 Investimentos")
    st.sidebar.caption("Acompanhe e analise seus ativos")

    catalog = load_ticker_catalog()
    ticker_labels = {item.yahoo_ticker: item.label for item in catalog}
    if ticker_labels:
        st.sidebar.selectbox(
            "Escolher do catálogo",
            options=list(ticker_labels),
            format_func=ticker_labels.get,
            key="catalog_ticker",
        )
        st.sidebar.button(
            "Adicionar ticker do catálogo",
            key="add_catalog_ticker_button",
            on_click=_add_catalog_ticker_from_sidebar,
        )
    else:
        st.sidebar.caption("O catálogo de tickers está vazio ou indisponível.")

    ticker = st.sidebar.text_input(
        "Ou informar outro ticker",
        placeholder="Ex.: PETR4.SA ou AAPL",
        key="new_ticker",
    ).strip()
    st.sidebar.button(
        "Adicionar ticker informado",
        key="add_ticker_button",
        type="primary",
        disabled=not ticker,
        on_click=_add_manual_ticker_from_sidebar,
    )
    notice = st.session_state.pop("ticker_add_notice", None)
    if notice:
        level, message = notice
        getattr(st.sidebar, level)(message)

    symbols = selected_symbols()
    if symbols:
        return st.sidebar.multiselect(
            "Ações acompanhadas",
            options=symbols,
            key="selected_symbols",
            on_change=_persist_selected_symbols,
            help="A seleção é compartilhada entre as páginas.",
            placeholder="Escolha os tickers",
        )
    return []


def format_price(value: float, currency: str) -> str:
    symbol = "R$" if currency.upper() in {"BRL", "R$"} else currency
    return f"{symbol} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
