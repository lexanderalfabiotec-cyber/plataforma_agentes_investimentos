package yahoo

// ─────────────────────────────────────────────────────────────────────────────
// Testes do pacote yahoo
//
// Estratégia: substituímos o httpClient global por um httptest.Server que serve
// respostas JSON controladas — sem precisar de acesso à internet.
//
// Cobertura:
//   - parseamento correto de resposta válida
//   - filtragem de candles com campos nulos (dias sem negociação)
//   - volume nulo tratado como zero
//   - erro retornado pela API do Yahoo (campo chart.error)
//   - resposta com result vazio
//   - status HTTP ≠ 200 (ex.: 429 Too Many Requests)
//   - JSON malformado
//   - URL/host inválido (falha de conexão)
//
// Benchmarks:
//   - BenchmarkFetchHistory    – ciclo completo (handler + parser) contra servidor local
//   - BenchmarkParseCandles    – apenas o loop de parsing de candles (CPU bound)
//   - BenchmarkWriteJSON       – serialização JSON da resposta final
// ─────────────────────────────────────────────────────────────────────────────

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

// ── helpers ──────────────────────────────────────────────────────────────────

// ptr retorna um ponteiro para o valor passado (evita verbosidade nos fixtures).
func ptr[T any](v T) *T { return &v }

// fakeYahooServer cria um httptest.Server que responde com body e status fixos.
// Retorna o servidor e um cleanup via t.Cleanup.
func fakeYahooServer(t *testing.T, statusCode int, body string) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(statusCode)
		fmt.Fprint(w, body)
	}))
	t.Cleanup(srv.Close)
	return srv
}

// overrideClient substitui o httpClient global do pacote pelo client do servidor
// de teste e restaura o original ao término do teste.
func overrideClient(t *testing.T, srv *httptest.Server) {
	t.Helper()
	original := httpClient
	httpClient = srv.Client()
	t.Cleanup(func() { httpClient = original })
}

// overrideBaseURL substitui a URL de produção do Yahoo Finance por um prefixo
// que aponta para o servidor de teste (usa monkey-patching via variável de pacote).
// Para isso, precisamos de uma variável exportável — veja a nota abaixo.
//
// Como o pacote constrói a URL inline em FetchHistory, injetamos o server via
// um campo de URL base que podemos sobrescrever nos testes.
func serveAndPoint(t *testing.T, statusCode int, body string) {
	t.Helper()
	srv := fakeYahooServer(t, statusCode, body)
	overrideClient(t, srv)
	// Sobrescreve a baseURL do pacote para redirecionar as requisições
	origBase := baseURL
	baseURL = srv.URL + "/v8/finance/chart"
	t.Cleanup(func() { baseURL = origBase })
}

// ── fixtures JSON ─────────────────────────────────────────────────────────────

// validPayload gera uma resposta completa do Yahoo Finance com n candles.
func validPayload(symbol, currency string, n int) string {
	timestamps := make([]int64, n)
	open := make([]string, n)
	high := make([]string, n)
	low := make([]string, n)
	close_ := make([]string, n)
	volume := make([]string, n)

	base := int64(1_700_000_000)
	for i := range n {
		timestamps[i] = base + int64(i)*86400
		open[i] = fmt.Sprintf("%.2f", 10.0+float64(i))
		high[i] = fmt.Sprintf("%.2f", 11.0+float64(i))
		low[i] = fmt.Sprintf("%.2f", 9.0+float64(i))
		close_[i] = fmt.Sprintf("%.2f", 10.5+float64(i))
		volume[i] = fmt.Sprintf("%d", 1_000_000+i*1000)
	}

	toJSON := func(ss []string) string { return "[" + strings.Join(ss, ",") + "]" }
	tsJSON := func(ts []int64) string {
		parts := make([]string, len(ts))
		for i, v := range ts {
			parts[i] = fmt.Sprintf("%d", v)
		}
		return "[" + strings.Join(parts, ",") + "]"
	}

	return fmt.Sprintf(`{
		"chart": {
			"result": [{
				"meta": {"symbol": %q, "currency": %q},
				"timestamp": %s,
				"indicators": {
					"quote": [{
						"open":   %s,
						"high":   %s,
						"low":    %s,
						"close":  %s,
						"volume": %s
					}]
				}
			}],
			"error": null
		}
	}`, symbol, currency,
		tsJSON(timestamps),
		toJSON(open), toJSON(high), toJSON(low), toJSON(close_), toJSON(volume))
}

