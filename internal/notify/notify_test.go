package notify

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
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
	s, err := OpenStore(filepath.Join(t.TempDir(), "private-data"), 24*time.Hour, 100)
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
	dir := filepath.Join(t.TempDir(), "private-data")
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

// A torn tail must not be silently repaired by startup compaction. Recover
// from a verified backup or inspect and repair the log offline first.
func TestTruncatedRecordFailsClosedWithoutMutation(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err = s.Publish("alerts", PublishRequest{Body: "sent", Priority: 3}, "publisher", "", ""); err != nil {
		t.Fatal(err)
	}
	if err = s.Close(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "messages.jsonl")
	f, err := os.OpenFile(path, os.O_APPEND|os.O_WRONLY, 0600)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = f.WriteString(`{"id":"incomplete`)
	_ = f.Close()
	before, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if reopened, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = reopened.Close()
		t.Fatal("expected corruption to stop startup")
	}
	after, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(before, after) {
		t.Fatal("corruption failure must not rewrite original disk data")
	}
}

func TestCompactionErrorLeavesExistingLogWritable(t *testing.T) {
	s, err := OpenStore(filepath.Join(t.TempDir(), "private-data"), 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	defer s.Close()
	original := s.path
	s.path = filepath.Join(t.TempDir(), "missing", "messages.jsonl")
	if err := s.Prune(); err == nil {
		t.Fatal("expected compaction failure")
	}
	s.path = original
	if _, _, err := s.Publish("alerts", PublishRequest{Body: "still writable", Priority: 3}, "producer", "", ""); err != nil {
		t.Fatal("compaction failure prematurely closed active writer:", err)
	}
}

func TestAppendFailureFailsClosed(t *testing.T) {
	s, err := OpenStore(filepath.Join(t.TempDir(), "private-data"), 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	// A closed writer simulates the write-error branch without fault injection.
	if err := s.file.Close(); err != nil {
		t.Fatal(err)
	}
	for i := 0; i < 2; i++ {
		if _, _, err := s.Publish("alerts", PublishRequest{Body: "fail", Priority: 3}, "producer", "", ""); err == nil {
			t.Fatal("writes must fail closed after storage failure")
		}
	}
}

func TestDurableIdempotencyAfterCompactionAndRestart(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 3)
	if err != nil {
		t.Fatal(err)
	}
	r := PublishRequest{Body: "run-once", Priority: 3}
	original, dup, err := s.Publish("backup", r, "producer", "event-1", "digest-1")
	if err != nil || dup {
		t.Fatalf("original write: %v duplicate=%v", err, dup)
	}
	if err := s.Prune(); err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := OpenStore(dir, 24*time.Hour, 3)
	if err != nil {
		t.Fatal(err)
	}
	defer reopened.Close()
	again, dup, err := reopened.Publish("backup", r, "producer", "event-1", "digest-1")
	if err != nil || !dup || again.ID != original.ID {
		t.Fatalf("idempotency failed after restart: %v duplicate=%v", err, dup)
	}
}

func TestConcurrentStreamBudgetAndRecovery(t *testing.T) {
	_, h := setup(t)
	srv := httptest.NewServer(h)
	defer srv.Close()
	client := &http.Client{Timeout: 3 * time.Second}
	var open []*http.Response
	defer func() {
		for _, resp := range open {
			_ = resp.Body.Close()
		}
	}()
	connect := func() *http.Response {
		t.Helper()
		r, err := http.NewRequest(http.MethodGet, srv.URL+"/api/v1/topics/alerts/events", nil)
		if err != nil {
			t.Fatal(err)
		}
		r.Header.Set("Authorization", "Bearer "+adminToken)
		resp, err := client.Do(r)
		if err != nil {
			t.Fatal(err)
		}
		return resp
	}
	for i := 0; i < 4; i++ {
		resp := connect()
		if resp.StatusCode != http.StatusOK {
			t.Fatal(resp.Status)
		}
		open = append(open, resp)
	}
	rejected := connect()
	if rejected.StatusCode != http.StatusTooManyRequests || rejected.Header.Get("Retry-After") == "" {
		t.Fatal("expected stream budget 429 with retry guidance", rejected.Status)
	}
	_ = rejected.Body.Close()
	for _, resp := range open {
		_ = resp.Body.Close()
	}
	open = nil
	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		resp := connect()
		if resp.StatusCode == http.StatusOK {
			_ = resp.Body.Close()
			return
		}
		_ = resp.Body.Close()
		time.Sleep(20 * time.Millisecond)
	}
	t.Fatal("closed streams did not release capacity")
}

