package notify

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"syscall"
)

// BackupReport contains only integrity metadata; message bodies and credential
// hashes must never be included in status output.
type BackupReport struct {
	Records int    `json:"records"`
	Topics  int    `json:"topics"`
	Bytes   int64  `json:"bytes"`
	SHA256  string `json:"sha256"`
}

// BackupJournal creates a no-overwrite, fsynced local backup of a stopped
// notification journal or an independently consistent filesystem snapshot.
// It does not encrypt data; operators must use approved encrypted storage.
// allowNoLock is required only for immutable snapshots without .notify.lock.
func BackupJournal(source, destination string, allowNoLock bool) (BackupReport, error) {
	var result BackupReport
	srcPath, err := filepath.Abs(source)
	if err != nil {
		return result, err
	}
	dstPath, err := filepath.Abs(destination)
	if err != nil {
		return result, err
	}
	if srcPath == dstPath || filepath.Dir(srcPath) == filepath.Dir(dstPath) {
		return result, errors.New("backup destination must be in a different private directory")
	}
	if err = verifyPrivateDirectory(filepath.Dir(srcPath)); err != nil {
		return result, err
	}
	if err = verifyPrivateDirectory(filepath.Dir(dstPath)); err != nil {
		return result, err
	}
	if err = rejectSymlink(srcPath); err != nil {
		return result, err
	}

	lockPath := filepath.Join(filepath.Dir(srcPath), ".notify.lock")
	if err = rejectSymlink(lockPath); err != nil {
		return result, err
	}
	lock, lockErr := os.Open(lockPath)
	switch {
	case lockErr == nil:
		defer lock.Close()
		if err := verifyPrivateRegular(lock); err != nil {
			return result, err
		}
		if err := syscall.Flock(int(lock.Fd()), syscall.LOCK_SH|syscall.LOCK_NB); err != nil {
			return result, fmt.Errorf("journal is in use by a writer; stop it or snapshot first: %w", err)
		}
		defer syscall.Flock(int(lock.Fd()), syscall.LOCK_UN)
	case errors.Is(lockErr, os.ErrNotExist) && allowNoLock:
		// No lock file is only acceptable for a verified point-in-time snapshot.
	case errors.Is(lockErr, os.ErrNotExist):
		return result, errors.New("missing journal lock file; require a stopped service or explicit -snapshot flag")
	default:
		return result, lockErr
	}

	if _, err := os.Lstat(dstPath); err == nil {
		return result, errors.New("destination already exists; backups are never overwritten")
	} else if !errors.Is(err, os.ErrNotExist) {
		return result, err
	}

	src, err := os.Open(srcPath)
	if err != nil {
		return result, err
	}
	defer src.Close()
	if err := verifyPrivateRegular(src); err != nil {
		return result, err
	}
	verified, err := VerifyLog(srcPath)
	if err != nil {
		return result, fmt.Errorf("source failed journal validation: %w", err)
	}

	temp, err := os.CreateTemp(filepath.Dir(dstPath), ".notify-backup-*.tmp")
	if err != nil {
		return result, err
	}
	tmpPath := temp.Name()
	defer os.Remove(tmpPath)
	if err := temp.Chmod(0600); err != nil {
		_ = temp.Close()
		return result, err
	}
	hasher := sha256.New()
	count, err := io.Copy(io.MultiWriter(temp, hasher), src)
	if err != nil {
		_ = temp.Close()
		return result, err
	}
	if err := temp.Sync(); err != nil {
		_ = temp.Close()
		return result, err
	}
	if err := temp.Close(); err != nil {
		return result, err
	}
	if count != verified.Bytes {
		return result, errors.New("source journal changed during copy")
	}
	copyReport, err := VerifyLog(tmpPath)
	if err != nil {
		return result, fmt.Errorf("backup failed journal validation: %w", err)
	}
	if copyReport.Bytes != verified.Bytes || copyReport.Records != verified.Records || copyReport.Topics != verified.Topics {
		return result, errors.New("backup journal did not match source validation")
	}
	// Compare with a fresh pass of source bytes to detect concurrent mutation
	// outside a cooperating lock protocol (or a moving snapshot).
	if _, err := src.Seek(0, io.SeekStart); err != nil {
		return result, err
	}
	second := sha256.New()
	secondBytes, err := io.Copy(second, src)
	if err != nil {
		return result, err
	}
	if secondBytes != count || !equalHash(hasher.Sum(nil), second.Sum(nil)) {
		return result, errors.New("source journal changed during backup; discard snapshot")
	}
	// Hard-link staging into place for atomic creation without overwriting an
	// existing backup. Both paths live on the same local destination filesystem.
	if err := os.Link(tmpPath, dstPath); err != nil {
		return result, fmt.Errorf("publish backup without overwrite: %w", err)
	}
	if err := syncDir(filepath.Dir(dstPath)); err != nil {
		return result, fmt.Errorf("backup directory sync uncertain: %w", err)
	}
	if err := os.Remove(tmpPath); err != nil {
		return result, err
	}
	if err := syncDir(filepath.Dir(dstPath)); err != nil {
		return result, fmt.Errorf("backup temp cleanup sync uncertain: %w", err)
	}
	result = BackupReport{Records: verified.Records, Topics: verified.Topics, Bytes: count, SHA256: hex.EncodeToString(hasher.Sum(nil))}
	return result, nil
}

func verifyPrivateDirectory(path string) error {
	info, err := os.Lstat(path)
	if err != nil {
		return err
	}
	if !info.IsDir() || info.Mode().Perm()&0077 != 0 {
		return errors.New("backup/source directories must be non-symlink private directories (chmod 0700)")
	}
	return nil
}

func equalHash(a, b []byte) bool {
	if len(a) != len(b) {
		return false
	}
	var different byte
	for i := range a {
		different |= a[i] ^ b[i]
	}
	return different == 0
}
