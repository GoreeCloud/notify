package notify

import (
	"crypto/sha256"
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
)

type Handler struct {
	store        *Store
	auth         *Auth
	ui           http.Handler
	limiterMu    sync.Mutex
	limiter      map[string]publishWindow
	streamsMu    sync.Mutex
	streams      map[string]int
	totalStreams int
	peers        *peerLimiter
}
type publishWindow struct {
	start time.Time
	count int
}

func NewHandler(s *Store, a *Auth, ui http.Handler) http.Handler {
	h := &Handler{store: s, auth: a, ui: ui, limiter: make(map[string]publishWindow), streams: make(map[string]int), peers: newPeerLimiter()}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok"})
	})
	mux.HandleFunc("GET /readyz", func(w http.ResponseWriter, r *http.Request) {
		if !h.store.Healthy() {
			writeJSON(w, http.StatusServiceUnavailable, map[string]any{"status": "unready"})
			return
		}
		writeJSON(w, http.StatusOK, map[string]any{"status": "ready"})
	})
	mux.HandleFunc("GET /api/v1/me", h.me)
	mux.HandleFunc("GET /api/v1/topics", h.topics)
	mux.HandleFunc("POST /api/v1/topics/{topic}/messages", h.publish)
	mux.HandleFunc("GET /api/v1/topics/{topic}/messages", h.history)
	mux.HandleFunc("GET /api/v1/topics/{topic}/events", h.events)
	mux.HandleFunc("GET /metrics", h.metrics)
	mux.Handle("GET /", ui)
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("X-Frame-Options", "DENY")
		w.Header().Set("Referrer-Policy", "no-referrer")
		w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
		if strings.HasPrefix(r.URL.Path, "/api/") {
			w.Header().Set("Cache-Control", "no-store")
		} else {
			w.Header().Set("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
			w.Header().Set("Cache-Control", "no-store")
		}
		// Liveness/readiness must remain available to local orchestration.
		// All other routes are limited by the real socket peer. Never use
		// user-controlled X-Forwarded-For or Forwarded headers here.
		if r.URL.Path != "/healthz" && r.URL.Path != "/readyz" && !h.peers.allow(r.RemoteAddr, time.Now()) {
			w.Header().Set("Retry-After", "60")
			fail(w, http.StatusTooManyRequests, "request rate limit exceeded")
			return
		}
		mux.ServeHTTP(w, r)
	})
}
func writeJSON(w http.ResponseWriter, code int, obj any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(obj)
}
func fail(w http.ResponseWriter, code int, message string) {
	writeJSON(w, code, map[string]string{"error": message})
}
func (h *Handler) principal(w http.ResponseWriter, r *http.Request, topic, action string) (Principal, bool) {
	// Reject duplicated/ambiguous headers and bearer credentials with
	// whitespace or control characters rather than normalizing them.
	values := r.Header.Values("Authorization")
	if len(values) != 1 || len(values[0]) < 8 || len(values[0]) > 2048 ||
		!strings.EqualFold(values[0][:7], "Bearer ") ||
		strings.TrimSpace(values[0][7:]) != values[0][7:] ||
		strings.ContainsAny(values[0][7:], " \t\r\n,") {
		h.peers.failedAuth(r.RemoteAddr, time.Now())
		w.Header().Set("WWW-Authenticate", `Bearer realm="GoreeCloud Notify"`)
		fail(w, http.StatusUnauthorized, "bearer token required")
		return Principal{}, false
	}
	p, ok := h.auth.Identify(values[0][7:])
	if !ok {
		h.peers.failedAuth(r.RemoteAddr, time.Now())
		w.Header().Set("WWW-Authenticate", `Bearer realm="GoreeCloud Notify"`)
		fail(w, http.StatusUnauthorized, "invalid token")
		return Principal{}, false
	}
	if topic != "" && !p.Allowed(topic, action) {
		fail(w, http.StatusForbidden, "topic access denied")
		return Principal{}, false
	}
	return p, true
}
func (h *Handler) me(w http.ResponseWriter, r *http.Request) {
	p, ok := h.principal(w, r, "", "")
	if ok {
		writeJSON(w, 200, p)
	}
}
func (h *Handler) topics(w http.ResponseWriter, r *http.Request) {
	p, ok := h.principal(w, r, "", "")
	if !ok {
		return
	}
	writeJSON(w, 200, map[string]any{"topics": h.store.Topics(func(topic string) bool { return p.Allowed(topic, "read") })})
}
func (h *Handler) topic(w http.ResponseWriter, r *http.Request, action string) (string, Principal, bool) {
	topic := r.PathValue("topic")
	if !ValidTopic(topic) {
		fail(w, 400, "invalid topic")
		return "", Principal{}, false
	}
	p, ok := h.principal(w, r, topic, action)
	return topic, p, ok
}

var idemPattern = regexp.MustCompile(`^[A-Za-z0-9_.:-]{1,100}$`)

