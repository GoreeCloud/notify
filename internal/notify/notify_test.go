package notify

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const adminToken = "this-is-a-long-admin-test-secret-123456789"

func setup(t *testing.T) (*Store, http.Handler) {
	t.Helper()
	s, err := OpenStore(t.TempDir(), 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = s.Close() })
	a, err := NewAuth(adminToken, "")
	if err != nil {
		t.Fatal(err)
	}
	return s, NewHandler(s, a, http.NotFoundHandler())
}
func req(t *testing.T, h http.Handler, method, path, auth, body string) *httptest.ResponseRecorder {
	t.Helper()
	r := httptest.NewRequest(method, path, strings.NewReader(body))
	if auth != "" {
		r.Header.Set("Authorization", "Bearer "+auth)
	}
	if body != "" {
		r.Header.Set("Content-Type", "application/json")
	}
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	return w
}
func TestAuthDefaultDeny(t *testing.T) {
	_, h := setup(t)
	if got := req(t, h, "GET", "/api/v1/topics", "", "").Code; got != 401 {
		t.Fatal(got)
	}
	if got := req(t, h, "GET", "/api/v1/topics", "bad", "").Code; got != 401 {
		t.Fatal(got)
	}
	if got := req(t, h, "GET", "/api/v1/topics", adminToken, "").Code; got != 200 {
		t.Fatal(got)
	}
}
func TestPublishHistoryAndRestart(t *testing.T) {
	dir := t.TempDir()
	s, e := OpenStore(dir, 24*time.Hour, 100)
	if e != nil {
		t.Fatal(e)
	}
	a, _ := NewAuth(adminToken, "")
	h := NewHandler(s, a, http.NotFoundHandler())
	b := `{"title":"Backup","body":"All good","priority":4,"tags":["backup"],"click":"https://example.org"}`
	w := req(t, h, "POST", "/api/v1/topics/backup/messages", adminToken, b)
	if w.Code != 201 {
		t.Fatalf("status %d: %s", w.Code, w.Body.String())
	}
	var msg Message
	if err := json.Unmarshal(w.Body.Bytes(), &msg); err != nil {
		t.Fatal(err)
	}
	if msg.Title != "Backup" || msg.Priority != 4 {
		t.Fatal(msg)
	}
	w = req(t, h, "GET", "/api/v1/topics/backup/messages?limit=10", adminToken, "")
	if w.Code != 200 || !strings.Contains(w.Body.String(), msg.ID) {
		t.Fatal(w.Body.String())
	}
	_ = s.Close()
	s, e = OpenStore(dir, 24*time.Hour, 100)
	if e != nil {
		t.Fatal(e)
	}
	defer s.Close()
	if x := s.List("backup", 10); len(x) != 1 || x[0].ID != msg.ID {
		t.Fatal(x)
	}
}
func TestIdempotencyAndValidation(t *testing.T) {
	_, h := setup(t)
	post := func(body, key string) *httptest.ResponseRecorder {
		r := httptest.NewRequest("POST", "/api/v1/topics/alerts/messages", strings.NewReader(body))
		r.Header.Set("Authorization", "Bearer "+adminToken)
		r.Header.Set("Content-Type", "application/json")
		r.Header.Set("Idempotency-Key", key)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	a := post(`{"body":"one"}`, "dedup-1")
	b := post(`{"body":"one"}`, "dedup-1")
	c := post(`{"body":"two"}`, "dedup-1")
	if a.Code != 201 || b.Code != 200 || c.Code != 409 {
		t.Fatalf("statuses %d %d %d", a.Code, b.Code, c.Code)
	}
	if got := post(`{"body":"x","click":"javascript:evil()"}`, "").Code; got != 400 {
		t.Fatal(got)
	}
	if got := post(`{"body":"x","priority":6}`, "").Code; got != 400 {
		t.Fatal(got)
	}
	if got := post(`{"body":"x","unknown":1}`, "").Code; got != 400 {
		t.Fatal(got)
	}
}
func TestTopicIsolationAndACL(t *testing.T) {
	s, _ := setup(t)
	tok := "subscriber-access-token-with-enough-entropy-999"
	hash := shaHex(tok)
	aclPath := filepath.Join(t.TempDir(), "acl.json")
	if err := os.WriteFile(aclPath, []byte(`[{"name":"viewer","sha256":"`+hash+`","role":"subscriber","topics":["alerts"]}]`), 0600); err != nil {
		t.Fatal(err)
	}
	a, e := NewAuth(adminToken, aclPath)
	if e != nil {
		t.Fatal(e)
	}
	h := NewHandler(s, a, http.NotFoundHandler())
	if got := req(t, h, "GET", "/api/v1/topics/alerts/messages", tok, "").Code; got != 200 {
		t.Fatal(got)
	}
	if got := req(t, h, "GET", "/api/v1/topics/secret/messages", tok, "").Code; got != 403 {
		t.Fatal(got)
	}
	if got := req(t, h, "POST", "/api/v1/topics/alerts/messages", tok, `{"body":"no"}`).Code; got != 403 {
		t.Fatal(got)
	}
}
func TestSSEReplay(t *testing.T) {
	s, h := setup(t)
	_, _, _ = s.Publish("alerts", PublishRequest{Body: "hello", Priority: 3}, "p", "", "")
	server := httptest.NewServer(h)
	defer server.Close()
	client := &http.Client{Timeout: time.Second}
	r, e := http.NewRequest("GET", server.URL+"/api/v1/topics/alerts/events", nil)
	if e != nil {
		t.Fatal(e)
	}
	r.Header.Set("Authorization", "Bearer "+adminToken)
	resp, e := client.Do(r)
	if e != nil {
		t.Fatal(e)
	}
	defer resp.Body.Close()
	buf := make([]byte, 1024)
	n, e := resp.Body.Read(buf)
	if e != nil && e != io.EOF {
		t.Fatal(e)
	}
	if !bytes.Contains(buf[:n], []byte("retry:")) {
		t.Fatal(string(buf[:n]))
	}
}
func TestRetentionAndTopicName(t *testing.T) {
	if ValidTopic("../a") || ValidTopic("my/topic") || !ValidTopic("backup_prod-2") {
		t.Fatal("topic validation")
	}
	s, _ := setup(t)
	for i := 0; i < 5; i++ {
		_, _, err := s.Publish("x", PublishRequest{Body: "hello", Priority: 3}, "p", "", "")
		if err != nil {
			t.Fatal(err)
		}
	}
	if err := s.Prune(); err != nil {
		t.Fatal(err)
	}
	if n := len(s.List("x", 100)); n != 5 {
		t.Fatal(n)
	}
}

func shaHex(s string) string { h := sha256.Sum256([]byte(s)); return hex.EncodeToString(h[:]) }

func TestBootstrapRejectsExamplePlaceholder(t *testing.T) {
	if _, err := NewAuth("REPLACE_WITH_A_RANDOM_SECRET_AT_LEAST_32_CHARACTERS", ""); err == nil {
		t.Fatal("example admin token must be rejected")
	}
}
func TestPublisherRateLimit(t *testing.T) {
	_, h := setup(t)
	for n := 0; n < 120; n++ {
		w := req(t, h, "POST", "/api/v1/topics/rate/messages", adminToken, `{"body":"message"}`)
		if w.Code != 201 {
			t.Fatalf("message %d: %d %s", n, w.Code, w.Body.String())
		}
	}
	w := req(t, h, "POST", "/api/v1/topics/rate/messages", adminToken, `{"body":"message"}`)
	if w.Code != 429 || w.Header().Get("Retry-After") != "60" {
		t.Fatalf("expected 429, got %d", w.Code)
	}
}


// The service does not silently rewrite a truncated tail during startup.
func TestTruncatedRecordFailsClosedWithoutMutation(t *testing.T) {
	dir := t.TempDir()
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil { t.Fatal(err) }
	if _, _, err := s.Publish("alerts", PublishRequest{Body: "sent", Priority: 3}, "publisher", "", ""); err != nil { t.Fatal(err) }
	if err := s.Close(); err != nil { t.Fatal(err) }
	path := filepath.Join(dir, "messages.jsonl")
	fd, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil { t.Fatal(err) }
	if _, err := fd.WriteString("{\"id\":\"incomplete"); err != nil { t.Fatal(err) }
	_ = fd.Close()
	before, err := os.ReadFile(path)
	if err != nil { t.Fatal(err) }
	reopened, err := OpenStore(dir, 24*time.Hour, 100)
	if err == nil { _ = reopened.Close(); t.Fatal("corrupted log was accepted") }
	after, err := os.ReadFile(path)
	if err != nil { t.Fatal(err) }
	if !bytes.Equal(before, after) { t.Fatal("failed startup modified damaged log") }
}

func TestCompactionErrorKeepsOldLogWriter(t *testing.T) {
	s, err := OpenStore(t.TempDir(), 24*time.Hour, 100)
	if err != nil { t.Fatal(err) }
	defer s.Close()
	original := s.path
	s.path = filepath.Join(t.TempDir(), "missing", "messages.jsonl")
	if err := s.Prune(); err == nil { t.Fatal("expected staging error") }
	s.path = original
	if _, _, err := s.Publish("alerts", PublishRequest{Body: "still writable", Priority: 3}, "producer", "", ""); err != nil {
		t.Fatal("old log writer lost after failed compaction:", err)
	}
}

func TestAppendFailureFailsClosed(t *testing.T) {
	s, err := OpenStore(t.TempDir(), 24*time.Hour, 100)
	if err != nil { t.Fatal(err) }
	if err := s.file.Close(); err != nil { t.Fatal(err) }
	for i := 0; i < 2; i++ {
		if _, _, err := s.Publish("alerts", PublishRequest{Body: "fail", Priority: 3}, "producer", "", ""); err == nil {
			t.Fatal("append failure must reject later writes")
		}
	}
}

func TestDurableIdempotencyAfterCompactionAndRestart(t *testing.T) {
	dir := t.TempDir()
	s, err := OpenStore(dir, 24*time.Hour, 3)
	if err != nil { t.Fatal(err) }
	req := PublishRequest{Body: "run-once", Priority: 3}
	first, dup, err := s.Publish("backup", req, "producer", "event-1", "digest-1")
	if err != nil || dup { t.Fatalf("initial publish failed: %v duplicate=%v", err, dup) }
	if err := s.Prune(); err != nil { t.Fatal(err) }
	if err := s.Close(); err != nil { t.Fatal(err) }
	s, err = OpenStore(dir, 24*time.Hour, 3)
	if err != nil { t.Fatal(err) }
	defer s.Close()
	second, dup, err := s.Publish("backup", req, "producer", "event-1", "digest-1")
	if err != nil || !dup || second.ID != first.ID {
		t.Fatalf("deduplication not preserved after restart: %v dup=%v", err, dup)
	}
}

func TestMissingFinalNewlineFailsClosed(t *testing.T) {
	dir := t.TempDir()
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil { t.Fatal(err) }
	_, _, err = s.Publish("alerts", PublishRequest{Body: "complete", Priority: 3}, "publisher", "", "")
	if err != nil { t.Fatal(err) }
	_ = s.Close()
	path := filepath.Join(dir, "messages.jsonl")
	b, err := os.ReadFile(path)
	if err != nil { t.Fatal(err) }
	if len(b) < 2 || b[len(b)-1] != '\n' { t.Fatal("unexpected log") }
	if err := os.WriteFile(path, b[:len(b)-1], 0600); err != nil { t.Fatal(err) }
	if reopened, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = reopened.Close()
		t.Fatal("missing newline should fail startup")
	}
	if _, err := VerifyLog(path); err == nil { t.Fatal("verifier missed missing delimiter") }
}

