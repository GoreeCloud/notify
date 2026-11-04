// GoreeCloud Notify offline journal backup. No production service modifications.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"

	"github.com/GoreeCloud/notify/internal/notify"
)

func main() {
	file := flag.String("file", "", "source messages.jsonl from stopped service or consistent snapshot")
	out := flag.String("out", "", "new path in a private backup directory (will not overwrite)")
	snapshot := flag.Bool("snapshot", false, "allow a verified immutable snapshot without a .notify.lock file")
	flag.Parse()
	if flag.NArg() != 0 || *file == "" || *out == "" {
		fmt.Fprintln(os.Stderr, "usage: notifybackup -file SOURCE/messages.jsonl -out PRIVATE_BACKUPS/backup.jsonl [-snapshot]")
		os.Exit(2)
	}
	report, err := notify.BackupJournal(*file, *out, *snapshot)
	if err != nil {
		fmt.Fprintln(os.Stderr, "backup failed:", err)
		os.Exit(1)
	}
	_ = json.NewEncoder(os.Stdout).Encode(report)
}
