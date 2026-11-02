"""Alternância entre os temas claro e escuro.

O Streamlit não tem API pública para trocar o tema em tempo de execução. A opção
``theme.base`` é reenviada ao navegador a cada execução do script, então alterá-la
muda o tema sem recarregar a página nem perder o estado da sessão. A opção vale para
todo o processo, como a lista de ativos, que também é única por instância.
"""

from __future__ import annotations

import streamlit as st
from streamlit import config

from investment_agents.watchlist_db import get_preference, set_preference

THEMES = ("light", "dark")

_PREFERENCE_KEY = "tema"
_WIDGET_KEY = "theme_selector"
_CONTAINER_KEY = "theme_toggle"
_ICONS = {"light": ":material/light_mode:", "dark": ":material/dark_mode:"}

# A chave do contêiner vira a classe CSS usada para fixá-lo no cabeçalho.
_STYLE = f"""
<style>
.st-key-{_CONTAINER_KEY} {{
    position: fixed;
    top: 0.45rem;
    right: 1rem;
    width: auto;
    z-index: 999991;
}}
</style>
"""


def sync_saved_theme() -> bool:
    """Aplica o tema salvo, se for diferente do atual, e indica se houve mudança."""
    saved = get_preference(_PREFERENCE_KEY)
    if saved not in THEMES or saved == config.get_option("theme.base"):
        return False
    config.set_option("theme.base", saved)
    return True


def theme_type() -> str:
    """Retorna o tema em uso, para os gráficos usarem as cores corretas."""
    # st.context.theme não serve aqui: ele segue o sistema operacional mesmo quando
    # a página está em outro tema.
    return "dark" if config.get_option("theme.base") == "dark" else "light"


def _save_selection() -> None:
    # Clicar na opção ativa devolve None; nesse caso, nada muda.
    selected = st.session_state.get(_WIDGET_KEY)
    if selected in THEMES:
        set_preference(_PREFERENCE_KEY, selected)


def render_theme_toggle() -> None:
    """Desenha o seletor de sol e lua no canto superior direito."""
    # O tema enviado ao navegador é lido no início de cada execução. Depois de
    # um clique ou de reiniciar o servidor, só a execução seguinte leva o novo valor.
    if sync_saved_theme():
        st.rerun()

    st.session_state[_WIDGET_KEY] = theme_type()
    st.html(_STYLE)
    with st.container(key=_CONTAINER_KEY):
        st.segmented_control(
            "Tema",
            options=THEMES,
            format_func=_ICONS.get,
            key=_WIDGET_KEY,
            on_change=_save_selection,
            label_visibility="collapsed",
            width="content",
        )
