package main

import (
	"context"
	"embed"
	"errors"
	"fmt"
	"io/fs"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/GoreeCloud/notify/internal/notify"
)

//go:embed web/*
var assets embed.FS

func main() {
	if err := run(); err != nil {
		slog.Error("service exited", "error", err)
		os.Exit(1)
	}
}
func run() error {
	token := os.Getenv("NOTIFY_ADMIN_TOKEN")
	auth, err := notify.NewAuth(token, os.Getenv("NOTIFY_ACL_FILE"))
	if err != nil {
		return err
	}
	dir := getEnv("NOTIFY_DATA_DIR", "./data")
	retentionHours, err := strconv.Atoi(getEnv("NOTIFY_RETENTION_HOURS", "168"))
	if err != nil || retentionHours < 1 || retentionHours > 8760 {
		return fmt.Errorf("invalid NOTIFY_RETENTION_HOURS")
	}
	maxMsgs, err := strconv.Atoi(getEnv("NOTIFY_MAX_MESSAGES_PER_TOPIC", "5000"))
	if err != nil || maxMsgs < 1 || maxMsgs > 100000 {
		return fmt.Errorf("invalid NOTIFY_MAX_MESSAGES_PER_TOPIC")
	}
	store, err := notify.OpenStore(dir, time.Duration(retentionHours)*time.Hour, maxMsgs)
	if err != nil {
		return err
	}
	defer store.Close()
	sub, err := fs.Sub(assets, "web")
	if err != nil {
		return err
	}
	ui := http.FileServer(http.FS(sub))
	handler := notify.NewHandler(store, auth, ui)
	srv := &http.Server{Addr: getEnv("NOTIFY_ADDR", "127.0.0.1:8080"), Handler: handler, ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 20 * time.Second, IdleTimeout: 70 * time.Second, MaxHeaderBytes: 16 << 10}
	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	go func() {
		ticker := time.NewTicker(time.Hour)
		defer ticker.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-ticker.C:
				if err := store.Prune(); err != nil {
					slog.Error("failed to compact messages", "error", err)
				}
			}
		}
	}()
	go func() {
		<-ctx.Done()
		stopCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		_ = srv.Shutdown(stopCtx)
	}()
	slog.Info("GoreeCloud Notify listening", "address", srv.Addr, "tls_note", "use a TLS reverse proxy for remote access")
	err = srv.ListenAndServe()
	if errors.Is(err, http.ErrServerClosed) {
		return nil
	}
	return err
}
func getEnv(name, fallback string) string {
	if val := os.Getenv(name); val != "" {
		return val
	}
	return fallback
}
