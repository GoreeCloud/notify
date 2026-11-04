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
	"syscall"
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
	lockFile    *os.File // OS-managed advisory lock: one writer per local journal.
	path        string
	messages    []Message
	subs        map[string]map[chan Message]struct{}
	dedup       map[string]Message
	retention   time.Duration
	maxPerTopic int
	published   uint64
	writeError  error // If append or fsync fails, prevent further writes until recovery.
}

// OpenStore owns a single-writer local journal. Do not mount a single data
// directory into multiple active service processes or nodes.
func OpenStore(dir string, retention time.Duration, maxPerTopic int) (*Store, error) {
	if retention < time.Hour || maxPerTopic < 1 {
		return nil, errors.New("invalid retention settings")
	}
	if err := os.MkdirAll(dir, 0700); err != nil {
		return nil, err
	}
	dataDir, err := os.Lstat(dir)
	if err != nil {
		return nil, err
	}
	if !dataDir.IsDir() || dataDir.Mode().Perm()&0077 != 0 {
		return nil, errors.New("notification data directory must be a private, non-symlink directory (chmod 0700)")
	}
	lockPath := filepath.Join(dir, ".notify.lock")
	if err := rejectSymlink(lockPath); err != nil {
		return nil, err
	}
	lock, err := os.OpenFile(lockPath, os.O_RDWR|os.O_CREATE, 0600)
	if err != nil {
		return nil, err
	}
	locked := false
	defer func() {
		if !locked {
			_ = lock.Close()
		}
	}()
	if err = verifyPrivateRegular(lock); err != nil {
		return nil, err
	}
	if err = syscall.Flock(int(lock.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); err != nil {
		return nil, fmt.Errorf("notification data directory already has an active writer: %w", err)
	}
	// The descriptor remains open for the lifetime of Store. Closing it also
	// releases the kernel flock if the process crashes or exits unexpectedly.
	path := filepath.Join(dir, "messages.jsonl")
	if err = rejectSymlink(path); err != nil {
		return nil, err
	}
	f, err := os.OpenFile(path, os.O_RDWR|os.O_CREATE|os.O_APPEND, 0600)
	if err != nil {
		return nil, err
	}
	s := &Store{file: f, lockFile: lock, path: path, subs: make(map[string]map[chan Message]struct{}), dedup: make(map[string]Message), retention: retention, maxPerTopic: maxPerTopic}
	// Fail closed on corrupt data; never silently discard potentially durable events.
	if err := verifyPrivateRegular(f); err != nil {
		_ = f.Close()
		return nil, err
	}
	if err := requireTerminatedLog(f); err != nil {
		_ = f.Close()
		return nil, err
	}
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 4096), 65536)
	cutoff := time.Now().UTC().Add(-retention)
	seen := make(map[string]struct{})
	for scanner.Scan() {
		var record storedMessage
		if err := json.Unmarshal(scanner.Bytes(), &record); err != nil || !validStoredMessage(record) {
			_ = f.Close()
			return nil, errors.New("invalid persisted record: corrupt JSONL file")
		}
		if _, ok := seen[record.ID]; ok {
			_ = f.Close()
			return nil, errors.New("duplicate message ID in persisted journal")
		}
		seen[record.ID] = struct{}{}
		if record.CreatedAt.Before(cutoff) {
			continue
		}
		m := record.Message
		m.Publisher = record.Publisher
		m.IdempotencyKey = record.IdempotencyKey
		m.PayloadDigest = record.PayloadDigest
		s.messages = append(s.messages, m)
		if m.IdempotencyKey != "" {
			key := dedupKey(m.Publisher, m.Topic, m.IdempotencyKey)
			if _, exists := s.dedup[key]; exists {
				_ = f.Close()
				return nil, errors.New("duplicate idempotency key in persisted journal")
			}
			s.dedup[key] = m
		}
	}
	if err := scanner.Err(); err != nil {
		_ = f.Close()
		return nil, err
	}
	if err := s.compactLocked(); err != nil {
		_ = s.file.Close()
		return nil, err
	}
	locked = true
	return s, nil
}

