package notify

import (
	"context"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode/utf8"
)

var topicPattern = regexp.MustCompile(`^[a-zA-Z0-9_-]{1,64}$`)

type broker struct {
	mu   sync.Mutex
	subs map[string]map[chan Message]struct{}
}

func newBroker() *broker { return &broker{subs: make(map[string]map[chan Message]struct{})} }

func (b *broker) subscribe(topic string) chan Message {
	ch := make(chan Message, 32)
	b.mu.Lock()
	defer b.mu.Unlock()
	if b.subs[topic] == nil {
		b.subs[topic] = make(map[chan Message]struct{})
	}
	b.subs[topic][ch] = struct{}{}
	return ch
}

func (b *broker) unsubscribe(topic string, ch chan Message) {
	b.mu.Lock()
	defer b.mu.Unlock()
	delete(b.subs[topic], ch)
	if len(b.subs[topic]) == 0 {
		delete(b.subs, topic)
	}
}

func (b *broker) publish(topic string, m Message) {
	b.mu.Lock()
	defer b.mu.Unlock()
	for ch := range b.subs[topic] {
		select {
		case ch <- m:
		default: // never let a stalled subscriber block other clients
		}
	}
}

type Handler struct {
	store     *Store
	tokenHash [32]byte
	broker    *broker
	limitMu   sync.Mutex
	published []time.Time
	mux       *http.ServeMux
}

func NewHandler(token string, store *Store) (*Handler, error) {
	if len(token) < 32 {
		return nil, errors.New("NOTIFY_API_TOKEN must be at least 32 characters")
	}
	if store == nil {
		return nil, errors.New("notification store is required")
	}
	h := &Handler{store: store, tokenHash: sha256.Sum256([]byte(token)), broker: newBroker()}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		sendJSON(w, http.StatusOK, map[string]string{"status": "ok"})
	})
	mux.HandleFunc("POST /api/v1/topics/{topic}/messages", h.post)
	mux.HandleFunc("GET /api/v1/topics/{topic}/messages", h.list)
	mux.HandleFunc("GET /api/v1/topics/{topic}/events", h.events)
	h.mux = mux
	return h, nil
}

func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Referrer-Policy", "no-referrer")
	w.Header().Set("Cache-Control", "no-store")
	if strings.HasPrefix(r.URL.Path, "/api/") {
		prefix := "Bearer "
		auth := r.Header.Get("Authorization")
		if !strings.HasPrefix(auth, prefix) {
			w.Header().Set("WWW-Authenticate", "Bearer")
			sendError(w, http.StatusUnauthorized, "bearer token required")
			return
		}
		provided := sha256.Sum256([]byte(strings.TrimPrefix(auth, prefix)))
		if subtle.ConstantTimeCompare(provided[:], h.tokenHash[:]) != 1 {
			sendError(w, http.StatusUnauthorized, "invalid credentials")
			return
		}
	}
	h.mux.ServeHTTP(w, r)
}

func sendJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(v)
}

func sendError(w http.ResponseWriter, status int, message string) {
	sendJSON(w, status, map[string]string{"error": message})
}

func validTopic(w http.ResponseWriter, r *http.Request) bool {
	if !topicPattern.MatchString(r.PathValue("topic")) {
		sendError(w, http.StatusBadRequest, "topic must be 1-64 ASCII letters, numbers, dashes or underscores")
		return false
	}
	return true
}

func (h *Handler) allowPublish() bool {
	h.limitMu.Lock()
	defer h.limitMu.Unlock()
	now := time.Now()
	cutoff := now.Add(-time.Minute)
	keep := h.published[:0]
	for _, t := range h.published {
		if t.After(cutoff) {
			keep = append(keep, t)
		}
	}
	h.published = keep
	if len(h.published) >= 120 {
		return false
	}
	h.published = append(h.published, now)
	return true
}

