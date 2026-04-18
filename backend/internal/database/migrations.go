package database

import (
	"database/sql"
	"fmt"
	"log"

	"supervideo-server/internal/security"
)

// Schema DDL — each const is an idempotent CREATE TABLE IF NOT EXISTS statement.
const (
	createClients = `
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    machine_id TEXT UNIQUE,
    api_key TEXT NOT NULL UNIQUE,
    last_seen TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);`

	createUsers = `
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_login_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);`

	createSessions = `
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);`

	createVideos = `
CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    client_id TEXT NOT NULL REFERENCES clients(id),
    file_name TEXT NOT NULL,
    file_hash TEXT,
    duration_ms INTEGER,
    frame_count INTEGER,
    uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(client_id, file_hash)
);
CREATE INDEX IF NOT EXISTS idx_videos_client ON videos(client_id);`

	createDetections = `
CREATE TABLE IF NOT EXISTS detections (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    frame_number INTEGER NOT NULL,
    bbox_x REAL,
    bbox_y REAL,
    bbox_w REAL,
    bbox_h REAL,
    confidence REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_detections_video ON detections(video_id);`

	createClassifications = `
CREATE TABLE IF NOT EXISTS classifications (
    id TEXT PRIMARY KEY,
    detection_id TEXT NOT NULL REFERENCES detections(id),
    species_name TEXT NOT NULL,
    species_name_zh TEXT,
    scientific_name TEXT,
    confidence REAL NOT NULL,
    rank INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_classifications_detection ON classifications(detection_id);
CREATE INDEX IF NOT EXISTS idx_classifications_species ON classifications(species_name);`
)

// RunMigrations executes all DDL statements in order.
// All statements are idempotent (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
func RunMigrations(db *sql.DB) error {
	stmts := []string{
		createClients,
		createUsers,
		createSessions,
		createVideos,
		createDetections,
		createClassifications,
	}
	for _, stmt := range stmts {
		if _, err := db.Exec(stmt); err != nil {
			return fmt.Errorf("migration failed: %w", err)
		}
	}
	return nil
}

// SeedDefaults creates the initial admin user (admin/admin123, role=admin)
// if no users exist yet. Idempotent: on subsequent boots this is a no-op.
func SeedDefaults(db *sql.DB) error {
	var count int
	if err := db.QueryRow("SELECT COUNT(1) FROM users").Scan(&count); err != nil {
		return fmt.Errorf("count users: %w", err)
	}
	if count > 0 {
		return nil
	}

	hash, err := security.HashPassword("admin123")
	if err != nil {
		return fmt.Errorf("hash bootstrap password: %w", err)
	}

	if _, err := db.Exec(
		`INSERT INTO users (username, password_hash, role, updated_at)
		 VALUES (?, ?, 'admin', datetime('now'))`,
		"admin", hash,
	); err != nil {
		return fmt.Errorf("seed bootstrap admin: %w", err)
	}

	log.Println("============================================================")
	log.Println(" SuperVideo bootstrap — admin account created.")
	log.Println("   username : admin")
	log.Println("   password : admin123")
	log.Println(" Change this password after first login!")
	log.Println("============================================================")
	return nil
}
