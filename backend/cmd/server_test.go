package main

// ─────────────────────────────────────────────────────────────────────────────
// Testes do pacote main (roteamento e endpoint /health)
//
// Cobertura:
//   - GET /health → 200 {"status":"ok"}
//   - Content-Type do /health é application/json
//   - GET /api/v1/history sem symbol → 400 (roteamento correto)
//   - GET /api/v1/latest sem symbol → 400 (roteamento correto)
//   - Rota inexistente → 404
//   - Todas rotas de erro retornam Content-Type: application/json
//
// Benchmarks:
//   - BenchmarkHealthEndpoint         – throughput sequencial do /health
//   - BenchmarkHealthEndpointParallel – throughput paralelo do /health
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

// newTestServer monta o mesmo mux do main() e retorna um httptest.Server.
func newTestServer(t *testing.T) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(buildMux())
	t.Cleanup(srv.Close)
	return srv
}

// ── testes de roteamento ──────────────────────────────────────────────────────

func TestHealth(t *testing.T) {
	srv := newTestServer(t)

	resp, err := srv.Client().Get(srv.URL + "/health")
	if err != nil {
		t.Fatalf("GET /health: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		t.Errorf("status: got %d, want 200", resp.StatusCode)
	}

	ct := resp.Header.Get("Content-Type")
	if !strings.Contains(ct, "application/json") {
		t.Errorf("Content-Type: got %q, want application/json", ct)
	}

	var body map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		t.Fatalf("decodificar body /health: %v", err)
	}
	if body["status"] != "ok" {
		t.Errorf("body[status]: got %q, want %q", body["status"], "ok")
	}
}

func TestHistoryRoute_MissingSymbol_Returns400(t *testing.T) {
	srv := newTestServer(t)

	resp, err := srv.Client().Get(srv.URL + "/api/v1/history")
	if err != nil {
		t.Fatalf("GET /api/v1/history: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("status: got %d, want 400", resp.StatusCode)
	}
}

func TestLatestRoute_MissingSymbol_Returns400(t *testing.T) {
	srv := newTestServer(t)

	resp, err := srv.Client().Get(srv.URL + "/api/v1/latest")
	if err != nil {
		t.Fatalf("GET /api/v1/latest: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("status: got %d, want 400", resp.StatusCode)
	}
}

func TestUnknownRoute_Returns404(t *testing.T) {
	srv := newTestServer(t)

	resp, err := srv.Client().Get(srv.URL + "/nao-existe")
	if err != nil {
		t.Fatalf("GET /nao-existe: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("status: got %d, want 404", resp.StatusCode)
	}
}

// TestAllErrorRoutesReturnJSON garante que todas as rotas de erro devolvem JSON.
func TestAllErrorRoutesReturnJSON(t *testing.T) {
	srv := newTestServer(t)
	client := srv.Client()

	routes := []string{
		"/api/v1/history", // sem symbol → 400
		"/api/v1/latest",  // sem symbol → 400
	}

	for _, route := range routes {
		t.Run(route, func(t *testing.T) {
			resp, err := client.Get(fmt.Sprintf("%s%s", srv.URL, route))
			if err != nil {
				t.Fatalf("GET %s: %v", route, err)
			}
			defer resp.Body.Close()

			ct := resp.Header.Get("Content-Type")
			if !strings.Contains(ct, "application/json") {
				t.Errorf("%s Content-Type: got %q, want application/json", route, ct)
			}

			// Verifica que o body é JSON válido com campo "error"
			var body map[string]string
			if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
				t.Errorf("%s: body não é JSON válido: %v", route, err)
			}
			if body["error"] == "" {
				t.Errorf("%s: campo 'error' não deve ser vazio", route)
			}
		})
	}
}

// TestHealthIdempotent verifica que /health é estável em múltiplas chamadas.
func TestHealthIdempotent(t *testing.T) {
	srv := newTestServer(t)
	client := srv.Client()

	for i := range 5 {
		resp, err := client.Get(srv.URL + "/health")
		if err != nil {
			t.Fatalf("chamada %d: %v", i, err)
		}
		resp.Body.Close()
		if resp.StatusCode != http.StatusOK {
			t.Errorf("chamada %d: status %d, want 200", i, resp.StatusCode)
		}
	}
}

// ── benchmarks ────────────────────────────────────────────────────────────────

// BenchmarkHealthEndpoint mede o throughput sequencial do endpoint /health.
func BenchmarkHealthEndpoint(b *testing.B) {
	srv := httptest.NewServer(buildMux())
	b.Cleanup(srv.Close)

	client := &http.Client{Timeout: 5 * time.Second}
	url := srv.URL + "/health"

	b.ResetTimer()
	b.ReportAllocs()

	for b.Loop() {
		resp, err := client.Get(url)
		if err != nil {
			b.Fatal(err)
		}
		resp.Body.Close()
	}
}

// BenchmarkHealthEndpointParallel mede o throughput paralelo do /health.
// Útil para detectar contenção de lock no handler.
func BenchmarkHealthEndpointParallel(b *testing.B) {
	srv := httptest.NewServer(buildMux())
	b.Cleanup(srv.Close)
	url := srv.URL + "/health"

	b.ResetTimer()
	b.ReportAllocs()

	b.RunParallel(func(pb *testing.PB) {
		client := &http.Client{Timeout: 5 * time.Second}
		for pb.Next() {
			resp, err := client.Get(url)
			if err != nil {
				b.Error(err)
				return
			}
			resp.Body.Close()
		}
	})
}

// BenchmarkBuildMux mede o custo de construir o mux (registrar rotas).
func BenchmarkBuildMux(b *testing.B) {
	b.ReportAllocs()
	for b.Loop() {
		_ = buildMux()
	}
}
