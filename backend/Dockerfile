# ── Build stage ─────────────────────────────────────────────────────────────
# A versão precisa acompanhar a diretiva "go" do go.mod: a imagem oficial usa
# GOTOOLCHAIN=local e não baixa outra toolchain.
FROM golang:1.27-alpine AS builder

WORKDIR /src

# go.mod é copiado primeiro para aproveitar o cache de layers do Docker
COPY go.mod ./
RUN go mod download

COPY . .

# Binário estático sem CGO para máxima portabilidade
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-w -s" -o /bin/app ./cmd

# ── Runtime stage ────────────────────────────────────────────────────────────
# alpine em vez de scratch para ter wget (BusyBox) no healthcheck do Compose
FROM alpine:3.21 AS runtime

RUN apk add --no-cache ca-certificates tzdata

COPY --from=builder /bin/app /app

ENV TZ=America/Sao_Paulo

EXPOSE 8080

USER nobody

ENTRYPOINT ["/app"]
