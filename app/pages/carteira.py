"""Gerenciamento da lista de ativos acompanhados."""

import logging

import requests
import streamlit as st

from investment_agents.integrations.ticker_client import get_latest
from investment_agents.ui import format_price, render_sidebar, show_backend_unavailable

logger = logging.getLogger(__name__)


def render() -> None:
    symbols = render_sidebar()
    st.title("Ações selecionadas")
    st.caption("Escolha os ativos que serão exibidos no resumo da Home.")
    ticker = st.text_input("Adicionar ticker", placeholder="Ex.: BOVA11.SA ou AAPL").strip().upper()
    if st.button("Adicionar à lista", type="primary", disabled=not ticker):
        if ticker not in symbols:
            st.session_state.selected_symbols = symbols + [ticker]
        st.rerun()

    if not symbols:
        st.info("Sua lista está vazia. Adicione um ticker acima ou escolha ativos na barra lateral.")
        return

    rows = []
    backend_unavailable = False
    for symbol in symbols:
        try:
            latest = get_latest(symbol)
            candle = latest.candle
            rows.append({"Ticker": symbol, "Último preço": format_price(candle.close, latest.currency), "Abertura": format_price(candle.open, latest.currency), "Máxima": format_price(candle.high, latest.currency), "Mínima": format_price(candle.low, latest.currency)})
        except Exception as error:
            logger.warning("Falha ao carregar cotação de %s", symbol, exc_info=True)
            if isinstance(error, requests.RequestException):
                backend_unavailable = True
            rows.append({"Ticker": symbol, "Último preço": "Indisponível", "Abertura": "—", "Máxima": "—", "Mínima": "—"})
    if backend_unavailable:
        show_backend_unavailable()
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("Para remover um ativo, desmarque-o no seletor da barra lateral.")
