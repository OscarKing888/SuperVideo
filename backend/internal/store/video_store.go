package store

import (
	"context"
	"database/sql"
	"fmt"

	"supervideo-server/internal/models"
)

// VideoStore implements domain.VideoRepository backed by SQLite.
type VideoStore struct {
	db DBTX
}

// NewVideoStore constructs a VideoStore.
func NewVideoStore(db *sql.DB) *VideoStore {
	return &VideoStore{db: db}
}

// WithTx returns a copy of the store that operates within the given transaction.
func (s *VideoStore) WithTx(tx *sql.Tx) *VideoStore {
	return &VideoStore{db: tx}
}

// Create inserts a new video record.
func (s *VideoStore) Create(ctx context.Context, video *models.Video) (*models.Video, error) {
	_, err := s.db.ExecContext(ctx,
		`INSERT INTO videos (id, client_id, file_name, file_hash, duration_ms, frame_count, uploaded_at)
		 VALUES (?, ?, ?, ?, ?, ?, datetime('now'))`,
		video.ID, video.ClientID, video.FileName,
		nullString(video.FileHash), nullInt(video.DurationMs), nullInt(video.FrameCount),
	)
	if err != nil {
		return nil, fmt.Errorf("create video %s: %w", video.FileName, err)
	}
	return s.GetByID(ctx, video.ID)
}

// GetByID fetches a video by primary key.
func (s *VideoStore) GetByID(ctx context.Context, id string) (*models.Video, error) {
	return s.scanVideo(ctx,
		`SELECT id, client_id, file_name, file_hash, duration_ms, frame_count, uploaded_at
		 FROM videos WHERE id = ?`, id)
}

// GetByClientAndHash looks up a video by client_id + file_hash for dedup.
func (s *VideoStore) GetByClientAndHash(ctx context.Context, clientID, fileHash string) (*models.Video, error) {
	return s.scanVideo(ctx,
		`SELECT id, client_id, file_name, file_hash, duration_ms, frame_count, uploaded_at
		 FROM videos WHERE client_id = ? AND file_hash = ?`, clientID, fileHash)
}

// List returns videos with pagination.
func (s *VideoStore) List(ctx context.Context, limit, offset int) ([]models.Video, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, client_id, file_name, file_hash, duration_ms, frame_count, uploaded_at
		 FROM videos ORDER BY uploaded_at DESC LIMIT ? OFFSET ?`, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("list videos: %w", err)
	}
	defer rows.Close()
	return s.scanVideoRows(rows)
}

// ListByClient returns all videos for a specific client.
func (s *VideoStore) ListByClient(ctx context.Context, clientID string) ([]models.Video, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, client_id, file_name, file_hash, duration_ms, frame_count, uploaded_at
		 FROM videos WHERE client_id = ? ORDER BY uploaded_at DESC`, clientID)
	if err != nil {
		return nil, fmt.Errorf("list videos by client %s: %w", clientID, err)
	}
	defer rows.Close()
	return s.scanVideoRows(rows)
}

// Count returns the total number of videos.
func (s *VideoStore) Count(ctx context.Context) (int, error) {
	var count int
	err := s.db.QueryRowContext(ctx, "SELECT COUNT(1) FROM videos").Scan(&count)
	if err != nil {
		return 0, fmt.Errorf("count videos: %w", err)
	}
	return count, nil
}

// scanVideo executes a query expected to return exactly one video row.
func (s *VideoStore) scanVideo(ctx context.Context, query string, args ...interface{}) (*models.Video, error) {
	var v models.Video
	var fileHash sql.NullString
	var durationMs, frameCount sql.NullInt64
	var uploadedAt string

	err := s.db.QueryRowContext(ctx, query, args...).Scan(
		&v.ID, &v.ClientID, &v.FileName, &fileHash,
		&durationMs, &frameCount, &uploadedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("scan video: %w", err)
	}
	v.FileHash = scanNullString(fileHash)
	v.DurationMs = scanNullInt(durationMs)
	v.FrameCount = scanNullInt(frameCount)
	v.UploadedAt = parseTime(uploadedAt)
	return &v, nil
}

// scanVideoRows scans multiple video rows from an active cursor.
func (s *VideoStore) scanVideoRows(rows *sql.Rows) ([]models.Video, error) {
	var videos []models.Video
	for rows.Next() {
		var v models.Video
		var fileHash sql.NullString
		var durationMs, frameCount sql.NullInt64
		var uploadedAt string

		err := rows.Scan(
			&v.ID, &v.ClientID, &v.FileName, &fileHash,
			&durationMs, &frameCount, &uploadedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("scan video row: %w", err)
		}
		v.FileHash = scanNullString(fileHash)
		v.DurationMs = scanNullInt(durationMs)
		v.FrameCount = scanNullInt(frameCount)
		v.UploadedAt = parseTime(uploadedAt)
		videos = append(videos, v)
	}
	return videos, rows.Err()
}
