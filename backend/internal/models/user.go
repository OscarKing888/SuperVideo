package models

import "time"

// User represents a dashboard user account.
// PasswordHash is never serialised — the `json:"-"` tag prevents leaking.
type User struct {
	ID           int        `json:"id"`
	Username     string     `json:"username"`
	PasswordHash string     `json:"-"`
	Role         string     `json:"role"`
	CreatedAt    time.Time  `json:"created_at"`
	UpdatedAt    time.Time  `json:"updated_at"`
	LastLoginAt  *time.Time `json:"last_login_at,omitempty"`
}

// UserSession is an opaque session token for cookie-based auth.
type UserSession struct {
	ID        int       `json:"id"`
	Token     string    `json:"token"`
	UserID    int       `json:"user_id"`
	ExpiresAt time.Time `json:"expires_at"`
	CreatedAt time.Time `json:"created_at"`
}

// LoginRequest is the DTO for POST /api/auth/login.
type LoginRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

// RegisterRequest is the DTO for POST /api/auth/register.
type RegisterRequest struct {
	Username string `json:"username"`
	Password string `json:"password"`
	Role     string `json:"role,omitempty"`
}
