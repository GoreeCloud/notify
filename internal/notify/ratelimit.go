package notify

import (
	"net"
	"sync"
	"time"
)

// peerLimiter limits requests and unsuccessful authentication by the actual TCP
// peer. Client-provided forwarding headers are deliberately ignored; an edge
// reverse proxy must enforce its own per-client controls before forwarding.
// The bounded map prevents a flood of unique peer addresses from growing
// application memory indefinitely.
type peerLimiter struct {
	mu    sync.Mutex
	peers map[string]peerWindow
}

type peerWindow struct {
	started  time.Time
	requests int
	failures int
}

const (
	peerWindowDuration = time.Minute
	maxPeerEntries     = 10000
	maxPeerRequests    = 240
	maxPeerFailures    = 30
)

func newPeerLimiter() *peerLimiter { return &peerLimiter{peers: make(map[string]peerWindow)} }

func (l *peerLimiter) allow(remote string, now time.Time) bool {
	key := peerKey(remote)
	l.mu.Lock()
	defer l.mu.Unlock()
	w, present := l.peers[key]
	if present && now.Sub(w.started) >= peerWindowDuration {
		delete(l.peers, key)
		present = false
	}
	if !present {
		if len(l.peers) >= maxPeerEntries {
			// Expired entries are reclaimed when the table fills; do not
			// evict active peers to admit an unbounded stream of new peers.
			for addr, entry := range l.peers {
				if now.Sub(entry.started) >= peerWindowDuration {
					delete(l.peers, addr)
				}
			}
			if len(l.peers) >= maxPeerEntries {
				return false
			}
		}
		w = peerWindow{started: now}
	}
	if w.requests >= maxPeerRequests || w.failures >= maxPeerFailures {
		return false
	}
	w.requests++
	l.peers[key] = w
	return true
}

func (l *peerLimiter) failedAuth(remote string, now time.Time) {
	key := peerKey(remote)
	l.mu.Lock()
	defer l.mu.Unlock()
	w, ok := l.peers[key]
	if !ok || now.Sub(w.started) >= peerWindowDuration {
		return
	}
	w.failures++
	l.peers[key] = w
}

// peerKey groups IPv6 addresses by /64 so rotating interface identifiers
// cannot evade per-peer limits or exhaust the in-memory limiter table.
func peerKey(remote string) string {
	host, _, err := net.SplitHostPort(remote)
	if err != nil {
		return "unknown"
	}
	ip := net.ParseIP(host)
	if ip == nil {
		return "unknown"
	}
	if v4 := ip.To4(); v4 != nil {
		return v4.String()
	}
	return ip.Mask(net.CIDRMask(64, 128)).String() + "/64"
}