func TestMissingFinalNewlineFailsClosed(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = s.Publish("alerts", PublishRequest{Body: "complete", Priority: 3}, "publisher", "", "")
	if err != nil {
		t.Fatal(err)
	}
	_ = s.Close()
	path := filepath.Join(dir, "messages.jsonl")
	b, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(b) < 2 || b[len(b)-1] != '\n' {
		t.Fatal("unexpected log format")
	}
	if err := os.WriteFile(path, b[:len(b)-1], 0600); err != nil {
		t.Fatal(err)
	}
	if opened, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = opened.Close()
		t.Fatal("missing delimiter should fail startup")
	}
	if _, err := VerifyLog(path); err == nil {
		t.Fatal("verifier missed truncated delimiter")
	}
}

func TestOfflineLogVerifierDoesNotRevealPayloads(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = s.Publish("private", PublishRequest{Body: "private data", Priority: 3}, "publisher", "", "")
	if err != nil {
		t.Fatal(err)
	}
	_, _, err = s.Publish("alerts", PublishRequest{Body: "public data", Priority: 3}, "publisher", "", "")
	if err != nil {
		t.Fatal(err)
	}
	_ = s.Close()
	report, err := VerifyLog(filepath.Join(dir, "messages.jsonl"))
	if err != nil {
		t.Fatal(err)
	}
	if report.Records != 2 || report.Topics != 2 || report.Bytes < 10 {
		t.Fatal(report)
	}
	b, err := json.Marshal(report)
	if err != nil {
		t.Fatal(err)
	}
	if bytes.Contains(b, []byte("private")) || bytes.Contains(b, []byte("data")) {
		t.Fatal("verifier report must not expose message contents")
	}
}

func TestReadinessDetectsFailedPersistentWriter(t *testing.T) {
	s, h := setup(t)
	if got := req(t, h, "GET", "/readyz", "", "").Code; got != http.StatusOK {
		t.Fatalf("expected healthy status, got %d", got)
	}
	if err := s.file.Close(); err != nil {
		t.Fatal(err)
	}
	_, _, err := s.Publish("alerts", PublishRequest{Body: "fail", Priority: 3}, "publisher", "", "")
	if err == nil {
		t.Fatal("expected storage write to fail")
	}
	w := req(t, h, "GET", "/readyz", "", "")
	if w.Code != http.StatusServiceUnavailable || !strings.Contains(w.Body.String(), "unready") {
		t.Fatalf("storage failure should revoke readiness, got %d %s", w.Code, w.Body.String())
	}
	if got := req(t, h, "GET", "/healthz", "", "").Code; got != http.StatusOK {
		t.Fatalf("process health should remain available, got %d", got)
	}
}

func TestPerPeerRequestBudgetIgnoresForwardedHeaders(t *testing.T) {
	_, h := setup(t)
	for n := 0; n < maxPeerRequests; n++ {
		r := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
		r.RemoteAddr = "198.51.100.20:8000"
		r.Header.Set("Authorization", "Bearer "+adminToken)
		r.Header.Set("X-Forwarded-For", fmt.Sprintf("203.0.113.%d", n%200))
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != http.StatusOK {
			t.Fatalf("unexpected throttle at request %d: %d", n, w.Code)
		}
	}
	r := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
	r.RemoteAddr = "198.51.100.20:9000"
	r.Header.Set("Authorization", "Bearer "+adminToken)
	r.Header.Set("Forwarded", "for=192.0.2.42")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusTooManyRequests || w.Header().Get("Retry-After") != "60" {
		t.Fatalf("expected real peer to be throttled, got %d", w.Code)
	}
	if w.Header().Get("X-Content-Type-Options") != "nosniff" {
		t.Fatal("missing security headers on 429")
	}
	r.RemoteAddr = "198.51.100.21:9000"
	w = httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusOK {
		t.Fatal("unrelated peer must not be throttled", w.Code)
	}
}

