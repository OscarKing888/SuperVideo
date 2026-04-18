package store

import (
	"context"
	"database/sql"
	"fmt"

	"supervideo-server/internal/models"
)

// ClientStore implements domain.ClientRepository backed by SQLite.
type ClientStore struct {
	db DBTX
}

// NewClientStore constructs a ClientStore.
func NewClientStore(db *sql.DB) *ClientStore {
	return &ClientStore{db: db}
}

// WithTx returns a copy of the store that operates within the given transaction.
func (s *ClientStore) WithTx(tx *sql.Tx) *ClientStore {
	return &ClientStore{db: tx}
}

// Create inserts a new client record.
func (s *ClientStore) Create(ctx context.Context, client *models.Client) (*models.Client, error) {
	_, err := s.db.ExecContext(ctx,
		`INSERT INTO clients (id, name, machine_id, api_key, created_at)
		 VALUES (?, ?, ?, ?, datetime('now'))`,
		client.ID, client.Name, nullString(client.MachineID), client.APIKey,
	)
	if err != nil {
		return nil, fmt.Errorf("create client %s: %w", client.Name, err)
	}
	return s.GetByID(ctx, client.ID)
}

// GetByID fetches a client by primary key.
func (s *ClientStore) GetByID(ctx context.Context, id string) (*models.Client, error) {
	return s.scanClient(ctx,
		`SELECT id, name, machine_id, api_key, last_seen, created_at
		 FROM clients WHERE id = ?`, id)
}

// GetByAPIKey looks up a client by its API key.
func (s *ClientStore) GetByAPIKey(ctx context.Context, apiKey string) (*models.Client, error) {
	return s.scanClient(ctx,
		`SELECT id, name, machine_id, api_key, last_seen, created_at
		 FROM clients WHERE api_key = ?`, apiKey)
}

// GetByMachineID looks up a client by its machine identifier.
func (s *ClientStore) GetByMachineID(ctx context.Context, machineID string) (*models.Client, error) {
	return s.scanClient(ctx,
		`SELECT id, name, machine_id, api_key, last_seen, created_at
		 FROM clients WHERE machine_id = ?`, machineID)
}

// List returns all registered clients.
func (s *ClientStore) List(ctx context.Context) ([]models.Client, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT id, name, machine_id, api_key, last_seen, created_at
		 FROM clients ORDER BY created_at DESC`)
	if err != nil {
		return nil, fmt.Errorf("list clients: %w", err)
	}
	defer rows.Close()

	var clients []models.Client
	for rows.Next() {
		c, err := scanClientRow(rows)
		if err != nil {
			return nil, err
		}
		clients = append(clients, *c)
	}
	return clients, rows.Err()
}

// UpdateLastSeen stamps last_seen = now for the given client.
func (s *ClientStore) UpdateLastSeen(ctx context.Context, id string) error {
	_, err := s.db.ExecContext(ctx,
		"UPDATE clients SET last_seen = datetime('now') WHERE id = ?", id)
	if err != nil {
		return fmt.Errorf("update last_seen for client %s: %w", id, err)
	}
	return nil
}

// scanClient executes a query expected to return exactly one client row.
func (s *ClientStore) scanClient(ctx context.Context, query string, args ...interface{}) (*models.Client, error) {
	var client models.Client
	var machineID, lastSeen sql.NullString
	var createdAt string

	err := s.db.QueryRowContext(ctx, query, args...).Scan(
		&client.ID, &client.Name, &machineID, &client.APIKey,
		&lastSeen, &createdAt,
	)
	if err != nil {
		return nil, fmt.Errorf("scan client: %w", err)
	}
	client.MachineID = scanNullString(machineID)
	client.LastSeen = parseNullTime(lastSeen)
	client.CreatedAt = parseTime(createdAt)
	return &client, nil
}

// scanClientRow scans a client from an active *sql.Rows cursor.
func scanClientRow(rows *sql.Rows) (*models.Client, error) {
	var client models.Client
	var machineID, lastSeen sql.NullString
	var createdAt string

	err := rows.Scan(
		&client.ID, &client.Name, &machineID, &client.APIKey,
		&lastSeen, &createdAt,
	)
	if err != nil {
		return nil, fmt.Errorf("scan client row: %w", err)
	}
	client.MachineID = scanNullString(machineID)
	client.LastSeen = parseNullTime(lastSeen)
	client.CreatedAt = parseTime(createdAt)
	return &client, nil
}
