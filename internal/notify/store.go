package notify

import (
	"bufio"
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"
)

const maxDataBytes int64 = 32 << 20
const maxMessages = 10000

var ErrCapacity = errors.New("notification store capacity reached")

type Message struct {
	ID        string    `json:"id"`
	Topic     string    `json:"topic"`
	Title     string    `json:"title"`
	Body      string    `json:"body"`
	Priority  int       `json:"priority"`
	CreatedAt time.Time `json:"created_at"`
}

// Store is a single-process, append-only JSONL journal. Do not share its data
// file between instances. Limits are explicit to avoid unbounded disk growth.
type Store struct {
	mu       sync.RWMutex
	path     string
	messages []Message
	size     int64
}

func OpenStore(path string) (*Store, error) {
	if path == "" {
		return nil, errors.New("data file is required")
	}
	if err := os.MkdirAll(filepath.Dir(path), 0700); err != nil {
		return nil, err
	}
	f, err := os.OpenFile(path, os.O_CREATE|os.O_RDWR, 0600)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	info, err := f.Stat()
	if err != nil {
		return nil, err
	}
	if info.Size() > maxDataBytes {
		return nil, fmt.Errorf("notification journal exceeds %d bytes: %w", maxDataBytes, ErrCapacity)
	}
	s := &Store{path: path, size: info.Size()}
	scanner := bufio.NewScanner(f)
	scanner.Buffer(make([]byte, 4096), 16384)
	for scanner.Scan() {
		line := bytes.TrimSpace(scanner.Bytes())
		if len(line) == 0 {
			continue
		}
		var m Message
		if err := json.Unmarshal(line, &m); err != nil {
			return nil, fmt.Errorf("invalid journal line %d: %w", len(s.messages)+1, err)
		}
		s.messages = append(s.messages, m)
		if len(s.messages) > maxMessages {
			return nil, ErrCapacity
		}
	}
	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return s, nil
}

func (s *Store) Append(m Message) error {
	line, err := json.Marshal(m)
	if err != nil {
		return err
	}
	line = append(line, '\n')
	s.mu.Lock()
	defer s.mu.Unlock()
	if len(s.messages) >= maxMessages || s.size+int64(len(line)) > maxDataBytes {
		return ErrCapacity
	}
	f, err := os.OpenFile(s.path, os.O_WRONLY|os.O_APPEND, 0600)
	if err != nil {
		return err
	}
	_, writeErr := f.Write(line)
	if writeErr == nil {
		writeErr = f.Sync()
	}
	closeErr := f.Close()
	if writeErr != nil {
		return writeErr
	}
	if closeErr != nil {
		return closeErr
	}
	s.messages = append(s.messages, m)
	s.size += int64(len(line))
	return nil
}

func (s *Store) List(topic string, limit int) []Message {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Message, 0, limit)
	for i := len(s.messages) - 1; i >= 0 && len(out) < limit; i-- {
		if s.messages[i].Topic == topic {
			out = append(out, s.messages[i])
		}
	}
	return out
}