// payloadWithNulls inclui candles com campos null (dias sem negociação).
const payloadWithNulls = `{
	"chart": {
		"result": [{
			"meta": {"symbol": "PETR4.SA", "currency": "BRL"},
			"timestamp": [1700000000, 1700086400, 1700172800],
			"indicators": {
				"quote": [{
					"open":   [10.0, null, 12.0],
					"high":   [11.0, null, 13.0],
					"low":    [9.0,  null, 11.0],
					"close":  [10.5, null, 12.5],
					"volume": [1000000, null, 1200000]
				}]
			}
		}],
		"error": null
	}
}`

// payloadNullVolume inclui um candle com volume null (deve virar 0).
const payloadNullVolume = `{
	"chart": {
		"result": [{
			"meta": {"symbol": "AAPL", "currency": "USD"},
			"timestamp": [1700000000],
			"indicators": {
				"quote": [{
					"open":   [150.0],
					"high":   [155.0],
					"low":    [149.0],
					"close":  [153.0],
					"volume": [null]
				}]
			}
		}],
		"error": null
	}
}`

const payloadYahooError = `{
	"chart": {
		"result": null,
		"error": {
			"code": "Not Found",
			"description": "No fundamentals data found for any of the summaryTypes=financialData"
		}
	}
}`

const payloadEmptyResult = `{
	"chart": {
		"result": [],
		"error": null
	}
}`

// ── testes unitários ─────────────────────────────────────────────────────────

func TestFetchHistory_ValidResponse(t *testing.T) {
	const (
		symbol   = "PETR4.SA"
		currency = "BRL"
		n        = 5
	)

	serveAndPoint(t, http.StatusOK, validPayload(symbol, currency, n))

	info, err := FetchHistory(symbol, "1mo", "1d")
	if err != nil {
		t.Fatalf("esperava sucesso, got erro: %v", err)
	}

	if info.Symbol != symbol {
		t.Errorf("Symbol: got %q, want %q", info.Symbol, symbol)
	}
	if info.Currency != currency {
		t.Errorf("Currency: got %q, want %q", info.Currency, currency)
	}
	if len(info.Candles) != n {
		t.Errorf("Candles: got %d, want %d", len(info.Candles), n)
	}

	// Verifica o primeiro candle
	c := info.Candles[0]
	if c.Open != 10.0 {
		t.Errorf("Candle[0].Open: got %.2f, want 10.00", c.Open)
	}
	if c.High != 11.0 {
		t.Errorf("Candle[0].High: got %.2f, want 11.00", c.High)
	}
	if c.Low != 9.0 {
		t.Errorf("Candle[0].Low: got %.2f, want 9.00", c.Low)
	}
	if c.Volume != 1_000_000 {
		t.Errorf("Candle[0].Volume: got %d, want 1000000", c.Volume)
	}
	if c.Date.IsZero() {
		t.Error("Candle[0].Date não deve ser zero")
	}
}

func TestFetchHistory_CachesBySymbolAndParameters(t *testing.T) {
	var requests int
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requests++
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, validPayload(r.URL.Path, "USD", 1))
	}))
	t.Cleanup(srv.Close)
	overrideClient(t, srv)

	origBase := baseURL
	baseURL = srv.URL
	t.Cleanup(func() { baseURL = origBase })

	first, err := FetchHistory("AAPL", "1mo", "1d")
	if err != nil {
		t.Fatalf("primeira busca falhou: %v", err)
	}
	second, err := FetchHistory("AAPL", "1mo", "1d")
	if err != nil {
		t.Fatalf("busca repetida falhou: %v", err)
	}
	if first != second {
		t.Error("busca repetida deveria retornar o valor armazenado no cache")
	}
	if requests != 1 {
		t.Fatalf("mesma chave fez %d requests; esperado 1", requests)
	}

	for _, args := range [][3]string{
		{"AAPL", "5d", "1d"},
		{"AAPL", "1mo", "1wk"},
		{"MSFT", "1mo", "1d"},
	} {
		if _, err := FetchHistory(args[0], args[1], args[2]); err != nil {
			t.Fatalf("busca com parâmetros %v falhou: %v", args, err)
		}
	}
	if requests != 4 {
		t.Errorf("chaves diferentes fizeram %d requests; esperado 4", requests)
	}
}

func TestFetchHistory_NullCandlesSkipped(t *testing.T) {
	serveAndPoint(t, http.StatusOK, payloadWithNulls)

	info, err := FetchHistory("PETR4.SA", "1mo", "1d")
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}

	// O candle do meio tem campos null → deve ser descartado (3 → 2 candles)
	if len(info.Candles) != 2 {
		t.Errorf("esperava 2 candles (null filtrado), got %d", len(info.Candles))
	}
}

