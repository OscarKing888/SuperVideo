package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"fmt"
	"time"

	"supervideo-server/internal/models"
)

// SessionStore implements domain.SessionRepository backed by SQLite.
type SessionStore struct {
	db *sql.DB
}

// NewSessionStore constructs a SessionStore.
func NewSessionStore(db *sql.DB) *SessionStore {
	return &SessionStore{db: db}
}

// Create issues a new session valid for `hours` hours.
func (s *SessionStore) Create(userID int, hours int) (*models.UserSession, error) {
	token := generateSessionToken()
	expiresAt := time.Now().UTC().Add(time.Duration(hours) * time.Hour)

	result, err := s.db.Exec(
		"INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
		token,
		userID,
		expiresAt.Format(sqliteTimeFormat),
		time.Now().UTC().Format(sqliteTimeFormat),
	)
	if err != nil {
		return nil, fmt.Errorf("create session for user %d: %w", userID, err)
	}

	id, _ := result.LastInsertId()
	return &models.UserSession{
		ID:        int(id),
		Token:     token,
		UserID:    userID,
		ExpiresAt: expiresAt,
		CreatedAt: time.Now().UTC(),
	}, nil
}

// GetByToken fetches a session. Expired sessions are auto-deleted.
func (s *SessionStore) GetByToken(token string) (*models.UserSession, error) {
	var session models.UserSession
	var expiresAt, createdAt string

	err := s.db.QueryRow(
		"SELECT id, token, user_id, expires_at, created_at FROM sessions WHERE token = ?",
		token,
	).Scan(&session.ID, &session.Token, &session.UserID, &expiresAt, &createdAt)
	if err != nil {
		return nil, fmt.Errorf("get session by token: %w", err)
	}

	session.ExpiresAt = parseTime(expiresAt)
	session.CreatedAt = parseTime(createdAt)
	if time.Now().UTC().After(session.ExpiresAt) {
		_ = s.Delete(token)
		return nil, sql.ErrNoRows
	}
	return &session, nil
}

// Delete removes a single session by token (used at logout).
func (s *SessionStore) Delete(token string) error {
	if _, err := s.db.Exec("DELETE FROM sessions WHERE token = ?", token); err != nil {
		return fmt.Errorf("delete session: %w", err)
	}
	return nil
}

// DeleteByUserID invalidates ALL sessions for a user.
func (s *SessionStore) DeleteByUserID(userID int) error {
	if _, err := s.db.Exec("DELETE FROM sessions WHERE user_id = ?", userID); err != nil {
		return fmt.Errorf("delete sessions for user %d: %w", userID, err)
	}
	return nil
}

func generateSessionToken() string {
	buffer := make([]byte, 32)
	_, _ = rand.Read(buffer)
	return hex.EncodeToString(buffer)
}
