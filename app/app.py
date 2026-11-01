"""Ponto de entrada e navegação da plataforma."""

import streamlit as st

from pages.analise import render as render_analise
from pages.carteira import render as render_carteira
from pages.home import render as render_home
from pages.mercado import render as render_mercado

st.set_page_config(
    page_title="Investimentos | Painel",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

navigation = st.navigation(
    [
        st.Page(render_home, title="Início", icon="🏠", default=True),
        st.Page(render_mercado, title="Mercado", icon="📊"),
        st.Page(render_analise, title="Análise", icon="🔎"),
        st.Page(render_carteira, title="Ações selecionadas", icon="⭐"),
    ],
    position="top",
)
navigation.run()
