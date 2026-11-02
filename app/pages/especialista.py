"""Painel inicial com resumo dos ativos selecionados."""

import logging

import streamlit as st

from investment_agents.ui import render_sidebar
from investment_agents.agents.specialist_agent import get_specialist_advice

logger = logging.getLogger(__name__)

def render() -> None:
    symbols = render_sidebar()
    st.title("Especialista em Investimentos")
    st.caption("Bem-vindo ao Especialista em Investimentos! Selecione as ações que deseja analisar.")
    if not symbols:
        st.info("Selecione um ticker em Ações acompanhadas ou cadastre um pela barra lateral para começar.")
        return

