# 📈 Plataforma de Agentes de Investimentos

Plataforma para acompanhamento e análise técnica de investimentos financeiros utilizando uma arquitetura híbrida de microsserviços em **Go** e **Python**, alimentada por inteligência artificial com modelos de linguagem (LLMs) executados localmente via **Ollama**.

---

## 🏛️ Visão Geral da Arquitetura

A solução é composta por três módulos principais:

```
                      ┌──────────────────────────────────────┐
                      │          Interface / Usuário         │
                      └──────────────────┬───────────────────┘
                                         │
                                         ▼
┌─────────────────────────┐   HTTP/REST    ┌─────────────────────────┐
│     Backend em Go       │ ◄────────────► │     Aplicação Python    │
│  - Ingestão de Cotações │                │  - Especialista Técnico │
│  - Yahoo Finance API    │                │  - Indicadores Técnicos │
│  - Porta: 8080          │                │  - Streamlit (Porta 8501)│
└─────────────────────────┘                └────────────┬────────────┘
                                                        │
                                                        ▼
                                           ┌─────────────────────────┐
                                           │       Ollama LLM        │
                                           │  - Modelo local (lfm3)  │
                                           │  - Porta: 11434         │
                                           └─────────────────────────┘
```

1. **Backend Go (`backend/`)**:
   - Microsserviço de alta performance responsável pela ingestão e normalização de dados do mercado financeiro (Yahoo Finance).
   - Fornece endpoints REST para histórico de velas (*candles* OHLCV) e preços mais recentes.
   - Cache de 60 segundos com consultas simultâneas compartilhadas e uso dos últimos dados conhecidos, por até 15 minutos, quando o Yahoo falha.
   - Testes unitários e de integração com stubs/mocks.

2. **Aplicação (`app/`)**:
   - Interface web em **Streamlit** para acompanhar cotações, comparar ativos e consultar indicadores técnicos (SMA, RSI e MACD), calculados localmente.
   - **Especialista técnico**: gera, com um LLM local, um parecer em streaming a partir dos indicadores.
   - **Roadmap**: agentes de previsão, notícias e fundamentos, além de um comitê que consolida os pareceres. As dependências reservadas a eles estão em `app/requirements-ml.txt`.

3. **Ollama LLM**:
   - Execução local de modelos de IA com privacidade e controle total, sem dependência obrigatória de APIs pagas na nuvem.

### Páginas da interface

A interface Streamlit está organizada em páginas navegáveis no topo. Os ativos são adicionados e removidos em **Gerenciar ativos**, na barra lateral, e a seleção vale para todas as páginas.

| Página | Conteúdo |
|---|---|
| **Início** | Cards com preço, variação do dia e evolução recente de cada ativo |
| **Mercado** | Candles, volume, resumo do período e tabela de cotações |
| **Análise** | Comparação percentual, retorno, volatilidade e maior queda |
| **Especialista** | Indicadores técnicos e parecer gerado por IA |

---

## 📋 Pré-requisitos

