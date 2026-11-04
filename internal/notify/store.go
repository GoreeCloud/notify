package notify

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

type storedMessage struct {
	Message
	Publisher      string `json:"publisher,omitempty"`
	IdempotencyKey string `json:"idempotency_key,omitempty"`
	PayloadDigest  string `json:"payload_digest,omitempty"`
}

type Store struct {
	mu          sync.Mutex
	file        *os.File
	path        string
	messages    []Message
	subs        map[string]map[chan Message]struct{}
	dedup       map[string]Message
	retention   time.Duration
	maxPerTopic int
	published   uint64
	writeError  error // Reject writes after a failed append or fsync.
}

func OpenStore(dir string, retention time.Duration, maxPerTopic int) (*Store, error) {
	if retention < time.Hour || maxPerTopic < 1 {
		return nil, errors.New("invalid retention settings")
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		return nil, err
	}
	path := filepath.Join(dir, "messages.jsonl")
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0600)
	if err != nil {
		return nil, err
	}
	s := &Store{file: f, path: path, subs: make(map[string]map[chan Message]struct{}), dedup: make(map[string]Message), retention: retention, maxPerTopic: maxPerTopic}
	// Fail closed on corrupt data; never silently discard potentially durable events.
	if err := requireTerminatedLog(f); err != nil {
		_ = f.Close()
		return nil, err
	}
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 4096), 65536)
	cutoff := time.Now().UTC().Add(-retention)
	for scanner.Scan() {
		var record storedMessage
		if err := json.Unmarshal(scanner.Bytes(), &record); err != nil || record.ID == "" || !ValidTopic(record.Topic) || record.CreatedAt.IsZero() {
			f.Close()
			return nil, fmt.Errorf("invalid persisted record: %w", errors.New("corrupt JSONL file"))
		}
		if record.CreatedAt.Before(cutoff) {
			continue
		}
		m := record.Message
		m.Publisher = record.Publisher
		m.IdempotencyKey = record.IdempotencyKey
		m.PayloadDigest = record.PayloadDigest
		s.messages = append(s.messages, m)
		if m.IdempotencyKey != "" {
			s.dedup[dedupKey(m.Publisher, m.Topic, m.IdempotencyKey)] = m
		}
	}
	if err := scanner.Err(); err != nil {
		f.Close()
		return nil, err
	}
	if err := s.compactLocked(); err != nil {
		f.Close()
		return nil, err
	}
	return s, nil
}

func dedupKey(publisher, topic, key string) string { return publisher + ":" + topic + ":" + key }

func (s *Store) Publish(topic string, req PublishRequest, publisher, idemKey, digest string) (Message, bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.writeError != nil {
		return Message{}, false, s.writeError
	}
	if idemKey != "" {
		if old, ok := s.dedup[dedupKey(publisher, topic, idemKey)]; ok {
			if old.PayloadDigest != digest {
				return Message{}, false, errors.New("idempotency key already used for a different payload")
			}
			return old, true, nil
		}
	}
	id, err := newID()
	if err != nil {
		return Message{}, false, err
	}
	m := Message{ID: id, Topic: topic, Title: req.Title, Body: req.Body, Priority: req.Priority, Tags: req.Tags, Click: req.Click, CreatedAt: time.Now().UTC(), Publisher: publisher, IdempotencyKey: idemKey, PayloadDigest: digest}
	record, err := json.Marshal(storedMessage{Message: m, Publisher: publisher, IdempotencyKey: idemKey, PayloadDigest: digest})
	if err != nil {
		return Message{}, false, err
	}
	if _, err = s.file.Write(append(record, '\n')); err != nil {
		s.writeError = fmt.Errorf("message log append failed; stop and restore before retrying: %w", err)
		return Message{}, false, s.writeError
	}
	if err = s.file.Sync(); err != nil {
		s.writeError = fmt.Errorf("message log fsync failed; stop and restore before retrying: %w", err)
		return Message{}, false, s.writeError
	}
	s.messages = append(s.messages, m)
	s.published++
	if idemKey != "" {
		s.dedup[dedupKey(publisher, topic, idemKey)] = m
	}
	for ch := range s.subs[topic] {
		select {
		case ch <- m:
		default:
			close(ch)
			delete(s.subs[topic], ch)
		}
	}
	return m, false, nil
}

