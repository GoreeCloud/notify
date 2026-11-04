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
		return Message{}, false, err
	}
	if err = s.file.Sync(); err != nil {
		return Message{}, false, err
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

func (s *Store) Prune() error { s.mu.Lock(); defer s.mu.Unlock(); return s.compactLocked() }
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
	if err = s.file.Close(); err != nil {
		return err
	}
	if err = os.Rename(tmp.Name(), s.path); err != nil {
		return err
	}
	next, err := os.OpenFile(s.path, os.O_RDWR|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	s.file = next
	s.messages = kept
	s.dedup = make(map[string]Message)
	for _, m := range kept {
		if m.IdempotencyKey != "" {
			s.dedup[dedupKey(m.Publisher, m.Topic, m.IdempotencyKey)] = m
		}
	}
	return nil
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
