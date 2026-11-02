"""Ponto de entrada e navegação da plataforma."""

import sys
from pathlib import Path

# Garante que os diretórios do app e 'src' estejam no sys.path
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

for path in (str(BASE_DIR), str(SRC_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import streamlit as st

from investment_agents.watchlist_db import initialize_database
from views.analise import render as render_analise
from views.especialista import render as render_especialista
from views.home import render as render_home
from views.mercado import render as render_mercado


@st.cache_resource(show_spinner=False)
def _prepare_database() -> None:
    """Garante o banco uma única vez por processo, não a cada interação."""
    initialize_database()


st.set_page_config(
    page_title="Investimentos",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="expanded",
)

_prepare_database()

navigation = st.navigation(
    [
        st.Page(render_home, title="Início", icon=":material/home:", default=True),
        st.Page(render_mercado, title="Mercado", icon=":material/candlestick_chart:", url_path="mercado"),
        st.Page(render_analise, title="Análise", icon=":material/compare_arrows:", url_path="analise"),
        st.Page(
            render_especialista, title="Especialista", icon=":material/auto_awesome:", url_path="especialista"
        ),
    ],
    position="top",
)
navigation.run()
