package domain

import "context"

// TxFn is a function that executes within a database transaction.
// It receives transaction-scoped repository instances; all writes through
// these repos are part of the same atomic transaction.
type TxFn func(
	ctx context.Context,
	videos VideoRepository,
	detections DetectionRepository,
	classifications ClassificationRepository,
) error

// Transactor executes a TxFn atomically inside a database transaction.
// Implementations commit on success and roll back on any error or panic.
type Transactor interface {
	ExecTx(ctx context.Context, fn TxFn) error
}
