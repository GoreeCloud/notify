package main

import (
	"context"
	"errors"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/GoreeCloud/notify/internal/notify"
)

func main() {
	token := os.Getenv("NOTIFY_API_TOKEN")
	dataFile := os.Getenv("NOTIFY_DATA_FILE")
	if dataFile == "" {
		dataFile = filepath.Join("data", "messages.jsonl")
	}
	address := os.Getenv("NOTIFY_LISTEN")
	if address == "" {
		address = "127.0.0.1:8080"
	}
	store, err := notify.OpenStore(dataFile)
	if err != nil {
		log.Fatalf("cannot open notification data: %v", err)
	}
	handler, err := notify.NewHandler(token, store)
	if err != nil {
		log.Fatalf("invalid configuration: %v", err)
	}
	server := &http.Server{Addr: address, Handler: handler, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 20 * time.Second, IdleTimeout: 65 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdownCtx); err != nil {
			log.Printf("shutdown error: %v", err)
		}
	}()
	log.Printf("GoreeCloud Notify listening on %s (bind to loopback by default; terminate TLS at a trusted proxy)", address)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatalf("server stopped: %v", err)
	}
}
