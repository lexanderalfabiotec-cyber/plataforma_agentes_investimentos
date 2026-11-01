"""Gerenciamento da lista de ativos acompanhados."""

import streamlit as st

from investment_agents.integrations.ticker_client import get_latest
from investment_agents.ui import format_price, render_sidebar


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
    for symbol in symbols:
        try:
            latest = get_latest(symbol)
            candle = latest.candle
            rows.append({"Ticker": symbol, "Último preço": format_price(candle.close, latest.currency), "Abertura": format_price(candle.open, latest.currency), "Máxima": format_price(candle.high, latest.currency), "Mínima": format_price(candle.low, latest.currency)})
        except Exception as error:
            rows.append({"Ticker": symbol, "Último preço": "Indisponível", "Abertura": "—", "Máxima": "—", "Mínima": str(error)})
    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption("Para remover um ativo, desmarque-o no seletor da barra lateral.")
