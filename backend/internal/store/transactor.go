package store

import (
	"context"
	"database/sql"
	"fmt"

	"supervideo-server/internal/domain"
)

// SQLiteTransactor implements domain.Transactor for SQLite.
// It begins a *sql.Tx and calls the provided TxFn with transaction-scoped
// copies of VideoStore, DetectionStore, and ClassificationStore.
type SQLiteTransactor struct {
	db                  *sql.DB
	videoStore          *VideoStore
	detectionStore      *DetectionStore
	classificationStore *ClassificationStore
}

// NewSQLiteTransactor constructs a transactor from existing store instances.
// The stores' WithTx methods are used to create tx-scoped copies at runtime.
func NewSQLiteTransactor(
	db *sql.DB,
	videos *VideoStore,
	detections *DetectionStore,
	classifications *ClassificationStore,
) *SQLiteTransactor {
	return &SQLiteTransactor{
		db:                  db,
		videoStore:          videos,
		detectionStore:      detections,
		classificationStore: classifications,
	}
}

// ExecTx begins a transaction, runs fn with tx-scoped repositories, then
// commits on success or rolls back on error. Panics are also caught and
// the transaction is rolled back before the panic is re-raised.
func (t *SQLiteTransactor) ExecTx(ctx context.Context, fn domain.TxFn) error {
	tx, err := t.db.BeginTx(ctx, nil)
	if err != nil {
		return fmt.Errorf("transactor.BeginTx: %w", err)
	}

	defer func() {
		if p := recover(); p != nil {
			_ = tx.Rollback()
			panic(p)
		}
	}()

	if err := fn(ctx,
		t.videoStore.WithTx(tx),
		t.detectionStore.WithTx(tx),
		t.classificationStore.WithTx(tx),
	); err != nil {
		if rbErr := tx.Rollback(); rbErr != nil {
			return fmt.Errorf("transactor.Rollback after error (%w): %w", err, rbErr)
		}
		return err
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("transactor.Commit: %w", err)
	}
	return nil
}
