package handlers

// ─────────────────────────────────────────────────────────────────────────────
// Testes do pacote handlers
//
// Estratégia: injetamos um FetchFunc stub via getHistoryWith / getLatestWith.
// Nenhuma chamada real à internet é feita.
//
// Cobertura:
//   GetHistory:
//     - symbol ausente → 400 Bad Request
//     - defaults de range e interval preenchidos
//     - parâmetros passados explicitamente
//     - FetchFunc retorna erro → 502 Bad Gateway
//     - resposta feliz → 200 OK com JSON correto
//
//   GetLatest:
//     - symbol ausente → 400 Bad Request
//     - FetchFunc retorna erro → 502 Bad Gateway
//     - sem candles → 404 Not Found
//     - resposta feliz → 200 OK com último candle
//     - sempre usa range="5d" interval="1d"
//
//   writeJSON (helper):
//     - Content-Type correto
//     - status code propagado
//
//   Benchmarks:
//     - BenchmarkGetHistory  – handler completo (stub de rede)
//     - BenchmarkGetLatest   – handler completo (stub de rede)
//     - BenchmarkWriteJSON   – serialização JSON pura
// ─────────────────────────────────────────────────────────────────────────────

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/yahoo"
)

// ── helpers ───────────────────────────────────────────────────────────────────

func ptr[T any](v T) *T { return &v }

// makeTickerInfo cria um TickerInfo com n candles de teste.
func makeTickerInfo(symbol, currency string, n int) *yahoo.TickerInfo {
	candles := make([]yahoo.Candle, n)
	for i := range n {
		candles[i] = yahoo.Candle{
			Date:   time.Unix(int64(1_700_000_000+i*86400), 0).UTC(),
			Open:   10.0 + float64(i),
			High:   11.0 + float64(i),
			Low:    9.0 + float64(i),
			Close:  10.5 + float64(i),
			Volume: int64(1_000_000 + i*1000),
		}
	}
	return &yahoo.TickerInfo{Symbol: symbol, Currency: currency, Candles: candles}
}

// stubFetch retorna um FetchFunc que sempre devolve o resultado fornecido.
func stubFetch(info *yahoo.TickerInfo, err error) FetchFunc {
	return func(_, _, _ string) (*yahoo.TickerInfo, error) { return info, err }
}

// captureFetch retorna um FetchFunc que captura os argumentos da chamada.
type fetchCall struct{ symbol, rng, interval string }

func captureFetch(info *yahoo.TickerInfo, err error, out *fetchCall) FetchFunc {
	return func(sym, rng, intv string) (*yahoo.TickerInfo, error) {
		*out = fetchCall{sym, rng, intv}
		return info, err
	}
}

// doRequest executa um handler e retorna o ResponseRecorder.
func doRequest(handler http.HandlerFunc, method, target string) *httptest.ResponseRecorder {
	req := httptest.NewRequest(method, target, nil)
	w := httptest.NewRecorder()
	handler(w, req)
	return w
}

// decodeBody decodifica o JSON do ResponseRecorder em v.
func decodeBody(t *testing.T, rr *httptest.ResponseRecorder, v any) {
	t.Helper()
	if err := json.NewDecoder(rr.Body).Decode(v); err != nil {
		t.Fatalf("falha ao decodificar body: %v\nbody=%s", err, rr.Body.String())
	}
}

// ── GetHistory ────────────────────────────────────────────────────────────────

func TestGetHistory_MissingSymbol(t *testing.T) {
	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getHistoryWith(stubFetch(nil, nil), w, r)
		},
		http.MethodGet, "/api/v1/history",
	)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("status: got %d, want %d", rr.Code, http.StatusBadRequest)
	}

	var resp ErrorResponse
	decodeBody(t, rr, &resp)
	if resp.Error == "" {
		t.Error("campo 'error' não deve ser vazio")
	}
	if !strings.Contains(resp.Error, "symbol") {
		t.Errorf("mensagem deve mencionar 'symbol': %q", resp.Error)
	}
}

func TestGetHistory_DefaultRangeAndInterval(t *testing.T) {
	var call fetchCall
	info := makeTickerInfo("PETR4.SA", "BRL", 3)

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getHistoryWith(captureFetch(info, nil, &call), w, r)
		},
		http.MethodGet, "/api/v1/history?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusOK {
		t.Errorf("status: got %d, want 200", rr.Code)
	}
	if call.rng != "1mo" {
		t.Errorf("range default: got %q, want %q", call.rng, "1mo")
	}
	if call.interval != "1d" {
		t.Errorf("interval default: got %q, want %q", call.interval, "1d")
	}
}