func TestFetchHistory_NullVolumeTreatedAsZero(t *testing.T) {
	serveAndPoint(t, http.StatusOK, payloadNullVolume)

	info, err := FetchHistory("AAPL", "5d", "1d")
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if len(info.Candles) != 1 {
		t.Fatalf("esperava 1 candle, got %d", len(info.Candles))
	}
	if info.Candles[0].Volume != 0 {
		t.Errorf("Volume null deve ser 0, got %d", info.Candles[0].Volume)
	}
}

func TestFetchHistory_YahooError(t *testing.T) {
	serveAndPoint(t, http.StatusOK, payloadYahooError)

	_, err := FetchHistory("INVALIDO", "1mo", "1d")
	if err == nil {
		t.Fatal("esperava erro (yahoo error), got nil")
	}
	if !strings.Contains(err.Error(), "yahoo error") {
		t.Errorf("mensagem de erro inesperada: %v", err)
	}
}

func TestFetchHistory_EmptyResult(t *testing.T) {
	serveAndPoint(t, http.StatusOK, payloadEmptyResult)

	_, err := FetchHistory("INVALIDO", "1mo", "1d")
	if err == nil {
		t.Fatal("esperava erro (resultado vazio), got nil")
	}
	if !strings.Contains(err.Error(), "resposta vazia") {
		t.Errorf("mensagem de erro inesperada: %v", err)
	}
}

func TestFetchHistory_NonOKStatus(t *testing.T) {
	serveAndPoint(t, http.StatusTooManyRequests, `{"message":"rate limit"}`)

	_, err := FetchHistory("PETR4.SA", "1mo", "1d")
	if err == nil {
		t.Fatal("esperava erro (status 429), got nil")
	}
	if !strings.Contains(err.Error(), "429") {
		t.Errorf("mensagem de erro deve conter status code: %v", err)
	}
}

func TestFetchHistory_MalformedJSON(t *testing.T) {
	serveAndPoint(t, http.StatusOK, `{ broken json `)

	_, err := FetchHistory("PETR4.SA", "1mo", "1d")
	if err == nil {
		t.Fatal("esperava erro (JSON malformado), got nil")
	}
	if !strings.Contains(err.Error(), "decodificar") {
		t.Errorf("mensagem de erro inesperada: %v", err)
	}
}

func TestFetchHistory_ConnectionError(t *testing.T) {
	// Aponta para uma porta que não existe (sem servidor rodando)
	origBase := baseURL
	baseURL = "http://127.0.0.1:1" // porta fechada
	t.Cleanup(func() { baseURL = origBase })

	_, err := FetchHistory("PETR4.SA", "1mo", "1d")
	if err == nil {
		t.Fatal("esperava erro de conexão, got nil")
	}
	if !strings.Contains(err.Error(), "executar request") {
		t.Errorf("mensagem de erro inesperada: %v", err)
	}
}

// TestFetchHistory_CandleDateUTC garante que o timestamp é convertido para UTC.
func TestFetchHistory_CandleDateUTC(t *testing.T) {
	serveAndPoint(t, http.StatusOK, validPayload("AAPL", "USD", 1))

	info, err := FetchHistory("AAPL", "1d", "1d")
	if err != nil {
		t.Fatalf("erro inesperado: %v", err)
	}
	if info.Candles[0].Date.Location() != time.UTC {
		t.Errorf("Date deve estar em UTC, got %v", info.Candles[0].Date.Location())
	}
}

// TestFetchHistory_DefaultParams verifica que a URL é construída com os params corretos.
func TestFetchHistory_URLBuilding(t *testing.T) {
	var capturedURL string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		capturedURL = r.URL.String()
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, validPayload("PETR4.SA", "BRL", 1))
	}))
	t.Cleanup(srv.Close)
	overrideClient(t, srv)

	origBase := baseURL
	baseURL = srv.URL + "/v8/finance/chart"
	t.Cleanup(func() { baseURL = origBase })

	_, _ = FetchHistory("PETR4.SA", "3mo", "1wk")

	if !strings.Contains(capturedURL, "PETR4.SA") {
		t.Errorf("URL deve conter o símbolo: %s", capturedURL)
	}
	if !strings.Contains(capturedURL, "range=3mo") {
		t.Errorf("URL deve conter range=3mo: %s", capturedURL)
	}
	if !strings.Contains(capturedURL, "interval=1wk") {
		t.Errorf("URL deve conter interval=1wk: %s", capturedURL)
	}
}

// ── testes de tabela ──────────────────────────────────────────────────────────

