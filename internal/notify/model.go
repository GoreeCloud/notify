package notify

import (
	"crypto/rand"
	"encoding/hex"
	"errors"
	"net/url"
	"regexp"
	"strings"
	"time"
)

var topicPattern = regexp.MustCompile(`^[A-Za-z0-9_-]{1,64}$`)

type Message struct {
	ID        string    `json:"id"`
	Topic     string    `json:"topic"`
	Title     string    `json:"title,omitempty"`
	Body      string    `json:"body"`
	Priority  int       `json:"priority"`
	Tags      []string  `json:"tags,omitempty"`
	Click     string    `json:"click,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	// Internal fields persist for safe duplicate handling and are never exported.
	Publisher      string `json:"-"`
	IdempotencyKey string `json:"-"`
	PayloadDigest  string `json:"-"`
}

type PublishRequest struct {
	Title    string   `json:"title"`
	Body     string   `json:"body"`
	Priority int      `json:"priority"`
	Tags     []string `json:"tags"`
	Click    string   `json:"click"`
}

func ValidTopic(topic string) bool { return topicPattern.MatchString(topic) }

func Validate(req *PublishRequest) error {
	if strings.TrimSpace(req.Body) == "" {
		return errors.New("body is required")
	}
	if len(req.Body) > 4096 || len(req.Title) > 120 {
		return errors.New("message is too long")
	}
	if req.Priority == 0 {
		req.Priority = 3
	}
	if req.Priority < 1 || req.Priority > 5 {
		return errors.New("priority must be between 1 and 5")
	}
	if len(req.Tags) > 12 {
		return errors.New("too many tags")
	}
	for _, tag := range req.Tags {
		if len(tag) < 1 || len(tag) > 32 || !topicPattern.MatchString(tag) {
			return errors.New("invalid tag")
		}
	}
	if req.Click != "" {
		u, err := url.Parse(req.Click)
		if err != nil || u.Host == "" || (u.Scheme != "https" && u.Scheme != "http") || u.User != nil {
			return errors.New("click must be an HTTP(S) URL without embedded credentials")
		}
	}
	return nil
}

func newID() (string, error) {
	var data [16]byte
	if _, err := rand.Read(data[:]); err != nil {
		return "", err
	}
	return hex.EncodeToString(data[:]), nil
}
