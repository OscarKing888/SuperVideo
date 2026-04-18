package domain

import (
	"context"

	"supervideo-server/internal/models"
)

// ClientRepository defines data access operations for client machines.
type ClientRepository interface {
	Create(ctx context.Context, client *models.Client) (*models.Client, error)
	GetByID(ctx context.Context, id string) (*models.Client, error)
	GetByAPIKey(ctx context.Context, apiKey string) (*models.Client, error)
	GetByMachineID(ctx context.Context, machineID string) (*models.Client, error)
	List(ctx context.Context) ([]models.Client, error)
	UpdateLastSeen(ctx context.Context, id string) error
}