func (s *Store) List(topic string, limit int) []Message {
	s.mu.Lock()
	defer s.mu.Unlock()
	result := make([]Message, 0, limit)
	cutoff := time.Now().UTC().Add(-s.retention)
	for i := len(s.messages) - 1; i >= 0 && len(result) < limit; i-- {
		m := s.messages[i]
		if m.Topic == topic && !m.CreatedAt.Before(cutoff) {
			result = append(result, m)
		}
	}
	return result
}

func (s *Store) Topics(allowed func(string) bool) []string {
	s.mu.Lock()
	defer s.mu.Unlock()
	unique := make(map[string]struct{})
	for _, m := range s.messages {
		if allowed(m.Topic) {
			unique[m.Topic] = struct{}{}
		}
	}
	topics := make([]string, 0, len(unique))
	for topic := range unique {
		topics = append(topics, topic)
	}
	sort.Strings(topics)
	return topics
}

// Subscribe holds the same mutex as Publish so replay and live events have no gap.
func (s *Store) Subscribe(topic, after string) ([]Message, chan Message, func()) {
	s.mu.Lock()
	ch := make(chan Message, 128)
	if s.subs[topic] == nil {
		s.subs[topic] = make(map[chan Message]struct{})
	}
	s.subs[topic][ch] = struct{}{}
	recent := make([]Message, 0, 100)
	for i := len(s.messages) - 1; i >= 0 && len(recent) < 100; i-- {
		if s.messages[i].Topic == topic && time.Since(s.messages[i].CreatedAt) <= s.retention {
			recent = append(recent, s.messages[i])
		}
	}
	for i, j := 0, len(recent)-1; i < j; i, j = i+1, j-1 {
		recent[i], recent[j] = recent[j], recent[i]
	}
	if after != "" {
		position := -1
		for i, m := range recent {
			if m.ID == after {
				position = i
				break
			}
		}
		if position >= 0 {
			recent = recent[position+1:]
		} // Unknown cursors replay retained history safely.
	}
	s.mu.Unlock()
	return recent, ch, func() {
		s.mu.Lock()
		defer s.mu.Unlock()
		if _, ok := s.subs[topic][ch]; ok {
			delete(s.subs[topic], ch)
			close(ch)
		}
	}
}

// Healthy reports whether this instance can still accept durable writes.
// Readiness is not a promise of end-to-end notification delivery.
func (s *Store) Healthy() bool {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.writeError == nil
}

func (s *Store) Stats() (messages int, active int, published uint64) {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, m := range s.messages {
		if time.Since(m.CreatedAt) <= s.retention {
			messages++
		}
	}
	for _, subs := range s.subs {
		active += len(subs)
	}
	return messages, active, s.published
}