func TestGetHistory_ExplicitParams(t *testing.T) {
	var call fetchCall
	info := makeTickerInfo("AAPL", "USD", 10)

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getHistoryWith(captureFetch(info, nil, &call), w, r)
		},
		http.MethodGet, "/api/v1/history?symbol=AAPL&range=3mo&interval=1wk",
	)

	if rr.Code != http.StatusOK {
		t.Errorf("status: got %d, want 200", rr.Code)
	}
	if call.symbol != "AAPL" {
		t.Errorf("symbol: got %q, want AAPL", call.symbol)
	}
	if call.rng != "3mo" {
		t.Errorf("range: got %q, want 3mo", call.rng)
	}
	if call.interval != "1wk" {
		t.Errorf("interval: got %q, want 1wk", call.interval)
	}
}

func TestGetHistory_FetchError(t *testing.T) {
	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getHistoryWith(stubFetch(nil, errors.New("timeout")), w, r)
		},
		http.MethodGet, "/api/v1/history?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusBadGateway {
		t.Errorf("status: got %d, want %d", rr.Code, http.StatusBadGateway)
	}
	var resp ErrorResponse
	decodeBody(t, rr, &resp)
	if strings.Contains(resp.Error, "timeout") {
		t.Errorf("detalhes internos não devem chegar ao cliente: %q", resp.Error)
	}
}

func TestGetHistory_Success(t *testing.T) {
	info := makeTickerInfo("PETR4.SA", "BRL", 5)

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getHistoryWith(stubFetch(info, nil), w, r)
		},
		http.MethodGet, "/api/v1/history?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusOK {
		t.Errorf("status: got %d, want 200", rr.Code)
	}
	if ct := rr.Header().Get("Content-Type"); !strings.Contains(ct, "application/json") {
		t.Errorf("Content-Type: got %q, want application/json", ct)
	}

	var result yahoo.TickerInfo
	decodeBody(t, rr, &result)

	if result.Symbol != "PETR4.SA" {
		t.Errorf("Symbol: got %q, want PETR4.SA", result.Symbol)
	}
	if result.Currency != "BRL" {
		t.Errorf("Currency: got %q, want BRL", result.Currency)
	}
	if len(result.Candles) != 5 {
		t.Errorf("Candles: got %d, want 5", len(result.Candles))
	}
}

// ── GetLatest ─────────────────────────────────────────────────────────────────

func TestGetLatest_MissingSymbol(t *testing.T) {
	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(stubFetch(nil, nil), w, r)
		},
		http.MethodGet, "/api/v1/latest",
	)

	if rr.Code != http.StatusBadRequest {
		t.Errorf("status: got %d, want %d", rr.Code, http.StatusBadRequest)
	}
}

func TestGetLatest_AlwaysUses5dAnd1d(t *testing.T) {
	var call fetchCall
	info := makeTickerInfo("PETR4.SA", "BRL", 3)

	doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(captureFetch(info, nil, &call), w, r)
		},
		http.MethodGet, "/api/v1/latest?symbol=PETR4.SA",
	)

	if call.rng != "5d" {
		t.Errorf("GetLatest deve usar range=5d, got %q", call.rng)
	}
	if call.interval != "1d" {
		t.Errorf("GetLatest deve usar interval=1d, got %q", call.interval)
	}
}

func TestGetLatest_FetchError(t *testing.T) {
	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(stubFetch(nil, errors.New("conexão recusada")), w, r)
		},
		http.MethodGet, "/api/v1/latest?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusBadGateway {
		t.Errorf("status: got %d, want %d", rr.Code, http.StatusBadGateway)
	}
}

func TestGetLatest_EmptyCandles(t *testing.T) {
	info := &yahoo.TickerInfo{Symbol: "PETR4.SA", Currency: "BRL", Candles: nil}

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(stubFetch(info, nil), w, r)
		},
		http.MethodGet, "/api/v1/latest?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusNotFound {
		t.Errorf("status: got %d, want %d", rr.Code, http.StatusNotFound)
	}
}

func TestGetLatest_Success(t *testing.T) {
	info := makeTickerInfo("PETR4.SA", "BRL", 3)
	lastExpected := info.Candles[len(info.Candles)-1]

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(stubFetch(info, nil), w, r)
		},
		http.MethodGet, "/api/v1/latest?symbol=PETR4.SA",
	)

	if rr.Code != http.StatusOK {
		t.Errorf("status: got %d, want 200", rr.Code)
	}

	var result struct {
		Symbol   string       `json:"symbol"`
		Currency string       `json:"currency"`
		Candle   yahoo.Candle `json:"candle"`
	}
	decodeBody(t, rr, &result)

	if result.Symbol != "PETR4.SA" {
		t.Errorf("Symbol: got %q, want PETR4.SA", result.Symbol)
	}
	if result.Candle.Close != lastExpected.Close {
		t.Errorf("Close: got %.2f, want %.2f", result.Candle.Close, lastExpected.Close)
	}
	if result.Candle.Volume != lastExpected.Volume {
		t.Errorf("Volume: got %d, want %d", result.Candle.Volume, lastExpected.Volume)
	}
}

