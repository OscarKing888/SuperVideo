package service

import (
	"context"
	"fmt"
	"strings"

	"supervideo-server/internal/config"
	"supervideo-server/internal/models"
	"supervideo-server/internal/security"
	"supervideo-server/internal/store"
)

// UserService encapsulates user registration, login, and profile logic.
type UserService struct {
	users    *store.UserStore
	sessions *store.SessionStore
	cfg      *config.Config
}

// NewUserService constructs a UserService.
func NewUserService(cfg *config.Config, users *store.UserStore, sessions *store.SessionStore) *UserService {
	return &UserService{cfg: cfg, users: users, sessions: sessions}
}

// Register creates a new user account, validates input, hashes the
// password, and returns the user with an auto-login session.
func (s *UserService) Register(ctx context.Context, req models.RegisterRequest) (*models.User, *models.UserSession, error) {
	username := strings.TrimSpace(req.Username)
	if username == "" {
		return nil, nil, fmt.Errorf("username is required")
	}
	if err := security.ValidatePassword(req.Password); err != nil {
		return nil, nil, err
	}

	hash, err := security.HashPassword(req.Password)
	if err != nil {
		return nil, nil, fmt.Errorf("hash password: %w", err)
	}

	role := strings.TrimSpace(req.Role)
	if role == "" {
		role = "viewer"
	}

	user := &models.User{
		Username:     username,
		PasswordHash: hash,
		Role:         role,
	}

	created, err := s.users.Create(ctx, user)
	if err != nil {
		return nil, nil, fmt.Errorf("create user: %w", err)
	}

	session, err := s.sessions.Create(created.ID, s.cfg.SessionHours)
	if err != nil {
		return nil, nil, fmt.Errorf("create session: %w", err)
	}

	return created, session, nil
}

// Login verifies credentials and returns the user with a new session.
func (s *UserService) Login(ctx context.Context, username, password string) (*models.User, *models.UserSession, error) {
	user, err := s.users.GetByUsername(ctx, strings.TrimSpace(username))
	if err != nil {
		return nil, nil, fmt.Errorf("invalid username or password")
	}
	if !security.CheckPassword(user.PasswordHash, password) {
		return nil, nil, fmt.Errorf("invalid username or password")
	}

	session, err := s.sessions.Create(user.ID, s.cfg.SessionHours)
	if err != nil {
		return nil, nil, fmt.Errorf("create session: %w", err)
	}

	_ = s.users.UpdateLastLogin(ctx, user.ID)

	return user, session, nil
}

// Logout invalidates a session by token.
func (s *UserService) Logout(ctx context.Context, token string) error {
	return s.sessions.Delete(token)
}

// GetBySessionToken resolves a session token to the owning user.
func (s *UserService) GetBySessionToken(ctx context.Context, token string) (*models.User, error) {
	session, err := s.sessions.GetByToken(token)
	if err != nil {
		return nil, err
	}
	user, err := s.users.GetByID(ctx, session.UserID)
	if err != nil {
		return nil, err
	}
	return user, nil
}

// GetProfile returns a user by ID.
func (s *UserService) GetProfile(ctx context.Context, userID int) (*models.User, error) {
	return s.users.GetByID(ctx, userID)
}
