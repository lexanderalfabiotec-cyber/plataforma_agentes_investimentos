# ── Build stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Evita arquivos .pyc e garante saída de log imediata
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências do sistema necessárias para compilar pacotes nativos
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependências Python em um virtualenv isolado
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Cria usuário não-root para segurança
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app
ENV PYTHONPATH="/app/src"

# Copia o virtualenv do stage anterior
COPY --from=builder /opt/venv /opt/venv

# Copia o código da aplicação
COPY --chown=appuser:appgroup . .

USER appuser

# Porta padrão do Streamlit (ajuste se necessário)
EXPOSE 8501

# Healthcheck básico
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Inicia o ponto de entrada Python via Streamlit
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
