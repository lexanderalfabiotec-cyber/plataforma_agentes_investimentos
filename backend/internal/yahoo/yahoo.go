package yahoo

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/cache"
)

// chartResponse mapeia a resposta da API do Yahoo Finance
type chartResponse struct {
	Chart struct {
		Result []struct {
			Meta struct {
				Symbol   string `json:"symbol"`
				Currency string `json:"currency"`
			} `json:"meta"`
			Timestamp  []int64 `json:"timestamp"`
			Indicators struct {
				Quote []struct {
					Open   []*float64 `json:"open"`
					High   []*float64 `json:"high"`
					Low    []*float64 `json:"low"`
					Close  []*float64 `json:"close"`
					Volume []*int64   `json:"volume"`
				} `json:"quote"`
			} `json:"indicators"`
		} `json:"result"`
		Error *struct {
			Code        string `json:"code"`
			Description string `json:"description"`
		} `json:"error"`
	} `json:"chart"`
}

// Candle representa um candle OHLCV
type Candle struct {
	Date   time.Time `json:"date"`
	Open   float64   `json:"open"`
	High   float64   `json:"high"`
	Low    float64   `json:"low"`
	Close  float64   `json:"close"`
	Volume int64     `json:"volume"`
}

// TickerInfo contém informações básicas de um ticker
type TickerInfo struct {
	Symbol   string   `json:"symbol"`
	Currency string   `json:"currency"`
	Candles  []Candle `json:"candles"`
}

var httpClient = &http.Client{Timeout: 15 * time.Second}

// baseURL é a URL base da API do Yahoo Finance.
// Exposta como variável de pacote para permitir substituição nos testes.
var baseURL = "https://query1.finance.yahoo.com/v8/finance/chart"

// ErrTickerNotFound identifies a symbol for which Yahoo has no quote data.
var ErrTickerNotFound = errors.New("ticker não encontrado")

// historyCache mantém as cotações recentes. O último candle muda durante o
// pregão, então o TTL precisa ser curto; a janela de stale cobre falhas e limites
// de requisição do Yahoo sem interromper o usuário.
var historyCache = cache.NewWithOptions[*TickerInfo](cache.Options{
	TTL:        60 * time.Second,
	StaleFor:   15 * time.Minute,
	MaxEntries: 2048,
})

// FetchHistory busca o histórico de candles de um ticker no Yahoo Finance.
// symbol: ex. "PETR4.SA" (B3) ou "AAPL" (NYSE)
// rng: ex. "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
// interval: ex. "1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"
func FetchHistory(symbol, rng, interval string) (*TickerInfo, error) {
	cacheKey := historyCacheKey(baseURL, symbol, rng, interval)
	return historyCache.GetOrLoad(cacheKey, func() (*TickerInfo, error) {
		info, err := requestHistory(symbol, rng, interval)
		if err != nil && !errors.Is(err, ErrTickerNotFound) {
			log.Printf("falha ao consultar Yahoo para %q: %v", symbol, err)
		}
		return info, err
	})
}

func requestHistory(symbol, rng, interval string) (*TickerInfo, error) {
	query := url.Values{"range": {rng}, "interval": {interval}}
	endpoint := baseURL + "/" + url.PathEscape(symbol) + "?" + query.Encode()

	req, err := http.NewRequest(http.MethodGet, endpoint, nil)
	if err != nil {
		return nil, fmt.Errorf("criar request: %w", err)
	}
	req.Header.Set("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)")

	resp, err := httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("executar request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(io.LimitReader(resp.Body, 512))
		if resp.StatusCode == http.StatusNotFound {
			return nil, fmt.Errorf("%w: %s", ErrTickerNotFound, strings.TrimSpace(string(body)))
		}
		return nil, fmt.Errorf("status %d: %s", resp.StatusCode, body)
	}

	var data chartResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, fmt.Errorf("decodificar resposta: %w", err)
	}
	if data.Chart.Error != nil {
		if strings.EqualFold(data.Chart.Error.Code, "Not Found") ||
			strings.Contains(strings.ToLower(data.Chart.Error.Description), "no data found") {
			return nil, fmt.Errorf("%w: %s", ErrTickerNotFound, data.Chart.Error.Description)
		}
		return nil, fmt.Errorf("yahoo error: %s", data.Chart.Error.Description)
	}
	if len(data.Chart.Result) == 0 || len(data.Chart.Result[0].Indicators.Quote) == 0 {
		return nil, fmt.Errorf("resposta vazia para %s", symbol)
	}

	r := data.Chart.Result[0]
	q := r.Indicators.Quote[0]
	candles := make([]Candle, 0, len(r.Timestamp))

	for i, ts := range r.Timestamp {
		// Yahoo devolve null em dias sem negociação e, às vezes, séries mais
		// curtas que os timestamps; nos dois casos o candle é descartado.
		open, high := valueAt(q.Open, i), valueAt(q.High, i)
		low, closePrice := valueAt(q.Low, i), valueAt(q.Close, i)
		if open == nil || high == nil || low == nil || closePrice == nil {
			continue
		}
		var vol int64
		if volume := valueAt(q.Volume, i); volume != nil {
			vol = *volume
		}
		candles = append(candles, Candle{
			Date:   time.Unix(ts, 0).UTC(),
			Open:   *open,
			High:   *high,
			Low:    *low,
			Close:  *closePrice,
			Volume: vol,
		})
	}

	return &TickerInfo{
		Symbol:   r.Meta.Symbol,
		Currency: r.Meta.Currency,
		Candles:  candles,
	}, nil
}

func valueAt[T any](values []*T, index int) *T {
	if index >= len(values) {
		return nil
	}
	return values[index]
}

// historyCacheKey uniquely identifies a request by ticker and all query parameters.
func historyCacheKey(endpoint, symbol, rng, interval string) string {
	params := url.Values{}
	params.Set("endpoint", endpoint)
	params.Set("symbol", symbol)
	params.Set("range", rng)
	params.Set("interval", interval)
	return params.Encode()
}