func (h *Handler) publish(w http.ResponseWriter, r *http.Request) {
	topic, _, ok := h.topic(w, r, "publish")
	if !ok {
		return
	}
	if !strings.HasPrefix(strings.ToLower(r.Header.Get("Content-Type")), "application/json") {
		fail(w, 415, "Content-Type must be application/json")
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, 16*1024)
	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()
	var req PublishRequest
	if err := dec.Decode(&req); err != nil {
		fail(w, 400, "invalid notification JSON")
		return
	}
	var extra any
	if err := dec.Decode(&extra); !errors.Is(err, io.EOF) {
		fail(w, 400, "expected one JSON object")
		return
	}
	if err := Validate(&req); err != nil {
		fail(w, 400, err.Error())
		return
	}
	idem := r.Header.Get("Idempotency-Key")
	if idem != "" && !idemPattern.MatchString(idem) {
		fail(w, 400, "invalid idempotency key")
		return
	}
	body, _ := json.Marshal(req)
	digest := sha256.Sum256(body)
	pub := sha256.Sum256([]byte(strings.TrimSpace(r.Header.Get("Authorization")[7:])))
	if !h.allowPublish(hex.EncodeToString(pub[:])) {
		w.Header().Set("Retry-After", "60")
		fail(w, 429, "publishing rate limit exceeded")
		return
	}
	msg, duplicate, err := h.store.Publish(topic, req, hex.EncodeToString(pub[:]), idem, hex.EncodeToString(digest[:]))
	if err != nil {
		if strings.Contains(err.Error(), "idempotency key") {
			fail(w, 409, err.Error())
		} else {
			fail(w, 500, "storage error")
		}
		return
	}
	if duplicate {
		w.Header().Set("Idempotent-Replay", "true")
		writeJSON(w, 200, msg)
	} else {
		writeJSON(w, 201, msg)
	}
}
func (h *Handler) history(w http.ResponseWriter, r *http.Request) {
	topic, _, ok := h.topic(w, r, "read")
	if !ok {
		return
	}
	limit := 50
	if q := r.URL.Query().Get("limit"); q != "" {
		n, err := strconv.Atoi(q)
		if err != nil || n < 1 || n > 100 {
			fail(w, 400, "limit must be between 1 and 100")
			return
		}
		limit = n
	}
	writeJSON(w, 200, map[string]any{"messages": h.store.List(topic, limit)})
}
func (h *Handler) events(w http.ResponseWriter, r *http.Request) {
	topic, _, ok := h.topic(w, r, "read")
	if !ok {
		return
	}
	// Long-lived streams consume a socket, goroutine, and queue. Limit them
	// per credential and globally, without relying on spoofable proxy headers.
	key := sha256.Sum256([]byte(strings.TrimSpace(r.Header.Get("Authorization")[7:])))
	release, allowed := h.acquireStream(hex.EncodeToString(key[:]))
	if !allowed {
		w.Header().Set("Retry-After", "5")
		fail(w, http.StatusTooManyRequests, "too many active streams")
		return
	}
	defer release()
	flusher, ok := w.(http.Flusher)
	if !ok {
		fail(w, 500, "streaming unavailable")
		return
	}
	after := r.Header.Get("Last-Event-ID")
	if q := r.URL.Query().Get("after"); q != "" {
		after = q
	}
	if len(after) > 64 {
		fail(w, 400, "invalid event cursor")
		return
	}
	recent, ch, unsubscribe := h.store.Subscribe(topic, after)
	defer unsubscribe()
	w.Header().Set("Content-Type", "text/event-stream; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache, no-transform")
	w.Header().Set("X-Accel-Buffering", "no")
	_, _ = io.WriteString(w, "retry: 3000\n\n")
	flusher.Flush()
	send := func(m Message) bool {
		payload, err := json.Marshal(m)
		if err != nil {
			return false
		}
		_, err = fmt.Fprintf(w, "id: %s\nevent: notification\ndata: %s\n\n", m.ID, payload)
		if err != nil {
			return false
		}
		flusher.Flush()
		return true
	}
	for _, m := range recent {
		if !send(m) {
			return
		}
	}
	heartbeat := time.NewTicker(20 * time.Second)
	defer heartbeat.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case m, open := <-ch:
			if !open {
				return
			}
			if !send(m) {
				return
			}
		case <-heartbeat.C:
			if _, err := io.WriteString(w, ": heartbeat\n\n"); err != nil {
				return
			}
			flusher.Flush()
		}
	}
}
func (h *Handler) metrics(w http.ResponseWriter, r *http.Request) {
	p, ok := h.principal(w, r, "", "")
	if !ok {
		return
	}
	if p.Role != "admin" {
		fail(w, 403, "administrator required")
		return
	}
	messages, connections, published := h.store.Stats()
	w.Header().Set("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
	fmt.Fprintf(w, "# TYPE notify_messages_retained gauge\nnotify_messages_retained %d\n# TYPE notify_active_subscribers gauge\nnotify_active_subscribers %d\n# TYPE notify_messages_published_total counter\nnotify_messages_published_total %d\n", messages, connections, published)
}

// allowPublish limits accepted publishing attempts per token in a rolling one-minute window.
// The limit is intentionally conservative for the alpha. A trusted ingress proxy must
// independently enforce request-level limits for unauthenticated traffic.
func (h *Handler) allowPublish(tokenID string) bool {
	h.limiterMu.Lock()
	defer h.limiterMu.Unlock()
	now := time.Now()
	w := h.limiter[tokenID]
	if w.start.IsZero() || now.Sub(w.start) >= time.Minute {
		w = publishWindow{start: now}
	}
	if w.count >= 120 {
		return false
	}
	w.count++
	h.limiter[tokenID] = w
	return true
}

// acquireStream bounds per-token and process-wide long-running SSE requests.
// It never trusts user-supplied IP/forwarded headers for authorization.
func (h *Handler) acquireStream(tokenHash string) (func(), bool) {
	h.streamsMu.Lock()
	defer h.streamsMu.Unlock()
	const perToken = 4
	const global = 64
	if h.streams[tokenHash] >= perToken || h.totalStreams >= global {
		return nil, false
	}
	h.streams[tokenHash]++
	h.totalStreams++
	return func() {
		h.streamsMu.Lock()
		defer h.streamsMu.Unlock()
		h.streams[tokenHash]--
		h.totalStreams--
		if h.streams[tokenHash] == 0 {
			delete(h.streams, tokenHash)
		}
	}, true
}
