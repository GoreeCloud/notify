package notify

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestBackupRefusesActiveJournalAndPreservesDestination(t *testing.T) {
	root := t.TempDir()
	sourceDir := filepath.Join(root, "data")
	backupDir := filepath.Join(root, "backup")
	if err := os.Mkdir(backupDir, 0700); err != nil {
		t.Fatal(err)
	}
	store, err := OpenStore(sourceDir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	defer store.Close()
	dest := filepath.Join(backupDir, "first.jsonl")
	if _, err := BackupJournal(filepath.Join(sourceDir, "messages.jsonl"), dest, false); err == nil {
		t.Fatal("active writer was not detected")
	}
	if _, err := os.Stat(dest); !os.IsNotExist(err) {
		t.Fatal("backup published despite active writer")
	}
}

func TestOfflineBackupAndRestoration(t *testing.T) {
	root := t.TempDir()
	sourceDir := filepath.Join(root, "data")
	backupDir := filepath.Join(root, "backup")
	restoreDir := filepath.Join(root, "restore")
	if err := os.Mkdir(backupDir, 0700); err != nil {
		t.Fatal(err)
	}
	store, err := OpenStore(sourceDir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal(err)
	}
	msg, _, err := store.Publish("alerts", PublishRequest{Body: "confidential event", Priority: 3}, "publisher", "immutable-key", "digest")
	if err != nil {
		t.Fatal(err)
	}
	if err := store.Close(); err != nil {
		t.Fatal(err)
	}
	source := filepath.Join(sourceDir, "messages.jsonl")
	dest := filepath.Join(backupDir, "backup.jsonl")
	report, err := BackupJournal(source, dest, false)
	if err != nil {
		t.Fatal(err)
	}
	if report.Records != 1 || report.Topics != 1 || report.SHA256 == "" {
		t.Fatal(report)
	}
	if bytes.Contains([]byte(report.SHA256), []byte("confidential")) {
		t.Fatal("report exposed payload")
	}
	original, err := os.ReadFile(source)
	if err != nil {
		t.Fatal(err)
	}
	saved, err := os.ReadFile(dest)
	if err != nil || !bytes.Equal(original, saved) {
		t.Fatal("backup content mismatch")
	}
	if _, err := BackupJournal(source, dest, false); err == nil {
		t.Fatal("backup overwritten")
	}
	if err := os.Mkdir(restoreDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(restoreDir, "messages.jsonl"), saved, 0600); err != nil {
		t.Fatal(err)
	}
	restored, err := OpenStore(restoreDir, 24*time.Hour, 100)
	if err != nil {
		t.Fatal("restoration should open", err)
	}
	defer restored.Close()
	list := restored.List("alerts", 10)
	if len(list) != 1 || list[0].ID != msg.ID {
		t.Fatal("restored event differs")
	}
	retry, dup, err := restored.Publish("alerts", PublishRequest{Body: "confidential event", Priority: 3}, "publisher", "immutable-key", "digest")
	if err != nil || !dup || retry.ID != msg.ID {
		t.Fatal("idempotency not preserved on restore", err)
	}
}

func TestOfflineBackupRejectsCorruptionAndNoLockByDefault(t *testing.T) {
	root := t.TempDir()
	snapDir := filepath.Join(root, "snapshot")
	outDir := filepath.Join(root, "backups")
	if err := os.Mkdir(snapDir, 0700); err != nil {
		t.Fatal(err)
	}
	if err := os.Mkdir(outDir, 0700); err != nil {
		t.Fatal(err)
	}
	source := filepath.Join(snapDir, "messages.jsonl")
	dest := filepath.Join(outDir, "verified.jsonl")
	if err := os.WriteFile(source, []byte("invalid-json\n"), 0600); err != nil {
		t.Fatal(err)
	}
	if _, err := BackupJournal(source, dest, false); err == nil {
		t.Fatal("missing lock must be explicit")
	}
	if _, err := BackupJournal(source, dest, true); err == nil {
		t.Fatal("corrupt snapshot must fail validation")
	}
	if _, err := os.Stat(dest); !os.IsNotExist(err) {
		t.Fatal("invalid backup published")
	}
}
