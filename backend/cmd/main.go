package main

import (
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/handlers"
)

// buildMux constrói e retorna o ServeMux com todas as rotas registradas.
// Extraído do main() para permitir testes de roteamento sem subir um servidor real.
func buildMux() *http.ServeMux {
	mux := http.NewServeMux()

	// GET /api/v1/history?symbol=PETR4.SA&range=1mo&interval=1d
	mux.HandleFunc("/api/v1/history", handlers.GetHistory)

	// GET /api/v1/latest?symbol=PETR4.SA
	mux.HandleFunc("/api/v1/latest", handlers.GetLatest)

	// GET /health – utilizado pelo Docker healthcheck e pelo agente Python
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprintf(w, `{"status":"ok"}`)
	})

	return mux
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	server := &http.Server{
		Addr:         ":" + port,
		Handler:      buildMux(),
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	log.Printf("🚀 Backend Go iniciado na porta %s", port)
	log.Printf("   GET /api/v1/history?symbol=PETR4.SA&range=1mo&interval=1d")
	log.Printf("   GET /api/v1/latest?symbol=PETR4.SA")
	log.Printf("   GET /health")

	if err := server.ListenAndServe(); err != nil {
		log.Fatalf("servidor encerrado: %v", err)
	}
}