func TestInvalidBearerBudgetAndHealthExemption(t *testing.T) {
	_, h := setup(t)
	for n := 0; n < maxPeerFailures; n++ {
		r := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
		r.RemoteAddr = "198.51.100.50:4000"
		r.Header.Set("Authorization", "Bearer invalid-token")
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("auth attempt %d: %d", n, w.Code)
		}
	}
	r := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
	r.RemoteAddr = "198.51.100.50:4000"
	r.Header.Set("Authorization", "Bearer "+adminToken)
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusTooManyRequests {
		t.Fatalf("expected lockout for current peer window, got %d", w.Code)
	}
	r = httptest.NewRequest(http.MethodGet, "/readyz", nil)
	r.RemoteAddr = "198.51.100.50:4000"
	w = httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusOK {
		t.Fatal("readiness should remain observable")
	}
}

func TestPeerLimiterExpirationIPVersionAndCapacity(t *testing.T) {
	limiter := newPeerLimiter()
	now := time.Now()
	if !limiter.allow("[2001:db8:feed:1::a]:443", now) {
		t.Fatal("first IPv6 client rejected")
	}
	for i := 0; i < maxPeerRequests-1; i++ {
		if !limiter.allow("[2001:db8:feed:1::b]:8443", now) {
			t.Fatal("IPv6 subnet should have remaining capacity")
		}
	}
	if limiter.allow("[2001:db8:feed:1::c]:443", now) {
		t.Fatal("IPv6 /64 rotation evaded limit")
	}
	if !limiter.allow("[2001:db8:feed:2::a]:443", now) {
		t.Fatal("different IPv6 /64 must have separate budget")
	}
	if !limiter.allow("[2001:db8:feed:1::a]:443", now.Add(time.Minute)) {
		t.Fatal("expired window did not reset")
	}
	for n := 0; n < maxPeerEntries; n++ {
		limiter.peers[fmt.Sprintf("peer-%d", n)] = peerWindow{started: now}
	}
	if limiter.allow("192.0.2.100:443", now) {
		t.Fatal("full active limiter table should reject new peers")
	}
	if !limiter.allow("192.0.2.100:443", now.Add(2*time.Minute)) {
		t.Fatal("expired entries should be reclaimed")
	}
	if peerKey("garbage") != "unknown" {
		t.Fatal("invalid transport address must be bounded to common unknown bucket")
	}
}

func TestRejectDuplicateAndMalformedBearerHeaders(t *testing.T) {
	_, h := setup(t)
	for _, values := range [][]string{{"Bearer " + adminToken, "Bearer garbage"}, {"Bearer  " + adminToken}, {"Bearer " + adminToken + ",garbage"}, {"Bearer " + strings.Repeat("x", 2050)}} {
		r := httptest.NewRequest(http.MethodGet, "/api/v1/me", nil)
		for _, v := range values {
			r.Header.Add("Authorization", v)
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != http.StatusUnauthorized || w.Header().Get("WWW-Authenticate") == "" {
			t.Fatalf("ambiguous header accepted: status %d", w.Code)
		}
	}
}

func TestExclusiveJournalLockReleasedAfterClose(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	first, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	if second, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = second.Close()
		_ = first.Close()
		t.Fatal("two simultaneous writers were allowed")
	}
	if _, _, err := first.Publish("alerts", PublishRequest{Body: "still available", Priority: 3}, "producer", "", ""); err != nil {
		t.Fatal("failed lock attempt must not affect first writer", err)
	}
	if err := first.Close(); err != nil {
		t.Fatal(err)
	}
	reopened, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal("released advisory lock should permit reopen", err)
	}
	defer reopened.Close()
	if len(reopened.List("alerts", 10)) != 1 {
		t.Fatal("reopened journal did not retain data")
	}
}

