package notify

import (
	"crypto/sha256"
	"crypto/subtle"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"strings"
)

type Principal struct {
	Name   string   `json:"name"`
	Role   string   `json:"role"`
	Topics []string `json:"topics"`
}
type tokenEntry struct {
	Name   string   `json:"name"`
	SHA256 string   `json:"sha256"`
	Role   string   `json:"role"`
	Topics []string `json:"topics"`
}
type credential struct {
	principal Principal
	hash      [32]byte
}
type Auth struct{ credentials []credential }

// The bootstrap token is intentionally mandatory: the service must not start publicly writable.
func NewAuth(adminToken, aclFile string) (*Auth, error) {
	if len(adminToken) < 32 || strings.TrimSpace(adminToken) != adminToken || strings.HasPrefix(adminToken, "REPLACE_") {
		return nil, errors.New("NOTIFY_ADMIN_TOKEN must contain at least 32 non-whitespace-outer characters")
	}
	a := &Auth{credentials: []credential{{principal: Principal{Name: "administrator", Role: "admin", Topics: []string{"*"}}, hash: sha256.Sum256([]byte(adminToken))}}}
	if aclFile == "" {
		return a, nil
	}
	raw, err := os.ReadFile(aclFile)
	if err != nil {
		return nil, err
	}
	var entries []tokenEntry
	if err := json.Unmarshal(raw, &entries); err != nil {
		return nil, err
	}
	for _, item := range entries {
		if item.Name == "" || (item.Role != "subscriber" && item.Role != "publisher") || len(item.Topics) == 0 {
			return nil, errors.New("invalid ACL entry")
		}
		rawHash, err := hex.DecodeString(item.SHA256)
		if err != nil || len(rawHash) != 32 {
			return nil, errors.New("invalid ACL token hash")
		}
		for _, t := range item.Topics {
			if t != "*" && !ValidTopic(t) {
				return nil, errors.New("invalid ACL topic")
			}
		}
		var hashed [32]byte
		copy(hashed[:], rawHash)
		a.credentials = append(a.credentials, credential{principal: Principal{Name: item.Name, Role: item.Role, Topics: item.Topics}, hash: hashed})
	}
	return a, nil
}
func (a *Auth) Identify(token string) (Principal, bool) {
	if token == "" {
		return Principal{}, false
	}
	hashed := sha256.Sum256([]byte(token))
	for _, entry := range a.credentials {
		if subtle.ConstantTimeCompare(hashed[:], entry.hash[:]) == 1 {
			return entry.principal, true
		}
	}
	return Principal{}, false
}
func (p Principal) Allowed(topic, action string) bool {
	if p.Role == "admin" {
		return true
	}
	if action == "publish" && p.Role != "publisher" {
		return false
	}
	if action == "read" && p.Role != "subscriber" {
		return false
	}
	for _, t := range p.Topics {
		if t == "*" || t == topic {
			return true
		}
	}
	return false
}
