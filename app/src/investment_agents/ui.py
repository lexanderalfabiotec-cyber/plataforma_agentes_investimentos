"""Componentes compartilhados pela interface Streamlit."""

from __future__ import annotations

import streamlit as st

DEFAULT_SYMBOLS = ["PETR4.SA", "VALE3.SA", "ITUB4.SA"]
BACKEND_UNAVAILABLE_MESSAGE = (
    "Não foi possível conectar ao serviço de cotações. "
    "Verifique se o backend está em execução e tente novamente."
)


def show_backend_unavailable() -> None:
    """Exibe uma mensagem amigável sem expor detalhes técnicos da conexão."""
    st.info(BACKEND_UNAVAILABLE_MESSAGE)


def selected_symbols() -> list[str]:
    """Mantém a seleção de ativos entre as páginas da aplicação."""
    if "selected_symbols" not in st.session_state:
        st.session_state.selected_symbols = DEFAULT_SYMBOLS.copy()
    return st.session_state.selected_symbols


def render_sidebar() -> list[str]:
    st.sidebar.title("📈 Investimentos")
    st.sidebar.caption("Acompanhe e analise seus ativos")
    return st.sidebar.multiselect(
        "Ações acompanhadas",
        options=sorted(set(DEFAULT_SYMBOLS + selected_symbols())),
        key="selected_symbols",
        help="A seleção é compartilhada entre as páginas e aparece na Home.",
        placeholder="Escolha os tickers",
    )


def format_price(value: float, currency: str) -> str:
    symbol = "R$" if currency.upper() in {"BRL", "R$"} else currency
    return f"{symbol} {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
