"""Painel inicial com resumo dos ativos selecionados."""

import logging

import requests
import streamlit as st

from investment_agents.integrations.ticker_client import get_latest
from investment_agents.ui import format_price, render_sidebar, show_backend_unavailable

logger = logging.getLogger(__name__)

def render() -> None:
    symbols = render_sidebar()
    st.title("Especialista em Investimentos")
    st.caption("Bem-vindo ao Especialista em Investimentos! Selecione as ações que deseja analisar.")
    if not symbols:
        st.info("Selecione um ticker em Ações acompanhadas ou cadastre um pela barra lateral para começar.")
        return
