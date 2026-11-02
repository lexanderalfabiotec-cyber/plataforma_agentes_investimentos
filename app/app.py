"""Ponto de entrada e navegação da plataforma."""

from pathlib import Path
import sys

# Garante que os diretórios do app e 'src' estejam no sys.path
BASE_DIR = Path(__file__).resolve().parent
SRC_DIR = BASE_DIR / "src"

for path in (str(BASE_DIR), str(SRC_DIR)):
    if path not in sys.path:
        sys.path.insert(0, path)

import streamlit as st

from pages.analise import render as render_analise
from pages.carteira import render as render_carteira
from pages.home import render as render_home
from pages.mercado import render as render_mercado
from pages.especialista import render as render_especialista

st.set_page_config(
    page_title="Investimentos | Painel",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

navigation = st.navigation(
    [
        st.Page(render_home, title="Início", icon="🏠", url_path="inicio", default=True),
        st.Page(render_especialista, title="Especialista", icon="💡", url_path="especialista"),
        st.Page(render_mercado, title="Mercado", icon="📊", url_path="mercado"),
        st.Page(render_analise, title="Análise", icon="🔎", url_path="analise"),
        st.Page(render_carteira, title="Ações selecionadas", icon="⭐", url_path="acoes-selecionadas"),
    ],
    position="top",
)
navigation.run()