// TestGetLatest_ReturnsLastCandle garante que é o ÚLTIMO candle (não o primeiro).
func TestGetLatest_ReturnsLastCandle(t *testing.T) {
	info := makeTickerInfo("AAPL", "USD", 5)
	expectedClose := info.Candles[4].Close // índice 4 = último

	rr := doRequest(
		func(w http.ResponseWriter, r *http.Request) {
			getLatestWith(stubFetch(info, nil), w, r)
		},
		http.MethodGet, "/api/v1/latest?symbol=AAPL",
	)

	var result struct {
		Candle yahoo.Candle `json:"candle"`
	}
	decodeBody(t, rr, &result)

	if result.Candle.Close != expectedClose {
		t.Errorf("deve retornar o último candle: got Close=%.2f, want %.2f",
			result.Candle.Close, expectedClose)
	}
}

// ── writeJSON helper ──────────────────────────────────────────────────────────

func TestWriteJSON_ContentType(t *testing.T) {
	w := httptest.NewRecorder()
	writeJSON(w, http.StatusCreated, map[string]string{"key": "value"})

	if w.Code != http.StatusCreated {
		t.Errorf("status: got %d, want 201", w.Code)
	}
	ct := w.Header().Get("Content-Type")
	if !strings.Contains(ct, "application/json") {
		t.Errorf("Content-Type: got %q, want application/json", ct)
	}
}

func TestWriteJSON_Body(t *testing.T) {
	type payload struct {
		Name  string `json:"name"`
		Value int    `json:"value"`
	}
	w := httptest.NewRecorder()
	writeJSON(w, http.StatusOK, payload{Name: "teste", Value: 42})

	var result payload
	if err := json.NewDecoder(w.Body).Decode(&result); err != nil {
		t.Fatalf("decodificar body: %v", err)
	}
	if result.Name != "teste" || result.Value != 42 {
		t.Errorf("body inesperado: %+v", result)
	}
}

// ── benchmarks ────────────────────────────────────────────────────────────────

func BenchmarkGetHistory(b *testing.B) {
	info := makeTickerInfo("PETR4.SA", "BRL", 252)
	fetch := stubFetch(info, nil)

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/history?symbol=PETR4.SA&range=1y&interval=1d", nil)
		w := httptest.NewRecorder()
		getHistoryWith(fetch, w, req)
	}
}

func BenchmarkGetLatest(b *testing.B) {
	info := makeTickerInfo("PETR4.SA", "BRL", 5)
	fetch := stubFetch(info, nil)

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		req := httptest.NewRequest(http.MethodGet, "/api/v1/latest?symbol=PETR4.SA", nil)
		w := httptest.NewRecorder()
		getLatestWith(fetch, w, req)
	}
}

func BenchmarkWriteJSON(b *testing.B) {
	info := makeTickerInfo("PETR4.SA", "BRL", 252)

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		w := httptest.NewRecorder()
		writeJSON(w, http.StatusOK, info)
	}
}

func TestGetHistory_RejectsInvalidParams(t *testing.T) {
	cases := map[string]string{
		"symbol com query":   "symbol=PETR4.SA%3Finterval%3D1m",
		"symbol com caminho": "symbol=..%2F..%2Fv7%2Ffinance",
		"symbol muito longo": "symbol=" + strings.Repeat("A", 25),
		"range inválido":     "symbol=PETR4.SA&range=abc",
		"interval inválido":  "symbol=PETR4.SA&interval=zzz",
	}
	for name, query := range cases {
		t.Run(name, func(t *testing.T) {
			called := false
			fetch := func(_, _, _ string) (*yahoo.TickerInfo, error) {
				called = true
				return nil, nil
			}
			rr := doRequest(
				func(w http.ResponseWriter, r *http.Request) { getHistoryWith(fetch, w, r) },
				http.MethodGet, "/api/v1/history?"+query,
			)
			if rr.Code != http.StatusBadRequest {
				t.Errorf("status: got %d, want %d", rr.Code, http.StatusBadRequest)
			}
			if called {
				t.Error("parâmetros inválidos não devem chegar ao Yahoo")
			}
		})
	}
}

func TestGetLatest_AcceptsYahooSymbolFormats(t *testing.T) {
	for _, symbol := range []string{"PETR4.SA", "AAPL", "BTC-USD", "BRL=X", "%5EBVSP"} {
		fetch := func(_, _, _ string) (*yahoo.TickerInfo, error) {
			return &yahoo.TickerInfo{Symbol: symbol, Candles: []yahoo.Candle{{Close: 1}}}, nil
		}
		rr := doRequest(
			func(w http.ResponseWriter, r *http.Request) { getLatestWith(fetch, w, r) },
			http.MethodGet, "/api/v1/latest?symbol="+symbol,
		)
		if rr.Code != http.StatusOK {
			t.Errorf("%s: status %d, esperado 200", symbol, rr.Code)
		}
	}
}
