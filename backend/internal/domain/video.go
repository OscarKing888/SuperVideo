package domain

import (
	"context"

	"supervideo-server/internal/models"
)

// VideoRepository defines data access operations for video records.
type VideoRepository interface {
	Create(ctx context.Context, video *models.Video) (*models.Video, error)
	GetByID(ctx context.Context, id string) (*models.Video, error)
	GetByClientAndHash(ctx context.Context, clientID, fileHash string) (*models.Video, error)
	List(ctx context.Context, limit, offset int) ([]models.Video, error)
	ListByClient(ctx context.Context, clientID string) ([]models.Video, error)
	Count(ctx context.Context) (int, error)
}

// DetectionRepository defines data access operations for detection records.
type DetectionRepository interface {
	CreateBatch(ctx context.Context, detections []models.Detection) error
	ListByVideo(ctx context.Context, videoID string) ([]models.Detection, error)
}

// ClassificationRepository defines data access operations for classification records.
type ClassificationRepository interface {
	CreateBatch(ctx context.Context, classifications []models.Classification) error
	ListByDetection(ctx context.Context, detectionID string) ([]models.Classification, error)
	SpeciesStats(ctx context.Context) ([]models.SpeciesStats, error)
}
