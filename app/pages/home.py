"""Painel inicial com resumo dos ativos selecionados."""

import logging

import requests
import streamlit as st

from investment_agents.integrations.ticker_client import get_latest
from investment_agents.ui import format_price, render_sidebar, show_backend_unavailable

logger = logging.getLogger(__name__)


def render() -> None:
    symbols = render_sidebar()
    st.title("Visão geral")
    st.caption("Resumo das ações que você está acompanhando.")
    if not symbols:
        st.info("Selecione ações na barra lateral ou abra Ações selecionadas para começar.")
        return

    columns = st.columns(min(len(symbols), 4))
    backend_unavailable = False
    for index, symbol in enumerate(symbols):
        with columns[index % len(columns)]:
            try:
                latest = get_latest(symbol)
                candle = latest.candle
                change = ((candle.close - candle.open) / candle.open * 100) if candle.open else 0
                st.metric(symbol, format_price(candle.close, latest.currency), f"{change:+.2f}% no período")
                st.caption(f"Máx. {format_price(candle.high, latest.currency)} · Mín. {format_price(candle.low, latest.currency)}")
            except Exception as error:
                logger.warning("Falha ao carregar cotação de %s", symbol, exc_info=True)
                if isinstance(error, requests.RequestException):
                    backend_unavailable = True
                else:
                    st.warning(f"Não foi possível carregar os dados de {symbol}.")

    if backend_unavailable:
        show_backend_unavailable()

    st.divider()
    st.subheader("Ativos acompanhados")
    st.write("Use Mercado para consultar o histórico e Análise para comparar o desempenho dos ativos.")
