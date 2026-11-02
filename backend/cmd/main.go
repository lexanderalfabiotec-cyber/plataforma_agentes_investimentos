package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/lexanderalfabiotec-cyber/plataforma_agentes_investimentos/internal/handlers"
)

// buildMux constrói e retorna o ServeMux com todas as rotas registradas.
// Extraído do main() para permitir testes de roteamento sem subir um servidor real.
func buildMux() *http.ServeMux {
	mux := http.NewServeMux()

	// GET /api/v1/history?symbol=PETR4.SA&range=1mo&interval=1d
	mux.HandleFunc("GET /api/v1/history", handlers.GetHistory)

	// GET /api/v1/latest?symbol=PETR4.SA
	mux.HandleFunc("GET /api/v1/latest", handlers.GetLatest)

	// GET /health – utilizado pelo Docker healthcheck e pelo agente Python
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
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
		Addr:              ":" + port,
		Handler:           buildMux(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       30 * time.Second,
		WriteTimeout:      30 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	log.Printf("🚀 Backend Go iniciado na porta %s", port)
	log.Printf("   GET /api/v1/history?symbol=PETR4.SA&range=1mo&interval=1d")
	log.Printf("   GET /api/v1/latest?symbol=PETR4.SA")
	log.Printf("   GET /health")

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	serverErr := make(chan error, 1)
	go func() { serverErr <- server.ListenAndServe() }()

	select {
	case err := <-serverErr:
		if !errors.Is(err, http.ErrServerClosed) {
			log.Fatalf("servidor encerrado: %v", err)
		}
	case <-ctx.Done():
		log.Print("encerrando: aguardando requisições em andamento")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("encerramento forçado: %v", err)
		}
	}
}
