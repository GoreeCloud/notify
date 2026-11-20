package notify

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const testToken = "test-token-please-replace-this-1234567890"

func newTestServer(t *testing.T) (*httptest.Server, *Store) {
	t.Helper()
	s, err := OpenStore(filepath.Join(t.TempDir(), "messages.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	h, err := NewHandler(testToken, s)
	if err != nil {
		t.Fatal(err)
	}
	srv := httptest.NewServer(h)
	t.Cleanup(srv.Close)
	return srv, s
}

func request(t *testing.T, srv *httptest.Server, method, path, payload, token string) *http.Response {
	t.Helper()
	req, err := http.NewRequest(method, srv.URL+path, strings.NewReader(payload))
	if err != nil {
		t.Fatal(err)
	}
	if token != "" {
		req.Header.Set("Authorization", "Bearer "+token)
	}
	if payload != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := srv.Client().Do(req)
	if err != nil {
		t.Fatal(err)
	}
	return resp
}

func TestAuthPublishHistoryAndRestart(t *testing.T) {
	srv, store := newTestServer(t)
	unauth := request(t, srv, http.MethodGet, "/api/v1/topics/system/messages", "", "")
	unauth.Body.Close()
	if unauth.StatusCode != http.StatusUnauthorized {
		t.Fatalf("unauthenticated request: %d", unauth.StatusCode)
	}
	wrong := request(t, srv, http.MethodGet, "/api/v1/topics/system/messages", "", strings.Repeat("x", 32))
	wrong.Body.Close()
	if wrong.StatusCode != http.StatusUnauthorized {
		t.Fatalf("wrong token: %d", wrong.StatusCode)
	}
	post := request(t, srv, http.MethodPost, "/api/v1/topics/system/messages", `{"title":"Alert","body":"Disk nearing capacity","priority":5}`, testToken)
	if post.StatusCode != http.StatusCreated {
		t.Fatalf("publish status: %d", post.StatusCode)
	}
	var published Message
	if err := json.NewDecoder(post.Body).Decode(&published); err != nil {
		t.Fatal(err)
	}
	post.Body.Close()
	if len(published.ID) != 32 || published.Priority != 5 || published.CreatedAt.IsZero() {
		t.Fatalf("unexpected message: %+v", published)
	}
	history := request(t, srv, http.MethodGet, "/api/v1/topics/system/messages?limit=10", "", testToken)
	if history.StatusCode != http.StatusOK {
		t.Fatalf("history status: %d", history.StatusCode)
	}
	var result struct {
		Messages []Message `json:"messages"`
	}
	if err := json.NewDecoder(history.Body).Decode(&result); err != nil {
		t.Fatal(err)
	}
	history.Body.Close()
	if len(result.Messages) != 1 || result.Messages[0].ID != published.ID {
		t.Fatalf("history mismatch: %+v", result.Messages)
	}
	other := request(t, srv, http.MethodGet, "/api/v1/topics/other/messages", "", testToken)
	defer other.Body.Close()
	var empty struct {
		Messages []Message `json:"messages"`
	}
	if err := json.NewDecoder(other.Body).Decode(&empty); err != nil || len(empty.Messages) != 0 {
		t.Fatalf("topic leak: %v %+v", err, empty)
	}
	reloaded, err := OpenStore(store.path)
	if err != nil {
		t.Fatal(err)
	}
	if len(reloaded.List("system", 10)) != 1 {
		t.Fatal("message was not durable")
	}
}

func TestValidationAndSafeDefaults(t *testing.T) {
	srv, _ := newTestServer(t)
	tests := []struct {
		path string
		body string
		want int
	}{
		{"/api/v1/topics/inv%20alid/messages", `{"body":"hello"}`, 400},
		{"/api/v1/topics/system/messages", `{"body":""}`, 400},
		{"/api/v1/topics/system/messages", `{"body":"hello","priority":9}`, 400},
		{"/api/v1/topics/system/messages", `{"body":"hello","unknown":true}`, 400},
		{"/api/v1/topics/system/messages", `{"body":"ok"}{"body":"no"}`, 400},
		{"/api/v1/topics/system/messages", `{"body":"hello"}`, 201},
	}
	for _, tt := range tests {
		resp := request(t, srv, "POST", tt.path, tt.body, testToken)
		resp.Body.Close()
		if resp.StatusCode != tt.want {
			t.Errorf("%s: got %d want %d", tt.body, resp.StatusCode, tt.want)
		}
	}
	badLimit := request(t, srv, "GET", "/api/v1/topics/system/messages?limit=201", "", testToken)
	badLimit.Body.Close()
	if badLimit.StatusCode != 400 {
		t.Fatal("unbounded list permitted")
	}
}

func TestTokenMinimumAndFilePermissions(t *testing.T) {
	s, err := OpenStore(filepath.Join(t.TempDir(), "private", "events.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := NewHandler("short", s); err == nil {
		t.Fatal("weak token accepted")
	}
	if err := s.Append(Message{ID: "test", Topic: "a", Body: "b"}); err != nil {
		t.Fatal(err)
	}
	if bytes.Contains([]byte(strings.Join([]string{s.path}, "")), []byte(testToken)) {
		t.Fatal("test token in storage path")
	}
}

func TestLiveSSEDelivery(t *testing.T) {
	server, _ := newTestServer(t)
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	request, err := http.NewRequestWithContext(ctx, http.MethodGet, server.URL+"/api/v1/topics/system/events", nil)
	if err != nil {
		t.Fatal(err)
	}
	request.Header.Set("Authorization", "Bearer "+testToken)
	response, err := server.Client().Do(request)
	if err != nil {
		t.Fatal(err)
	}
	defer response.Body.Close()
	if response.StatusCode != http.StatusOK || !strings.HasPrefix(response.Header.Get("Content-Type"), "text/event-stream") {
		t.Fatalf("unexpected SSE response: %d", response.StatusCode)
	}
	scanner := bufio.NewScanner(response.Body)
	if !scanner.Scan() || scanner.Text() != ": connected" {
		t.Fatal("missing stream handshake")
	}
	published := requestForSSE(t, server)
	if published.StatusCode != http.StatusCreated {
		t.Fatalf("unexpected publish: %d", published.StatusCode)
	}
	published.Body.Close()
	for scanner.Scan() {
		line := scanner.Text()
		if strings.HasPrefix(line, "data: ") {
			var m Message
			if err := json.Unmarshal([]byte(strings.TrimPrefix(line, "data: ")), &m); err != nil {
				t.Fatal(err)
			}
			if m.Topic != "system" || m.Body != "Streaming test message" {
				t.Fatalf("wrong topic or body: %+v", m)
			}
			return
		}
	}
	t.Fatalf("no SSE message received: %v", scanner.Err())
}

func requestForSSE(t *testing.T, server *httptest.Server) *http.Response {
	t.Helper()
	return request(t, server, "POST", "/api/v1/topics/system/messages", `{"body":"Streaming test message"}`, testToken)
}