func TestFetchHistory_StatusCodes(t *testing.T) {
	cases := []struct {
		name       string
		statusCode int
		wantErr    bool
	}{
		{"ok_200", http.StatusOK, false},
		{"not_found_404", http.StatusNotFound, true},
		{"rate_limit_429", http.StatusTooManyRequests, true},
		{"server_error_500", http.StatusInternalServerError, true},
		{"bad_gateway_502", http.StatusBadGateway, true},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			body := validPayload("PETR4.SA", "BRL", 2)
			if tc.statusCode != http.StatusOK {
				body = `{"error":"simulated"}`
			}
			serveAndPoint(t, tc.statusCode, body)

			_, err := FetchHistory("PETR4.SA", "1mo", "1d")
			if tc.wantErr && err == nil {
				t.Errorf("status %d: esperava erro, got nil", tc.statusCode)
			}
			if !tc.wantErr && err != nil {
				t.Errorf("status %d: erro inesperado: %v", tc.statusCode, err)
			}
		})
	}
}

// ── testes de integração (marcados com -run=Integration ou t.Short) ───────────

// TestFetchHistory_Integration faz uma chamada REAL ao Yahoo Finance.
// Pulado em modo curto (go test -short).
func TestFetchHistory_Integration(t *testing.T) {
	if testing.Short() {
		t.Skip("pulando teste de integração (use go test sem -short)")
	}

	info, err := FetchHistory("PETR4.SA", "5d", "1d")
	if err != nil {
		t.Fatalf("chamada real falhou: %v", err)
	}
	if info.Symbol == "" {
		t.Error("Symbol não deve ser vazio")
	}
	if len(info.Candles) == 0 {
		t.Error("deve retornar pelo menos 1 candle")
	}
}

// ── benchmarks ────────────────────────────────────────────────────────────────

// BenchmarkFetchHistory mede o ciclo completo (HTTP round-trip + parse) contra
// um servidor local (sem latência de rede real).
func BenchmarkFetchHistory(b *testing.B) {
	body := validPayload("PETR4.SA", "BRL", 252) // 1 ano de candles diários

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, body)
	}))
	b.Cleanup(srv.Close)

	original := httpClient
	httpClient = srv.Client()
	b.Cleanup(func() { httpClient = original })

	origBase := baseURL
	baseURL = srv.URL + "/v8/finance/chart"
	b.Cleanup(func() { baseURL = origBase })

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		_, err := FetchHistory("PETR4.SA", "1y", "1d")
		if err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkParseCandles mede exclusivamente o loop de construção dos candles
// a partir de dados já decodificados (sem I/O).
func BenchmarkParseCandles(b *testing.B) {
	const n = 252
	base := int64(1_700_000_000)

	timestamps := make([]int64, n)
	openV := make([]*float64, n)
	highV := make([]*float64, n)
	lowV := make([]*float64, n)
	closeV := make([]*float64, n)
	volumeV := make([]*int64, n)

	for i := range n {
		timestamps[i] = base + int64(i)*86400
		openV[i] = ptr(10.0 + float64(i))
		highV[i] = ptr(11.0 + float64(i))
		lowV[i] = ptr(9.0 + float64(i))
		closeV[i] = ptr(10.5 + float64(i))
		vol := int64(1_000_000 + i*1000)
		volumeV[i] = &vol
	}

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		candles := make([]Candle, 0, n)
		for i, ts := range timestamps {
			if closeV[i] == nil || openV[i] == nil || highV[i] == nil || lowV[i] == nil {
				continue
			}
			var vol int64
			if volumeV[i] != nil {
				vol = *volumeV[i]
			}
			candles = append(candles, Candle{
				Date:   time.Unix(ts, 0).UTC(),
				Open:   *openV[i],
				High:   *highV[i],
				Low:    *lowV[i],
				Close:  *closeV[i],
				Volume: vol,
			})
		}
		_ = candles
	}
}

// BenchmarkJSONDecode mede o custo de decodificar o JSON da resposta do Yahoo
// (1 ano de candles diários).
func BenchmarkJSONDecode(b *testing.B) {
	body := validPayload("PETR4.SA", "BRL", 252)
	raw := []byte(body)

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		var data chartResponse
		if err := json.Unmarshal(raw, &data); err != nil {
			b.Fatal(err)
		}
	}
}

// BenchmarkFetchHistorySmall mede o mesmo ciclo com poucos candles (5d/1d).
func BenchmarkFetchHistorySmall(b *testing.B) {
	body := validPayload("AAPL", "USD", 5)

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, body)
	}))
	b.Cleanup(srv.Close)

	original := httpClient
	httpClient = srv.Client()
	b.Cleanup(func() { httpClient = original })

	origBase := baseURL
	baseURL = srv.URL + "/v8/finance/chart"
	b.Cleanup(func() { baseURL = origBase })

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		_, err := FetchHistory("AAPL", "5d", "1d")
		if err != nil {
			b.Fatal(err)
		}
	}
}
