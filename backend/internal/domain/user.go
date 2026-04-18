package domain

import (
	"context"

	"supervideo-server/internal/models"
)

// UserRepository defines data access operations for user accounts.
type UserRepository interface {
	Create(ctx context.Context, user *models.User) (*models.User, error)
	GetByID(ctx context.Context, id int) (*models.User, error)
	GetByUsername(ctx context.Context, username string) (*models.User, error)
	Update(ctx context.Context, user *models.User) error
	SetPassword(ctx context.Context, id int, passwordHash string) error
}

// SessionRepository defines data access operations for user sessions.
type SessionRepository interface {
	Create(userID int, hours int) (*models.UserSession, error)
	GetByToken(token string) (*models.UserSession, error)
	Delete(token string) error
	DeleteByUserID(userID int) error
}
