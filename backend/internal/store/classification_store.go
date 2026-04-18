package store

import (
	"context"
	"database/sql"
	"fmt"

	"supervideo-server/internal/models"
)

// ClassificationStore implements domain.ClassificationRepository backed by SQLite.
type ClassificationStore struct {
	db DBTX
}

// NewClassificationStore constructs a ClassificationStore.
func NewClassificationStore(db *sql.DB) *ClassificationStore {
	return &ClassificationStore{db: db}
}

// WithTx returns a copy of the store that operates within the given transaction.
func (s *ClassificationStore) WithTx(tx *sql.Tx) *ClassificationStore {
	return &ClassificationStore{db: tx}
}

// CreateBatch inserts multiple classifications in a single transaction scope.
func (s *ClassificationStore) CreateBatch(ctx context.Context, classifications []models.Classification) error {
	for _, c := range classifications {
		_, err := s.db.ExecContext(ctx,
			`INSERT INTO classifications (id, detection_id, species_name, species_name_zh, scientific_name, confidence, rank)
			 VALUES (?, ?, ?, ?, ?, ?, ?)`,
			c.ID, c.DetectionID, c.SpeciesName,
			nullString(c.SpeciesNameZh), nullString(c.ScientificName),
			c.Confidence, c.Rank,
		)
		if err != nil {
			return fmt.Errorf("create classification %s: %w", c.ID, err)
		}
	}
	return nil
}

// ListByDetection returns all classifications for a given detection.
func (s *ClassificationStore) ListByDetection(ctx context.Context, detectionID string) ([]models.Classification, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, detection_id, species_name, species_name_zh, scientific_name, confidence, rank
		 FROM classifications WHERE detection_id = ? ORDER BY rank`, detectionID)
	if err != nil {
		return nil, fmt.Errorf("list classifications for detection %s: %w", detectionID, err)
	}
	defer rows.Close()

	var classifications []models.Classification
	for rows.Next() {
		var c models.Classification
		var speciesNameZh, scientificName sql.NullString
		err := rows.Scan(
			&c.ID, &c.DetectionID, &c.SpeciesName,
			&speciesNameZh, &scientificName,
			&c.Confidence, &c.Rank,
		)
		if err != nil {
			return nil, fmt.Errorf("scan classification row: %w", err)
		}
		c.SpeciesNameZh = scanNullString(speciesNameZh)
		c.ScientificName = scanNullString(scientificName)
		classifications = append(classifications, c)
	}
	return classifications, rows.Err()
}

// SpeciesStats returns aggregated statistics per species across all classifications.
func (s *ClassificationStore) SpeciesStats(ctx context.Context) ([]models.SpeciesStats, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT species_name,
		        COALESCE(species_name_zh, ''),
		        COALESCE(scientific_name, ''),
		        COUNT(*) as count,
		        AVG(confidence) as avg_confidence
		 FROM classifications
		 WHERE rank = 1
		 GROUP BY species_name
		 ORDER BY count DESC`)
	if err != nil {
		return nil, fmt.Errorf("species stats: %w", err)
	}
	defer rows.Close()

	var stats []models.SpeciesStats
	for rows.Next() {
		var s models.SpeciesStats
		err := rows.Scan(&s.SpeciesName, &s.SpeciesNameZh, &s.ScientificName,
			&s.Count, &s.AvgConfidence)
		if err != nil {
			return nil, fmt.Errorf("scan species stats row: %w", err)
		}
		stats = append(stats, s)
	}
	return stats, rows.Err()
}
