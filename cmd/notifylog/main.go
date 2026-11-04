// GoreeCloud Notify offline message log inspector.
// Run only against a stopped service or a consistent filesystem snapshot.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/GoreeCloud/notify/internal/notify"
)

func main() {
	path := flag.String("file", "./data/messages.jsonl", "path to a stopped/snapshotted Notify message log")
	flag.Parse()
	if flag.NArg() != 0 {
		fmt.Fprintln(os.Stderr, "usage: notifylog -file PATH")
		os.Exit(2)
	}
	report, err := notify.VerifyLog(*path)
	if err != nil {
		fmt.Fprintln(os.Stderr, "verification failed:", err)
		os.Exit(1)
	}
	_ = json.NewEncoder(os.Stdout).Encode(report)
}
