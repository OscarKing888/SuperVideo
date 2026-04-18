package store

import (
	"context"
	"database/sql"
	"fmt"

	"supervideo-server/internal/models"
)

// DetectionStore implements domain.DetectionRepository backed by SQLite.
type DetectionStore struct {
	db DBTX
}

// NewDetectionStore constructs a DetectionStore.
func NewDetectionStore(db *sql.DB) *DetectionStore {
	return &DetectionStore{db: db}
}

// WithTx returns a copy of the store that operates within the given transaction.
func (s *DetectionStore) WithTx(tx *sql.Tx) *DetectionStore {
	return &DetectionStore{db: tx}
}

// CreateBatch inserts multiple detections in a single transaction scope.
func (s *DetectionStore) CreateBatch(ctx context.Context, detections []models.Detection) error {
	for _, d := range detections {
		_, err := s.db.ExecContext(ctx,
			`INSERT INTO detections (id, video_id, frame_number, bbox_x, bbox_y, bbox_w, bbox_h, confidence)
			 VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			d.ID, d.VideoID, d.FrameNumber,
			d.BBoxX, d.BBoxY, d.BBoxW, d.BBoxH, d.Confidence,
		)
		if err != nil {
			return fmt.Errorf("create detection %s: %w", d.ID, err)
		}
	}
	return nil
}

// ListByVideo returns all detections for a given video.
func (s *DetectionStore) ListByVideo(ctx context.Context, videoID string) ([]models.Detection, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, video_id, frame_number, bbox_x, bbox_y, bbox_w, bbox_h, confidence
		 FROM detections WHERE video_id = ? ORDER BY frame_number`, videoID)
	if err != nil {
		return nil, fmt.Errorf("list detections for video %s: %w", videoID, err)
	}
	defer rows.Close()

	var detections []models.Detection
	for rows.Next() {
		var d models.Detection
		err := rows.Scan(
			&d.ID, &d.VideoID, &d.FrameNumber,
			&d.BBoxX, &d.BBoxY, &d.BBoxW, &d.BBoxH, &d.Confidence,
		)
		if err != nil {
			return nil, fmt.Errorf("scan detection row: %w", err)
		}
		detections = append(detections, d)
	}
	return detections, rows.Err()
}
