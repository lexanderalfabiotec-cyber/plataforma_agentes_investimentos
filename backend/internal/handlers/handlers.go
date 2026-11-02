package handlers

import (
	"encoding/json"
	"errors"
	"log"
	"net/http"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/yahoo"
)

// FetchFunc é o tipo da função que busca dados do Yahoo Finance.
// Permite injetar um stub nos testes sem bater na rede real.
type FetchFunc func(symbol, rng, interval string) (*yahoo.TickerInfo, error)

// defaultFetch é a implementação padrão (produção).
var defaultFetch FetchFunc = yahoo.FetchHistory

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
	symbol := r.URL.Query().Get("symbol")
	if symbol == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'symbol' é obrigatório"})
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

	log.Printf("GET /history symbol=%s range=%s interval=%s", symbol, rng, interval)

	info, err := fetch(symbol, rng, interval)
	if err != nil {
		if errors.Is(err, yahoo.ErrTickerNotFound) {
			writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "ticker não encontrado ou sem dados disponíveis"})
			return
		}
		log.Printf("erro ao buscar dados: %v", err)
		writeJSON(w, http.StatusBadGateway, ErrorResponse{Error: err.Error()})
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
	symbol := r.URL.Query().Get("symbol")
	if symbol == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "parâmetro 'symbol' é obrigatório"})
		return
	}

	log.Printf("GET /latest symbol=%s", symbol)

	info, err := fetch(symbol, "5d", "1d")
	if err != nil {
		if errors.Is(err, yahoo.ErrTickerNotFound) {
			writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "ticker não encontrado ou sem dados disponíveis"})
			return
		}
		log.Printf("erro ao buscar dados: %v", err)
		writeJSON(w, http.StatusBadGateway, ErrorResponse{Error: err.Error()})
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