func (h *Handler) post(w http.ResponseWriter, r *http.Request) {
	if !validTopic(w, r) {
		return
	}
	if !strings.HasPrefix(r.Header.Get("Content-Type"), "application/json") {
		sendError(w, http.StatusUnsupportedMediaType, "application/json required")
		return
	}
	if !h.allowPublish() {
		w.Header().Set("Retry-After", "60")
		sendError(w, http.StatusTooManyRequests, "publish rate limit reached")
		return
	}
	var input struct {
		Title    string `json:"title"`
		Body     string `json:"body"`
		Priority int    `json:"priority"`
	}
	decoder := json.NewDecoder(http.MaxBytesReader(w, r.Body, 8192))
	decoder.DisallowUnknownFields()
	if err := decoder.Decode(&input); err != nil {
		sendError(w, http.StatusBadRequest, "invalid message JSON")
		return
	}
	var trailing any
	if decoder.Decode(&trailing) != io.EOF {
		sendError(w, http.StatusBadRequest, "only one JSON object is allowed")
		return
	}
	input.Title = strings.TrimSpace(input.Title)
	input.Body = strings.TrimSpace(input.Body)
	if input.Priority == 0 {
		input.Priority = 3
	}
	if input.Body == "" || !utf8.ValidString(input.Body) || utf8.RuneCountInString(input.Body) > 4096 ||
		!utf8.ValidString(input.Title) || utf8.RuneCountInString(input.Title) > 160 ||
		input.Priority < 1 || input.Priority > 5 {
		sendError(w, http.StatusBadRequest, "body, title or priority outside allowed limits")
		return
	}
	idBytes := make([]byte, 16)
	if _, err := rand.Read(idBytes); err != nil {
		sendError(w, http.StatusInternalServerError, "unable to create message ID")
		return
	}
	m := Message{
		ID: hex.EncodeToString(idBytes), Topic: r.PathValue("topic"), Title: input.Title,
		Body: input.Body, Priority: input.Priority, CreatedAt: time.Now().UTC(),
	}
	if err := h.store.Append(m); err != nil {
		if errors.Is(err, ErrCapacity) {
			sendError(w, http.StatusInsufficientStorage, "journal capacity reached; archive and rotate before retry")
		} else {
			sendError(w, http.StatusInternalServerError, "message could not be saved")
		}
		return
	}
	h.broker.publish(m.Topic, m)
	sendJSON(w, http.StatusCreated, m)
}

func (h *Handler) list(w http.ResponseWriter, r *http.Request) {
	if !validTopic(w, r) {
		return
	}
	limit := 50
	if raw := r.URL.Query().Get("limit"); raw != "" {
		n, err := strconv.Atoi(raw)
		if err != nil || n < 1 || n > 200 {
			sendError(w, http.StatusBadRequest, "limit must be 1-200")
			return
		}
		limit = n
	}
	sendJSON(w, http.StatusOK, map[string]any{"messages": h.store.List(r.PathValue("topic"), limit)})
}

func (h *Handler) events(w http.ResponseWriter, r *http.Request) {
	if !validTopic(w, r) {
		return
	}
	flusher, ok := w.(http.Flusher)
	if !ok {
		sendError(w, http.StatusInternalServerError, "streaming unsupported")
		return
	}
	topic := r.PathValue("topic")
	ch := h.broker.subscribe(topic)
	defer h.broker.unsubscribe(topic, ch)
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("X-Accel-Buffering", "no")
	w.Header().Set("Connection", "keep-alive")
	fmt.Fprint(w, ": connected\n\n")
	flusher.Flush()
	ticker := time.NewTicker(20 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case m := <-ch:
			data, err := json.Marshal(m)
			if err != nil {
				continue
			}
			if _, err := fmt.Fprintf(w, "event: message\ndata: %s\n\n", data); err != nil {
				return
			}
			flusher.Flush()
		case <-ticker.C:
			if _, err := fmt.Fprint(w, ": heartbeat\n\n"); err != nil {
				return
			}
			flusher.Flush()
		case <-r.Context().Done():
			return
		}
	}
}

// Stream cancellation is owned by the request context; this is a compile-time guard.
var _ context.Context = context.Background()