### Para rodar com Docker (Recomendado)
- [Docker Engine](https://docs.docker.com/engine/install/) (v24.0+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)
- *(Opcional)* Placa de vídeo NVIDIA com drivers atualizados e [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) para aceleração por GPU.

### Para rodar sem Docker (Localmente)
- [Go](https://go.dev/dl/) 1.27.3 ou superior
- [Python](https://www.python.org/downloads/) 3.12 ou superior
- [Ollama](https://ollama.com/) instalado no sistema operacional
- `curl` ou utilitário equivalente para testes de API

---

## 🐳 Como Testar Usando o Docker

O `docker-compose.yml` orquestra todos os serviços necessários: Ollama, inicializador do modelo, backend Go e os agentes Python.

### 1. Configurar as variáveis de ambiente

Copie o arquivo de exemplo para criar seu `.env`:

```bash
cp .env.example .env
```

> [!NOTE]
> Com GPU NVIDIA, inclua o arquivo de GPU nos comandos: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build`.
>
> Se já houver um Ollama na máquina, troque `OLLAMA_PORT` no `.env` para evitar conflito na porta 11434.
>
> Para desenvolver com recarga do código Python, use `-f docker-compose.yml -f docker-compose.dev.yml`.

### 2. Construir e iniciar os contêineres

Execute o comando na raiz do projeto:

```bash
docker compose up --build
```

O compose executará o seguinte fluxo:
1. Inicia o servidor **Ollama** e, depois do healthcheck, o serviço `ollama-init` baixa o modelo em segundo plano.
2. Compila e inicia o **Backend Go** e aguarda seu healthcheck em `/health`.
3. Inicia a **aplicação Streamlit**. Cotações e indicadores já funcionam enquanto o modelo é baixado; o parecer da IA fica disponível quando o download termina.

As portas são publicadas somente em `127.0.0.1`, e a lista de ativos fica no volume `watchlist_data`.

Para rodar em segundo plano (*detached*), adicione a flag `-d`:

```bash
docker compose up -d
```

### 3. Verificar o status dos serviços

```bash
docker compose ps
```

### 4. Testar os endpoints e acessos

- **Healthcheck do Backend Go**:
  ```bash
  curl http://localhost:8080/health
  # Resposta esperada: {"status":"ok"}
  ```

- **Consulta da cotação mais recente (ex: Petrobras)**:
  ```bash
  curl "http://localhost:8080/api/v1/latest?symbol=PETR4.SA"
  ```

- **Consulta de histórico de candles (ex: Apple, 1 mês, diário)**:
  ```bash
  curl "http://localhost:8080/api/v1/history?symbol=AAPL&range=1mo&interval=1d"
  ```

- **Verificar se o modelo Ollama está pronto**:
  ```bash
  curl http://localhost:11434/api/tags
  ```

- **Interface dos Agentes (Streamlit)**:
  Acesse no seu navegador: [http://localhost:8501](http://localhost:8501)

### 5. Parar a aplicação

```bash
docker compose down
```

Para remover também os volumes persistidos (como os modelos baixados do Ollama):

```bash
docker compose down -v
```

---

## 💻 Como Testar Localmente Sem Usar o Docker

Para testar diretamente na sua máquina de desenvolvimento, execute cada componente individualmente seguindo os passos abaixo.

### Passo 1: Configurar e Iniciar o Ollama

1. Inicie o serviço do Ollama em um terminal:
   ```bash
   ollama serve
   ```

2. Em outro terminal, faça o download do modelo padrão (`lfm3`):
   ```bash
   ollama pull lfm3
   ```

3. Teste a execução do modelo:
   ```bash
   ollama run lfm3 "Olá! Responda em uma frase curta."
   ```

---

### Passo 2: Executar e Testar o Backend em Go

1. Acesse o diretório do backend:
   ```bash
   cd backend
   ```

2. **Executar a suíte de testes unitários e de integração**:
   ```bash
   go test -race ./...
   ```
   *Todos os testes devem passar com sucesso (`ok`).*

3. **Iniciar o servidor Go**:
   ```bash
   go run ./cmd/main.go
   ```
   *O backend estará escutando na porta `8080`.*

4. **Validar as rotas em outro terminal**:
   ```bash
   # 1. Healthcheck
   curl -i http://localhost:8080/health

   # 2. Preço mais recente de um ativo da B3
   curl -i "http://localhost:8080/api/v1/latest?symbol=PETR4.SA"

   # 3. Histórico de preços
   curl -i "http://localhost:8080/api/v1/history?symbol=VALE3.SA&range=5d&interval=1d"
   ```

---

### Passo 3: Executar e Testar os Agentes Python

1. Exporte as variáveis de ambiente no terminal (o `.env` é lido apenas pelo Docker Compose):
   ```bash
   export OLLAMA_HOST=http://localhost:11434
   export BACKEND_URL=http://localhost:8080
   ```

2. Acesse a pasta `app` e crie um ambiente virtual:
   ```bash
   cd app
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Executar os testes e o lint**:
   ```bash
   pip install -r requirements-dev.txt
   pytest
   ruff check .
   ```

5. **Testar a conexão com o backend Go**:
   ```bash
   PYTHONPATH=src python -c "from investment_agents.integrations import ticker_client; print('Status backend:', ticker_client.health_check()); print(ticker_client.get_latest('PETR4.SA'))"
   ```

6. **Iniciar a aplicação Streamlit**:
   ```bash
   streamlit run app.py
   ```
   Abra no seu navegador o endereço indicado (normalmente [http://localhost:8501](http://localhost:8501)).

---

## ⚙️ Variáveis de Ambiente

| Variável | Descrição | Padrão Local | Padrão Docker |
|---|---|---|---|
| `OLLAMA_HOST` | URL base do servidor Ollama | `http://localhost:11434` | `http://ollama:11434` |
| `BACKEND_URL` | URL base do backend Go consumido pelos agentes | `http://localhost:8080` | `http://backend:8080` |
| `OLLAMA_MODEL` | Modelo usado pelo especialista | `lfm3` | `lfm3` |
| `PORT` | Porta de escuta do backend Go | `8080` | `8080` |
| `WATCHLIST_DB_PATH` | Arquivo SQLite da lista de ativos | `app/ativos.db` | `/data/ativos.db` |
| `APP_PORT`, `BACKEND_PORT`, `OLLAMA_PORT` | Portas publicadas pelo Compose | — | `8501`, `8080`, `11434` |

---

## 📁 Estrutura de Diretórios

```
plataforma_agentes_investimentos/
├── docker-compose.yml        # Orquestração dos contêineres
├── docker-compose.gpu.yml    # Opcional: GPU NVIDIA para o Ollama
├── docker-compose.dev.yml    # Opcional: recarga do código Python
├── .env.example              # Modelo de variáveis de ambiente
├── backend/                  # Serviço de cotações em Go
│   ├── cmd/                  # Servidor HTTP e testes de integração
│   ├── internal/
│   │   ├── cache/            # Cache com TTL, carga compartilhada e dados de contingência
│   │   ├── handlers/         # Validação e handlers HTTP
│   │   └── yahoo/            # Cliente e parser do Yahoo Finance
│   └── Dockerfile
└── app/                      # Aplicação Python
    ├── app.py                # Entrada e navegação
    ├── .streamlit/           # Tema e configuração do Streamlit
    ├── config/               # Catálogo de tickers e configurações
    ├── views/                # Páginas da interface
    ├── src/investment_agents/
    │   ├── agents/           # Especialista técnico (LLM)
    │   ├── integrations/     # Cliente HTTP do backend Go
    │   ├── services/         # Dados de mercado, indicadores e catálogo
    │   ├── charts.py         # Gráficos Altair
    │   ├── formatting.py     # Formatação no padrão brasileiro
    │   ├── ui.py             # Componentes compartilhados da interface
    │   └── watchlist_db.py   # Persistência no SQLite
    ├── tests/                # Testes com pytest
    ├── requirements.txt      # Dependências do aplicativo
    ├── requirements-dev.txt  # Testes e lint
    └── requirements-ml.txt   # Reservado aos agentes do roadmap
```

> `views/` não pode se chamar `pages/`: o Streamlit trata essa pasta como páginas automáticas, o que quebra links diretos.

---

## 📄 Licença

Este projeto está licenciado sob os termos da licença [MIT](LICENSE).
