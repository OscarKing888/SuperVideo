package service

import (
	"context"
	"fmt"

	"github.com/google/uuid"

	"supervideo-server/internal/domain"
	"supervideo-server/internal/models"
	"supervideo-server/internal/store"
)

// UploadService handles processing of batch uploads from client machines.
type UploadService struct {
	clientStore *store.ClientStore
	transactor  domain.Transactor
}

// NewUploadService constructs an UploadService.
func NewUploadService(clients *store.ClientStore, transactor domain.Transactor) *UploadService {
	return &UploadService{
		clientStore: clients,
		transactor:  transactor,
	}
}

// ProcessUpload validates the client, deduplicates by file hash, and
// transactionally inserts videos, detections, and classifications.
func (s *UploadService) ProcessUpload(ctx context.Context, clientID string, req models.UploadRequest) (*models.UploadResponse, error) {
	// Validate the client exists
	_, err := s.clientStore.GetByID(ctx, clientID)
	if err != nil {
		return nil, fmt.Errorf("invalid client: %w", err)
	}

	// Update the client's last-seen timestamp
	_ = s.clientStore.UpdateLastSeen(ctx, clientID)

	resp := &models.UploadResponse{}

	err = s.transactor.ExecTx(ctx, func(
		ctx context.Context,
		videoRepo domain.VideoRepository,
		detectionRepo domain.DetectionRepository,
		classificationRepo domain.ClassificationRepository,
	) error {
		// Map from request video index to created video ID
		videoIDMap := make(map[int]string)

		// Process videos — dedup by client_id + file_hash
		for i, uv := range req.Videos {
			if uv.FileHash != "" {
				existing, err := videoRepo.GetByClientAndHash(ctx, clientID, uv.FileHash)
				if err == nil && existing != nil {
					// Already uploaded — skip but remember its ID for detections
					videoIDMap[i] = existing.ID
					resp.VideosSkipped++
					continue
				}
			}

			videoID := uuid.New().String()
			video := &models.Video{
				ID:         videoID,
				ClientID:   clientID,
				FileName:   uv.FileName,
				FileHash:   uv.FileHash,
				DurationMs: uv.DurationMs,
				FrameCount: uv.FrameCount,
			}
			created, err := videoRepo.Create(ctx, video)
			if err != nil {
				return fmt.Errorf("create video %s: %w", uv.FileName, err)
			}
			videoIDMap[i] = created.ID
			resp.VideoIDs = append(resp.VideoIDs, created.ID)
			resp.VideosCreated++
		}

		// Map from request detection index to created detection ID
		detectionIDMap := make(map[int]string)

		// Process detections
		var detections []models.Detection
		for i, ud := range req.Detections {
			videoID, ok := videoIDMap[ud.VideoIndex]
			if !ok {
				return fmt.Errorf("detection references invalid video_index %d", ud.VideoIndex)
			}

			detID := uuid.New().String()
			detectionIDMap[i] = detID
			detections = append(detections, models.Detection{
				ID:          detID,
				VideoID:     videoID,
				FrameNumber: ud.FrameNumber,
				BBoxX:       ud.BBoxX,
				BBoxY:       ud.BBoxY,
				BBoxW:       ud.BBoxW,
				BBoxH:       ud.BBoxH,
				Confidence:  ud.Confidence,
			})
		}
		if len(detections) > 0 {
			if err := detectionRepo.CreateBatch(ctx, detections); err != nil {
				return fmt.Errorf("create detections: %w", err)
			}
			resp.DetectionsCreated = len(detections)
		}

		// Process classifications
		var classifications []models.Classification
		for _, uc := range req.Classifications {
			detID, ok := detectionIDMap[uc.DetectionIndex]
			if !ok {
				return fmt.Errorf("classification references invalid detection_index %d", uc.DetectionIndex)
			}

			rank := uc.Rank
			if rank == 0 {
				rank = 1
			}

			classifications = append(classifications, models.Classification{
				ID:             uuid.New().String(),
				DetectionID:    detID,
				SpeciesName:    uc.SpeciesName,
				SpeciesNameZh:  uc.SpeciesNameZh,
				ScientificName: uc.ScientificName,
				Confidence:     uc.Confidence,
				Rank:           rank,
			})
		}
		if len(classifications) > 0 {
			if err := classificationRepo.CreateBatch(ctx, classifications); err != nil {
				return fmt.Errorf("create classifications: %w", err)
			}
			resp.ClassificationsCreated = len(classifications)
		}

		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("process upload: %w", err)
	}

	if resp.VideoIDs == nil {
		resp.VideoIDs = []string{}
	}

	return resp, nil
}