// This validation is shared by startup and the offline checker to avoid
// declaring an invalid journal healthy simply because a record is expired.
func validStoredMessage(record storedMessage) bool {
	return record.ID != "" && ValidTopic(record.Topic) && !record.CreatedAt.IsZero() &&
		record.Priority >= 1 && record.Priority <= 5 && record.Body != ""
}

func rejectSymlink(path string) error {
	info, err := os.Lstat(path)
	if errors.Is(err, os.ErrNotExist) {
		return nil
	}
	if err != nil {
		return err
	}
	if info.Mode()&os.ModeSymlink != 0 {
		return errors.New("symlink not allowed in notification journal directory")
	}
	return nil
}

func verifyPrivateRegular(f *os.File) error {
	info, err := f.Stat()
	if err != nil {
		return err
	}
	if !info.Mode().IsRegular() || info.Mode().Perm()&0077 != 0 {
		return errors.New("notification journal files must be private regular files (chmod 0600)")
	}
	return nil
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

// Healthy reports whether this process can still accept durable writes.
// Readiness is not a claim of end-to-end notification delivery.
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
	// Open the replacement before publishing it. If any earlier step fails,
	// keep the old active log descriptor intact so publishing still works.
	next, err := os.OpenFile(tmp.Name(), os.O_RDWR|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	if err = os.Rename(tmp.Name(), s.path); err != nil {
		_ = next.Close()
		return err
	}
	// The rename succeeds atomically on the supported Linux filesystem.
	// Switch descriptors immediately, even if directory fsync subsequently fails.
	old := s.file
	s.file = next
	_ = old.Close()
	if err = syncDir(filepath.Dir(s.path)); err != nil {
		// Durability is uncertain after the rename; refuse more writes.
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

// syncDir persists the rename metadata so a power loss does not silently
// revert a successful compaction on ordinary local Linux filesystems.
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
	fileErr := s.file.Close()
	if s.lockFile != nil {
		_ = syscall.Flock(int(s.lockFile.Fd()), syscall.LOCK_UN)
		if lockErr := s.lockFile.Close(); fileErr == nil {
			fileErr = lockErr
		}
	}
	return fileErr
}

// requireTerminatedLog detects a torn append even when the last JSON object
// happens to be parseable. Every accepted record is written with a newline.
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

// LogReport describes an offline validation of the persisted message log.
// No messages, token hashes, or notification bodies are included in the report.
type LogReport struct {
	Records int   `json:"records"`
	Topics  int   `json:"topics"`
	Bytes   int64 `json:"bytes"`
}

// VerifyLog is read-only. The caller must stop the writer or work on a
// point-in-time snapshot; verification during active appends is not reliable.
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
	idempotencyKeys := make(map[string]struct{})
	for scan.Scan() {
		var entry storedMessage
		if err := json.Unmarshal(scan.Bytes(), &entry); err != nil {
			return report, fmt.Errorf("malformed record %d: %w", report.Records+1, err)
		}
		if !validStoredMessage(entry) {
			return report, fmt.Errorf("invalid record %d", report.Records+1)
		}
		if _, ok := ids[entry.ID]; ok {
			return report, fmt.Errorf("duplicate record ID at line %d", report.Records+1)
		}
		ids[entry.ID] = struct{}{}
		if entry.IdempotencyKey != "" {
			key := dedupKey(entry.Publisher, entry.Topic, entry.IdempotencyKey)
			if _, exists := idempotencyKeys[key]; exists {
				return report, fmt.Errorf("duplicate idempotency key at line %d", report.Records+1)
			}
			idempotencyKeys[key] = struct{}{}
		}
		topics[entry.Topic] = struct{}{}
		report.Records++
	}
	if err := scan.Err(); err != nil {
		return report, err
	}
	report.Topics = len(topics)
	return report, nil
}