func TestJournalRejectsInsecureDirectoryAndSymlink(t *testing.T) {
	parent := t.TempDir()
	openDir := filepath.Join(parent, "open")
	if err := os.Mkdir(openDir, 0755); err != nil {
		t.Fatal(err)
	}
	if s, err := OpenStore(openDir, 24*time.Hour, 100); err == nil {
		_ = s.Close()
		t.Fatal("world-readable directory should be rejected")
	}
	private := filepath.Join(parent, "private")
	if err := os.Mkdir(private, 0700); err != nil {
		t.Fatal(err)
	}
	external := filepath.Join(parent, "external")
	if err := os.WriteFile(external, []byte("SECRET"), 0600); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(external, filepath.Join(private, "messages.jsonl")); err != nil {
		t.Skip("symlink unsupported:", err)
	}
	if s, err := OpenStore(private, 24*time.Hour, 100); err == nil {
		_ = s.Close()
		t.Fatal("symlink journal should be rejected")
	}
	b, err := os.ReadFile(external)
	if err != nil || string(b) != "SECRET" {
		t.Fatal("symlink target modified")
	}
}

func TestStartupRejectsDuplicateJournalRecordsWithoutModification(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := s.Publish("alerts", PublishRequest{Body: "first", Priority: 3}, "producer", "", ""); err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "messages.jsonl")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	corrupted := append(append([]byte(nil), raw...), raw...)
	if err := os.WriteFile(path, corrupted, 0600); err != nil {
		t.Fatal(err)
	}
	if reopened, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = reopened.Close()
		t.Fatal("duplicate record accepted")
	}
	got, err := os.ReadFile(path)
	if err != nil || !bytes.Equal(got, corrupted) {
		t.Fatal("invalid journal modified")
	}
}

func TestExpiredInvalidRecordStillFailsStartup(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "messages.jsonl")
	bad := storedMessage{Message: Message{ID: "expired-bad", Topic: "alerts", Body: "content", Priority: 99, CreatedAt: time.Now().Add(-48 * time.Hour)}}
	data, _ := json.Marshal(bad)
	if err := os.WriteFile(path, append(data, '\n'), 0600); err != nil {
		t.Fatal(err)
	}
	if reopened, err := OpenStore(dir, time.Hour, 100); err == nil {
		_ = reopened.Close()
		t.Fatal("expired invalid record accepted")
	}
	if _, err := VerifyLog(path); err == nil {
		t.Fatal("offline verifier accepted expired invalid record")
	}
}

func TestDuplicateIdempotencyKeyFailsStartupAndOfflineCheck(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "private-data")
	s, err := OpenStore(dir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	if _, _, err := s.Publish("alerts", PublishRequest{Body: "first", Priority: 3}, "producer", "same-key", "digest-1"); err != nil {
		t.Fatal(err)
	}
	if err := s.Close(); err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "messages.jsonl")
	original, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	var record storedMessage
	if err := json.Unmarshal(bytes.TrimSpace(original), &record); err != nil {
		t.Fatal(err)
	}
	record.ID = "different-event-id"
	record.Body = "second"
	extra, _ := json.Marshal(record)
	corrupted := append(append([]byte(nil), original...), append(extra, '\n')...)
	if err := os.WriteFile(path, corrupted, 0600); err != nil {
		t.Fatal(err)
	}
	if reopened, err := OpenStore(dir, 24*time.Hour, 100); err == nil {
		_ = reopened.Close()
		t.Fatal("duplicate idempotency key accepted")
	}
	if _, err := VerifyLog(path); err == nil {
		t.Fatal("offline verifier accepted duplicate idempotency key")
	}
}
