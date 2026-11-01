# ── Build stage ─────────────────────────────────────────────────────────────
FROM golang:1.24-alpine AS builder

# Instala dependências mínimas de build
RUN apk add --no-cache git ca-certificates tzdata

WORKDIR /app

# Copia go.mod (e go.sum se existir) e baixa dependências primeiro
# para aproveitar o cache de layers do Docker
COPY go.mod ./
RUN if [ -f go.sum ]; then cp go.sum .; fi
RUN go mod download

# Copia o restante do código-fonte
COPY . .

# Compila o binário estático sem CGO para máxima portabilidade
# Ponto de entrada: cmd/main.go (padrão do projeto Go com layout cmd/internal)
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 \
    go build -ldflags="-w -s" -o /bin/app ./cmd/main.go

# ── Runtime stage ────────────────────────────────────────────────────────────
# alpine em vez de scratch para ter wget disponível no healthcheck do Docker
FROM alpine:3.21 AS runtime

# Instala certificados TLS e wget (usado no healthcheck do docker-compose)
RUN apk add --no-cache ca-certificates tzdata wget

# Copia o binário compilado
COPY --from=builder /bin/app /app

# Porta padrão da API
EXPOSE 8080

# Define o fuso horário padrão
ENV TZ=America/Sao_Paulo

# Entrypoint: executa o binário diretamente
ENTRYPOINT ["/app"]
