package handlers

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"
	"regexp"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/yahoo"
)

// FetchFunc é o tipo da função que busca dados do Yahoo Finance.
// Permite injetar um stub nos testes sem bater na rede real.
type FetchFunc func(symbol, rng, interval string) (*yahoo.TickerInfo, error)

// defaultFetch é a implementação padrão (produção).
var defaultFetch FetchFunc = yahoo.FetchHistory

// symbolPattern aceita os formatos do Yahoo: PETR4.SA, BTC-USD, BRL=X, ^BVSP.
var symbolPattern = regexp.MustCompile(`^[A-Za-z0-9.^=-]{1,24}$`)

var (
	allowedRanges = map[string]bool{
		"1d": true, "5d": true, "1mo": true, "3mo": true, "6mo": true, "1y": true,
		"2y": true, "5y": true, "10y": true, "ytd": true, "max": true,
	}
	allowedIntervals = map[string]bool{
		"1m": true, "2m": true, "5m": true, "15m": true, "30m": true, "60m": true, "90m": true,
		"1h": true, "1d": true, "5d": true, "1wk": true, "1mo": true, "3mo": true,
	}
)

// ErrorResponse é a resposta padronizada de erro da API
type ErrorResponse struct {
	Error string `json:"error"`
}

// writeJSON é um helper para escrever JSON na resposta HTTP
func writeJSON(w http.ResponseWriter, statusCode int, data any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("erro ao serializar resposta: %v", err)
	}
}

// readSymbol valida o parâmetro symbol e responde 400 quando ele é inválido.
func readSymbol(w http.ResponseWriter, r *http.Request) (string, bool) {
	symbol := r.URL.Query().Get("symbol")
	if symbol == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'symbol' é obrigatório"})
		return "", false
	}
	if !symbolPattern.MatchString(symbol) {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'symbol' inválido"})
		return "", false
	}
	return symbol, true
}

// writeFetchError traduz falhas de consulta sem expor detalhes internos ao cliente.
func writeFetchError(w http.ResponseWriter, err error) {
	if errors.Is(err, yahoo.ErrTickerNotFound) {
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "ticker não encontrado ou sem dados disponíveis"})
		return
	}
	log.Printf("erro ao buscar dados: %v", err)
	writeJSON(w, http.StatusBadGateway, ErrorResponse{Error: "provedor de cotações indisponível no momento"})
}

// GetHistory retorna o histórico de candles de um ticker.
//
// Rota: GET /api/v1/history?symbol=PETR4.SA&range=1mo&interval=1d
//
// Query params:
//
//	symbol   - Ticker (obrigatório). Ex: PETR4.SA, AAPL
//	range    - Período   (opcional, default: 1mo). Ex: 1d, 5d, 1mo, 3mo, 6mo, 1y
//	interval - Resolução (opcional, default: 1d). Ex: 1m, 5m, 15m, 1h, 1d, 1wk
func GetHistory(w http.ResponseWriter, r *http.Request) {
	getHistoryWith(defaultFetch, w, r)
}

func getHistoryWith(fetch FetchFunc, w http.ResponseWriter, r *http.Request) {
	symbol, ok := readSymbol(w, r)
	if !ok {
		return
	}

	rng := r.URL.Query().Get("range")
	if rng == "" {
		rng = "1mo"
	}

	interval := r.URL.Query().Get("interval")
	if interval == "" {
		interval = "1d"
	}

	if !allowedRanges[rng] {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'range' inválido"})
		return
	}
	if !allowedIntervals[interval] {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'interval' inválido"})
		return
	}

	log.Printf("GET /history symbol=%s range=%s interval=%s", symbol, rng, interval)

	info, err := fetch(symbol, rng, interval)
	if err != nil {
		writeFetchError(w, err)
		return
	}

	writeJSON(w, http.StatusOK, info)
}

// GetLatest retorna somente o último candle (preço atual) de um ticker.
//
// Rota: GET /api/v1/latest?symbol=PETR4.SA
//
// Query params:
//
//	symbol - Ticker (obrigatório). Ex: PETR4.SA, AAPL
func GetLatest(w http.ResponseWriter, r *http.Request) {
	getLatestWith(defaultFetch, w, r)
}

func getLatestWith(fetch FetchFunc, w http.ResponseWriter, r *http.Request) {
	symbol, ok := readSymbol(w, r)
	if !ok {
		return
	}

	log.Printf("GET /latest symbol=%s", symbol)

	info, err := fetch(symbol, "5d", "1d")
	if err != nil {
		writeFetchError(w, err)
		return
	}

	if len(info.Candles) == 0 {
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "nenhum candle disponível"})
		return
	}

	last := info.Candles[len(info.Candles)-1]
	writeJSON(w, http.StatusOK, map[string]any{
		"symbol":   info.Symbol,
		"currency": info.Currency,
		"candle":   last,
	})
}
