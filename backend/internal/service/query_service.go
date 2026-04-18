package service

import (
	"context"
	"fmt"

	"supervideo-server/internal/models"
	"supervideo-server/internal/store"
)

// QueryService provides read-only queries for the dashboard and API.
type QueryService struct {
	videoStore          *store.VideoStore
	detectionStore      *store.DetectionStore
	classificationStore *store.ClassificationStore
	clientStore         *store.ClientStore
}

// NewQueryService constructs a QueryService.
func NewQueryService(
	videos *store.VideoStore,
	detections *store.DetectionStore,
	classifications *store.ClassificationStore,
	clients *store.ClientStore,
) *QueryService {
	return &QueryService{
		videoStore:          videos,
		detectionStore:      detections,
		classificationStore: classifications,
		clientStore:         clients,
	}
}

// GetOverview returns summary statistics for the admin dashboard.
func (s *QueryService) GetOverview(ctx context.Context) (*models.OverviewStats, error) {
	stats := &models.OverviewStats{}

	clients, err := s.clientStore.List(ctx)
	if err != nil {
		return nil, fmt.Errorf("count clients: %w", err)
	}
	stats.TotalClients = len(clients)

	videoCount, err := s.videoStore.Count(ctx)
	if err != nil {
		return nil, fmt.Errorf("count videos: %w", err)
	}
	stats.TotalVideos = videoCount

	speciesStats, err := s.classificationStore.SpeciesStats(ctx)
	if err != nil {
		return nil, fmt.Errorf("species stats: %w", err)
	}
	stats.UniqueSpecies = len(speciesStats)
	for _, sp := range speciesStats {
		stats.TotalClassifications += sp.Count
	}

	// Count detections across all videos. We do a simple aggregate.
	var detCount int
	videos, err := s.videoStore.List(ctx, 100000, 0)
	if err == nil {
		for _, v := range videos {
			dets, err := s.detectionStore.ListByVideo(ctx, v.ID)
			if err == nil {
				detCount += len(dets)
			}
		}
	}
	stats.TotalDetections = detCount

	return stats, nil
}

// ListVideos returns a paginated list of videos.
func (s *QueryService) ListVideos(ctx context.Context, limit, offset int) ([]models.Video, error) {
	if limit <= 0 {
		limit = 50
	}
	if offset < 0 {
		offset = 0
	}
	return s.videoStore.List(ctx, limit, offset)
}

// GetVideo returns a single video with its detections and classifications.
func (s *QueryService) GetVideo(ctx context.Context, videoID string) (map[string]interface{}, error) {
	video, err := s.videoStore.GetByID(ctx, videoID)
	if err != nil {
		return nil, fmt.Errorf("get video: %w", err)
	}

	detections, err := s.detectionStore.ListByVideo(ctx, videoID)
	if err != nil {
		return nil, fmt.Errorf("list detections: %w", err)
	}

	// Build detection list with their classifications
	type detectionWithClassifications struct {
		models.Detection
		Classifications []models.Classification `json:"classifications"`
	}

	var detWithClass []detectionWithClassifications
	for _, d := range detections {
		cls, err := s.classificationStore.ListByDetection(ctx, d.ID)
		if err != nil {
			return nil, fmt.Errorf("list classifications for detection %s: %w", d.ID, err)
		}
		if cls == nil {
			cls = []models.Classification{}
		}
		detWithClass = append(detWithClass, detectionWithClassifications{
			Detection:       d,
			Classifications: cls,
		})
	}

	if detWithClass == nil {
		detWithClass = []detectionWithClassifications{}
	}

	return map[string]interface{}{
		"video":      video,
		"detections": detWithClass,
	}, nil
}

// GetSpeciesStats returns aggregated species statistics.
func (s *QueryService) GetSpeciesStats(ctx context.Context) ([]models.SpeciesStats, error) {
	stats, err := s.classificationStore.SpeciesStats(ctx)
	if err != nil {
		return nil, err
	}
	if stats == nil {
		stats = []models.SpeciesStats{}
	}
	return stats, nil
}

// ListClients returns all registered client machines.
func (s *QueryService) ListClients(ctx context.Context) ([]models.Client, error) {
	clients, err := s.clientStore.List(ctx)
	if err != nil {
		return nil, err
	}
	if clients == nil {
		clients = []models.Client{}
	}
	return clients, nil
}
