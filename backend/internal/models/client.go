package models

import "time"

// Client represents a registered client machine that uploads classification results.
type Client struct {
	ID        string     `json:"id"`
	Name      string     `json:"name"`
	MachineID string     `json:"machine_id,omitempty"`
	APIKey    string     `json:"api_key,omitempty"`
	LastSeen  *time.Time `json:"last_seen,omitempty"`
	CreatedAt time.Time  `json:"created_at"`
}
