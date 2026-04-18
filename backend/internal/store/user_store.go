package store

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	"supervideo-server/internal/models"
)

// UserStore implements domain.UserRepository backed by SQLite.
type UserStore struct {
	db DBTX
}

// NewUserStore constructs a UserStore.
func NewUserStore(db *sql.DB) *UserStore {
	return &UserStore{db: db}
}

// WithTx returns a copy of the store that operates within the given transaction.
func (s *UserStore) WithTx(tx *sql.Tx) *UserStore {
	return &UserStore{db: tx}
}

// Create inserts a new user and returns the created record.
func (s *UserStore) Create(ctx context.Context, user *models.User) (*models.User, error) {
	role := user.Role
	if role == "" {
		role = "viewer"
	}

	result, err := s.db.ExecContext(ctx,
		`INSERT INTO users (username, password_hash, role, updated_at)
		 VALUES (?, ?, ?, datetime('now'))`,
		strings.TrimSpace(user.Username),
		user.PasswordHash,
		role,
	)
	if err != nil {
		return nil, fmt.Errorf("create user %s: %w", user.Username, err)
	}
	id, _ := result.LastInsertId()
	return s.GetByID(ctx, int(id))
}

// GetByID fetches a user by primary key.
func (s *UserStore) GetByID(ctx context.Context, id int) (*models.User, error) {
	return s.scanUser(ctx,
		`SELECT id, username, password_hash, role, created_at, updated_at, last_login_at
		 FROM users WHERE id = ?`, id)
}

// GetByUsername looks up a user by username.
func (s *UserStore) GetByUsername(ctx context.Context, username string) (*models.User, error) {
	return s.scanUser(ctx,
		`SELECT id, username, password_hash, role, created_at, updated_at, last_login_at
		 FROM users WHERE username = ?`, strings.TrimSpace(username))
}

// Update persists changes to a user record.
func (s *UserStore) Update(ctx context.Context, user *models.User) error {
	_, err := s.db.ExecContext(ctx,
		`UPDATE users SET username = ?, role = ?, updated_at = datetime('now')
		 WHERE id = ?`,
		user.Username, user.Role, user.ID,
	)
	if err != nil {
		return fmt.Errorf("update user %d: %w", user.ID, err)
	}
	return nil
}

// SetPassword replaces the user's password hash.
func (s *UserStore) SetPassword(ctx context.Context, id int, passwordHash string) error {
	_, err := s.db.ExecContext(ctx,
		"UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
		passwordHash, id,
	)
	if err != nil {
		return fmt.Errorf("set password for user %d: %w", id, err)
	}
	return nil
}

// UpdateLastLogin stamps last_login_at = now.
func (s *UserStore) UpdateLastLogin(ctx context.Context, id int) error {
	_, err := s.db.ExecContext(ctx,
		"UPDATE users SET last_login_at = datetime('now'), updated_at = datetime('now') WHERE id = ?",
		id,
	)
	if err != nil {
		return fmt.Errorf("update last_login for user %d: %w", id, err)
	}
	return nil
}

// scanUser is a shared helper that executes a query expected to return exactly
// one user row.
func (s *UserStore) scanUser(ctx context.Context, query string, args ...interface{}) (*models.User, error) {
	var user models.User
	var createdAt, updatedAt string
	var lastLogin sql.NullString

	err := s.db.QueryRowContext(ctx, query, args...).Scan(
		&user.ID, &user.Username, &user.PasswordHash,
		&user.Role, &createdAt, &updatedAt, &lastLogin,
	)
	if err != nil {
		return nil, fmt.Errorf("scan user: %w", err)
	}
	user.CreatedAt = parseTime(createdAt)
	user.UpdatedAt = parseTime(updatedAt)
	user.LastLoginAt = parseNullTime(lastLogin)
	return &user, nil
}