func (s *Store) Prune() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	if s.writeError != nil {
		return s.writeError
	}
	return s.compactLocked()
}
func (s *Store) compactLocked() error {
	cutoff := time.Now().UTC().Add(-s.retention)
	counts := map[string]int{}
	kept := make([]Message, 0, len(s.messages))
	for i := len(s.messages) - 1; i >= 0; i-- {
		m := s.messages[i]
		if m.CreatedAt.Before(cutoff) || counts[m.Topic] >= s.maxPerTopic {
			continue
		}
		kept = append(kept, m)
		counts[m.Topic]++
	}
	for i, j := 0, len(kept)-1; i < j; i, j = i+1, j-1 {
		kept[i], kept[j] = kept[j], kept[i]
	}
	tmp, err := os.CreateTemp(filepath.Dir(s.path), ".messages-*.tmp")
	if err != nil {
		return err
	}
	defer os.Remove(tmp.Name())
	if err = tmp.Chmod(0600); err != nil {
		tmp.Close()
		return err
	}
	for _, m := range kept {
		b, e := json.Marshal(storedMessage{Message: m, Publisher: m.Publisher, IdempotencyKey: m.IdempotencyKey, PayloadDigest: m.PayloadDigest})
		if e != nil {
			tmp.Close()
			return e
		}
		if _, e = tmp.Write(append(b, '\n')); e != nil {
			tmp.Close()
			return e
		}
	}
	if err = tmp.Sync(); err != nil {
		tmp.Close()
		return err
	}
	if err = tmp.Close(); err != nil {
		return err
	}
	// Open the replacement before publishing it. On a staging/rename error,
	// the original descriptor remains active and writable.
	next, err := os.OpenFile(tmp.Name(), os.O_RDWR|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	if err = os.Rename(tmp.Name(), s.path); err != nil {
		_ = next.Close()
		return err
	}
	// On a local Linux filesystem rename atomically installs the new log.
	old := s.file
	s.file = next
	_ = old.Close()
	if err = syncDir(filepath.Dir(s.path)); err != nil {
		s.writeError = fmt.Errorf("message log directory fsync failed: %w", err)
		return s.writeError
	}
	s.messages = kept
	s.dedup = make(map[string]Message)
	for _, m := range kept {
		if m.IdempotencyKey != "" {
			s.dedup[dedupKey(m.Publisher, m.Topic, m.IdempotencyKey)] = m
		}
	}
	return nil
}
// syncDir persists the rename metadata on supported local Linux filesystems.
func syncDir(path string) error {
	d, err := os.Open(path)
	if err != nil {
		return err
	}
	defer d.Close()
	return d.Sync()
}

func (s *Store) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	for _, group := range s.subs {
		for ch := range group {
			close(ch)
		}
	}
	s.subs = map[string]map[chan Message]struct{}{}
	return s.file.Close()
}

// requireTerminatedLog detects a torn append even if the last JSON record
// happens to be parseable. Every accepted record ends in a newline.
func requireTerminatedLog(f *os.File) error {
	info, err := f.Stat()
	if err != nil {
		return err
	}
	if info.Size() == 0 {
		return nil
	}
	var end [1]byte
	if _, err := f.ReadAt(end[:], info.Size()-1); err != nil {
		return err
	}
	if end[0] != '\n' {
		return errors.New("message log lacks final newline (possible interrupted append); restore from verified backup or repair offline")
	}
	return nil
}

// LogReport is a content-free summary of an offline log integrity check.
type LogReport struct {
	Records int   `json:"records"`
	Topics  int   `json:"topics"`
	Bytes   int64 `json:"bytes"`
}

// VerifyLog is read-only; callers must stop writers or use a consistent snapshot.
func VerifyLog(path string) (LogReport, error) {
	var report LogReport
	f, err := os.Open(path)
	if err != nil {
		return report, err
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		return report, err
	}
	if !info.Mode().IsRegular() {
		return report, errors.New("message log is not a regular file")
	}
	report.Bytes = info.Size()
	if err := requireTerminatedLog(f); err != nil {
		return report, err
	}
	if _, err := f.Seek(0, 0); err != nil {
		return report, err
	}
	scan := bufio.NewScanner(f)
	scan.Buffer(make([]byte, 4096), 65536)
	topics := make(map[string]struct{})
	ids := make(map[string]struct{})
	for scan.Scan() {
		var entry storedMessage
		if err := json.Unmarshal(scan.Bytes(), &entry); err != nil {
			return report, fmt.Errorf("malformed record %d: %w", report.Records+1, err)
		}
		if entry.ID == "" || !ValidTopic(entry.Topic) || entry.CreatedAt.IsZero() || entry.Priority < 1 || entry.Priority > 5 {
			return report, fmt.Errorf("invalid record %d", report.Records+1)
		}
		if _, ok := ids[entry.ID]; ok {
			return report, fmt.Errorf("duplicate record ID at line %d", report.Records+1)
		}
		ids[entry.ID] = struct{}{}
		topics[entry.Topic] = struct{}{}
		report.Records++
	}
	if err := scan.Err(); err != nil {
		return report, err
	}
	report.Topics = len(topics)
	return report, nil
}
