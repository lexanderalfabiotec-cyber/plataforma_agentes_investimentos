"""Agente especialista em investimentos."""

import os

import streamlit as st
from openai import OpenAI

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
client = OpenAI(base_url=f"{OLLAMA_HOST}/v1", api_key="ollama")


@st.cache_data(ttl=300, show_spinner=False)
def get_specialist_advice(ticker_info: str) -> str:
    message = (
        "Interprete tendência, momentum e riscos usando somente estes dados. "
        f"{ticker_info}\n"
        "Retorne o resumo em markdown\n"
        "# Especialista em Investimentos\n"
        "## Resumo de Investimento\n"
        "1. Tendência (subindo, caindo ou lateral).\n"
        "2. Momentum (forte, moderado ou fraco).\n"
        "3. Risco (baixo, moderado ou alto).\n"
        "4. Recomendação (comprar, vender ou manter).\n"
        "## Conclusão\n"
        "Retorne o resumo em markdown\n"
    )

    response = client.chat.completions.create(
        model="lfm3",
        messages=[
            {"role": "system", "content": "Você é um assistente financeiro."},
            {"role": "user", "content": message},
        ],
        temperature=0.1,
        stream=False
    )
    return response.choices[0].message.content or ""
