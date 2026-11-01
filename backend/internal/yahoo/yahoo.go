package yahoo

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
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

var historyCache = cache.New[*TickerInfo]()

// FetchHistory busca o histórico de candles de um ticker no Yahoo Finance.
// symbol: ex. "PETR4.SA" (B3) ou "AAPL" (NYSE)
// rng: ex. "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"
// interval: ex. "1m", "5m", "15m", "30m", "60m", "1d", "1wk", "1mo"
func FetchHistory(symbol, rng, interval string) (*TickerInfo, error) {
	cacheKey := historyCacheKey(baseURL, symbol, rng, interval)
	if info, ok := historyCache.Get(cacheKey); ok {
		return info, nil
	}

	url := fmt.Sprintf(
		"%s/%s?range=%s&interval=%s",
		baseURL, symbol, rng, interval,
	)

	req, err := http.NewRequest(http.MethodGet, url, nil)
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
		return nil, fmt.Errorf("status %d: %s", resp.StatusCode, body)
	}

	var data chartResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, fmt.Errorf("decodificar resposta: %w", err)
	}
	if data.Chart.Error != nil {
		return nil, fmt.Errorf("yahoo error: %s", data.Chart.Error.Description)
	}
	if len(data.Chart.Result) == 0 || len(data.Chart.Result[0].Indicators.Quote) == 0 {
		return nil, fmt.Errorf("resposta vazia para %s", symbol)
	}

	r := data.Chart.Result[0]
	q := r.Indicators.Quote[0]
	candles := make([]Candle, 0, len(r.Timestamp))

	for i, ts := range r.Timestamp {
		// Yahoo devolve null em dias sem negociação → ponteiro nil
		if q.Close[i] == nil || q.Open[i] == nil || q.High[i] == nil || q.Low[i] == nil {
			continue
		}
		var vol int64
		if q.Volume[i] != nil {
			vol = *q.Volume[i]
		}
		candles = append(candles, Candle{
			Date:   time.Unix(ts, 0).UTC(),
			Open:   *q.Open[i],
			High:   *q.High[i],
			Low:    *q.Low[i],
			Close:  *q.Close[i],
			Volume: vol,
		})
	}

	info := &TickerInfo{
		Symbol:   r.Meta.Symbol,
		Currency: r.Meta.Currency,
		Candles:  candles,
	}
	historyCache.Set(cacheKey, info)
	return info, nil
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
