"""Local SQLite database models and migrations for the client."""

import sqlite3
import os
from typing import Optional

_MIGRATIONS = """
CREATE TABLE IF NOT EXISTS videos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path   TEXT NOT NULL UNIQUE,
    file_name   TEXT NOT NULL,
    file_hash   TEXT,
    duration_ms INTEGER,
    frame_count INTEGER,
    file_size   INTEGER,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS frames (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id     INTEGER NOT NULL REFERENCES videos(id),
    frame_number INTEGER NOT NULL,
    file_path    TEXT NOT NULL,
    width        INTEGER,
    height       INTEGER,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(video_id, frame_number)
);
CREATE INDEX IF NOT EXISTS idx_frames_video ON frames(video_id);

CREATE TABLE IF NOT EXISTS detections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    frame_id    INTEGER NOT NULL REFERENCES frames(id),
    bbox_x      REAL,
    bbox_y      REAL,
    bbox_w      REAL,
    bbox_h      REAL,
    confidence  REAL NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_detections_frame ON detections(frame_id);

CREATE TABLE IF NOT EXISTS classifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id    INTEGER NOT NULL REFERENCES detections(id),
    species_name    TEXT NOT NULL,
    species_name_zh TEXT,
    scientific_name TEXT,
    confidence      REAL NOT NULL,
    rank            INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_classifications_detection ON classifications(detection_id);
CREATE INDEX IF NOT EXISTS idx_classifications_species ON classifications(species_name);

CREATE TABLE IF NOT EXISTS upload_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id    INTEGER NOT NULL REFERENCES videos(id),
    status      TEXT NOT NULL DEFAULT 'pending',
    server_url  TEXT,
    error_msg   TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    uploaded_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_upload_video ON upload_queue(video_id);
"""


def init_database(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(_MIGRATIONS)
    return conn
