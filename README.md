# 📈 Plataforma de Agentes de Investimentos

Plataforma inteligente para análise e recomendação de investimentos financeiros utilizando uma arquitetura híbrida de microsserviços em **Go** e **Python**, alimentada por inteligência artificial com modelos de linguagem (LLMs) executados localmente via **Ollama**.

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
│     Backend em Go       │ ◄────────────► │     Agentes Python      │
│  - Ingestão de Cotações │                │  - Agentes Especialistas│
│  - Yahoo Finance API    │                │  - Comitê de Decisão    │
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
   - Fornece endpoints REST rápidos para histórico de velas (*candles* OHLCV) e preços em tempo real/mais recentes.
   - Cobertura completa de testes unitários e de integração com stubs/mocks.

2. **Agentes Inteligentes (`agentes/`)**:
   - Sistema multi-agente em Python alimentado por LLM local (`lfm3`) e análise de dados.
   - **Agentes Especialistas**:
     - *Previsão de Preços*: Análise de tendência e séries temporais.
     - *Técnico*: Análise quantitativa com indicadores (RSI, MACD, MME).
     - *Notícias*: Mineração de notícias via DuckDuckGo e análise de sentimento.
     - *Fundamentalista*: Avaliação de balanços e métricas contábeis.
   - **Comitê Avaliador**: Sintetiza as recomendações dos especialistas para emitir parecer consolidado (`COMPRAR`, `VENDER` ou `ESPERAR`).
   - Interface interativa web desenvolvida com **Streamlit**.

3. **Ollama LLM**:
   - Execução local de modelos de IA com privacidade e controle total, sem dependência obrigatória de APIs pagas na nuvem.

---

## 📋 Pré-requisitos

### Para rodar com Docker (Recomendado)
- [Docker Engine](https://docs.docker.com/engine/install/) (v24.0+)
- [Docker Compose](https://docs.docker.com/compose/) (v2.0+)
- *(Opcional)* Placa de vídeo NVIDIA com drivers atualizados e [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) para aceleração por GPU.

### Para rodar sem Docker (Localmente)
- [Go](https://go.dev/dl/) 1.22 ou superior (desenvolvido com Go 1.24)
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
> Se você **não** possui GPU NVIDIA disponível no host, abra o arquivo `docker-compose.yml` e comente o bloco `deploy` do serviço `ollama` (linhas 22 a 28):
> ```yaml
> # deploy:
> #   resources:
> #     reservations:
> #       devices:
> #         - driver: nvidia
> #           count: all
> #           capabilities: [gpu]
> ```

### 2. Construir e iniciar os contêineres

Execute o comando na raiz do projeto:

```bash
docker compose up --build
```

O compose executará o seguinte fluxo:
1. Inicia o servidor **Ollama** e aguarda o healthcheck.
2. Dispara o serviço auxiliar `ollama-init` que baixa automaticamente o modelo `lfm3`.
3. Compila e inicia o **Backend Go** e aguarda seu healthcheck em `/health`.
4. Inicia o contêiner de **Agentes Python** com a aplicação Streamlit.

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
   go test -v ./...
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

1. Na raiz do projeto ou diretório `agentes`, configure as variáveis de ambiente para execução local:
   ```bash
   # Na raiz do projeto:
   cp .env.example .env
   ```

   Certifique-se de que o `.env` ou seu terminal contenha:
   ```bash
   export OLLAMA_HOST=http://localhost:11434
   export BACKEND_URL=http://localhost:8080
   ```

2. Acesse a pasta `agentes` e crie um ambiente virtual:
   ```bash
   cd agentes
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Testar a integração com o Ollama e cliente de tickers**:
   Execute o script de teste do agente:
   ```bash
   python app.py
   ```

   Você também pode testar a conexão com o backend Go via Python interativo:
   ```python
   python -c "import ticker_client; print('Status backend:', ticker_client.health_check()); print(ticker_client.get_latest('PETR4.SA'))"
   ```

5. **Iniciar a aplicação Streamlit**:
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
| `PORT` | Porta de escuta do backend Go | `8080` | `8080` |

---

## 📁 Estrutura de Diretórios

```
plataforma_agentes_investimentos/
├── docker-compose.yml        # Orquestração dos contêineres (Ollama, Go, Python)
├── .env.example              # Modelo de variáveis de ambiente
├── README.md                 # Documentação do projeto
├── backend/                  # Serviço de cotações e dados em Go
│   ├── cmd/
│   │   ├── main.go           # Ponto de entrada do servidor HTTP
│   │   └── server_test.go    # Testes de integração do servidor
│   ├── internal/
│   │   ├── handlers/         # Handlers HTTP (/health, /api/v1/latest, /api/v1/history)
│   │   └── yahoo/            # Cliente e parser do Yahoo Finance
│   ├── Dockerfile            # Multi-stage build para imagem enxuta em Alpine
│   └── go.mod                # Módulo Go
└── agentes/                  # Aplicação em Python e agentes de IA
    ├── app.py                # Interface e orquestração dos agentes
    ├── ticker_client.py      # Cliente HTTP para consumo do backend Go
    ├── config.yaml           # Configurações de modelos, prompts e fontes de notícias
    ├── Util.py               # Utilitários de apoio, imagens e limpeza
    ├── requirements.txt      # Dependências Python (Streamlit, TensorFlow, Ollama, etc.)
    └── Dockerfile            # Multi-stage build com usuário não-root
```

---

## 📄 Licença

Este projeto está licenciado sob os termos da licença [MIT](LICENSE).