func TestOfflineLogVerifierDoesNotRevealPayloads(t *testing.T) {
	dir := t.TempDir()
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil { t.Fatal(err) }
	for _, topic := range []string{"private", "alerts"} {
		if _, _, err := s.Publish(topic, PublishRequest{Body: "confidential contents", Priority: 3}, "publisher", "", ""); err != nil { t.Fatal(err) }
	}
	_ = s.Close()
	report, err := VerifyLog(filepath.Join(dir, "messages.jsonl"))
	if err != nil { t.Fatal(err) }
	if report.Records != 2 || report.Topics != 2 || report.Bytes < 10 { t.Fatal(report) }
	b, err := json.Marshal(report)
	if err != nil { t.Fatal(err) }
	if bytes.Contains(b, []byte("confidential")) { t.Fatal("verifier leaked payload") }
}

func TestConcurrentStreamBudgetAndRecovery(t *testing.T) {
	_, h := setup(t)
	srv := httptest.NewServer(h)
	defer srv.Close()
	client := &http.Client{Timeout: 3 * time.Second}
	var open []*http.Response
	defer func() { for _, resp := range open { _ = resp.Body.Close() } }()
	connect := func() *http.Response {
		t.Helper()
		r, err := http.NewRequest(http.MethodGet, srv.URL+"/api/v1/topics/alerts/events", nil)
		if err != nil { t.Fatal(err) }
		r.Header.Set("Authorization", "Bearer "+adminToken)
		resp, err := client.Do(r)
		if err != nil { t.Fatal(err) }
		return resp
	}
	for i := 0; i < 4; i++ {
		resp := connect()
		if resp.StatusCode != http.StatusOK { t.Fatal(resp.Status) }
		open = append(open, resp)
	}
	rejected := connect()
	if rejected.StatusCode != http.StatusTooManyRequests || rejected.Header.Get("Retry-After") == "" {
		t.Fatal("expected 429 with retry guidance", rejected.Status)
	}
	_ = rejected.Body.Close()
	for _, resp := range open { _ = resp.Body.Close() }
	open = nil
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		resp := connect()
		if resp.StatusCode == http.StatusOK { _ = resp.Body.Close(); return }
		_ = resp.Body.Close()
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatal("streams did not release capacity")
}

func TestReadinessDetectsFailedPersistentWriter(t *testing.T) {
	s, h := setup(t)
	if got := req(t, h, "GET", "/readyz", "", "").Code; got != http.StatusOK {
		t.Fatalf("expected ready, got %d", got)
	}
	if err := s.file.Close(); err != nil { t.Fatal(err) }
	_, _, err := s.Publish("alerts", PublishRequest{Body: "fail", Priority: 3}, "publisher", "", "")
	if err == nil { t.Fatal("expected storage write to fail") }
	w := req(t, h, "GET", "/readyz", "", "")
	if w.Code != http.StatusServiceUnavailable || !strings.Contains(w.Body.String(), "unready") {
		t.Fatalf("storage failure should revoke readiness, got %d %s", w.Code, w.Body.String())
	}
	if got := req(t, h, "GET", "/healthz", "", "").Code; got != http.StatusOK {
		t.Fatalf("process health should remain available, got %d", got)
	}
}
