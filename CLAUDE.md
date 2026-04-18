# SuperVideo - Distributed Bird Classification from Video

## Project Overview

SuperVideo is a **distributed bird classification system** that extracts frames from video files and uses AI models to identify bird species. The system consists of:

- **Client** (PyQt6/PySide6): Desktop GUI for scanning videos, running classification, and uploading results
- **Backend** (Go): Central data hub with REST API, user management, and aggregated database
- **Frame Extractor** (Python): Reusable module for extracting specific frames from video files (already implemented)

## Architecture

```
┌─────────────────────┐        ┌─────────────────────┐
│   Client Machine A  │        │   Client Machine B  │
│  ┌───────────────┐  │        │  ┌───────────────┐  │
│  │  PyQt6 GUI    │  │        │  │  PyQt6 GUI    │  │
│  │  + Bird AI    │  │        │  │  + Bird AI    │  │
│  │  + SQLite     │  │        │  │  + SQLite     │  │
│  └───────┬───────┘  │        │  └───────┬───────┘  │
└──────────┼──────────┘        └──────────┼──────────┘
           │         Upload Results       │
           └──────────┬───────────────────┘
                      ▼
           ┌─────────────────────┐
           │   Central Server    │
           │  ┌───────────────┐  │
           │  │  Go Backend   │  │
           │  │  + REST API   │  │
           │  │  + SQLite/DB  │  │
           │  │  + Web UI     │  │
           │  └───────────────┘  │
           └─────────────────────┘
```

## Directory Structure

```
SuperVideo/
├── CLAUDE.md                              # This file
├── task.md                                # Requirements specification
├── README.md                              # User-facing documentation
├── LICENSE                                # GNU AGPL v3
│
├── src/supervideo_frame_extractor/        # Phase 1 - Frame extraction (DONE)
│   ├── __init__.py
│   ├── __main__.py                        # CLI entry point
│   ├── cli.py                             # Argument parsing & orchestration
│   ├── models.py                          # Data models & constants
│   ├── config.py                          # INI config loader
│   ├── scanner.py                         # Video file discovery
│   ├── service.py                         # Extraction service
│   └── extractors/
│       ├── base.py                        # Abstract FrameExtractor interface
│       └── ffmpeg.py                      # FFmpeg implementation
│
├── src/supervideo_bird_classifier/        # Phase 2 - Bird classification module
│   ├── __init__.py
│   ├── device.py                          # GPU/CPU device detection
│   ├── detector.py                        # YOLO bird detection
│   ├── classifier.py                      # Species classification (OSEA)
│   ├── scorer.py                          # Quality/aesthetic scoring
│   ├── pipeline.py                        # Orchestrates detect→classify→score
│   └── models/                            # Pre-trained model weights
│
├── client/                                # Phase 3 - PyQt6 desktop client
│   ├── main.py                            # Application entry point
│   ├── app.py                             # QApplication setup
│   ├── ui/                                # UI components
│   │   ├── main_window.py
│   │   ├── settings_dialog.py
│   │   ├── progress_panel.py
│   │   └── results_panel.py
│   ├── workers/                           # Background processing threads
│   │   ├── scan_worker.py
│   │   ├── classify_worker.py
│   │   └── upload_worker.py
│   ├── database/                          # Local SQLite operations
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── migrations.py
│   └── api/                               # Central server API client
│       └── client.py
│
├── backend/                               # Phase 4 - Go central server
│   ├── main.go                            # Entry point with DI
│   ├── go.mod
│   ├── internal/
│   │   ├── config/                        # Environment-based configuration
│   │   ├── database/                      # SQLite init & migrations
│   │   ├── domain/                        # Interface contracts (Repository)
│   │   ├── models/                        # Data models & DTOs
│   │   ├── store/                         # Repository implementations
│   │   ├── service/                       # Business logic layer
│   │   ├── handlers/                      # HTTP handlers
│   │   └── router/                        # Chi HTTP router
│   ├── web/                               # Embedded static assets
│   └── data/                              # SQLite database files
│
├── tests/                                 # Python tests
│   ├── test_config.py
│   └── test_smoke.py
│
├── scripts/                               # Helper scripts
│   ├── extract_frames.bat
│   └── extract_frames.sh
│
├── video/                                 # Test data
│   └── test.cfg
│
├── pyproject.toml                         # Python project config
└── requirements.txt                       # Python dependencies
```

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frame Extraction | Python + FFmpeg | Already implemented |
| Bird Detection | YOLO11L-seg (ultralytics) | GPU-accelerated |
| Bird Classification | OSEA ResNet34 (11K classes) | GPU-accelerated |
| Quality Scoring | TOPIQ ResNet50 | GPU-accelerated |
| Client GUI | PySide6 (PyQt6) | Worker threads for responsiveness |
| Client DB | SQLite | Local result storage |
| Backend API | Go + Chi v5 | REST API |
| Backend DB | SQLite (modernc.org/sqlite) | Pure Go, no CGO |
| Backend Auth | Session cookies + bcrypt | |

## Design Principles

- **Repository Pattern**: Domain interfaces in `domain/`, implementations in `store/`
- **Service Layer**: Business logic separated from HTTP handlers
- **Strategy Pattern**: Pluggable extractors (FFmpeg), detectors, classifiers
- **Dependency Injection**: Constructor-based, wired in main entry points
- **Interface Segregation**: Small, focused interfaces per responsibility
- **Lazy Model Loading**: AI models loaded on first use, singleton-cached
- **Worker Threads**: Long-running tasks in QThread with Signal/Slot communication

## Reference Projects

- **E:\ABIGit** — Go backend patterns: Repository, Service, Chi router, SQLite with WAL, session auth, middleware
- **E:\SuperPickyOrig** — PyQt6 UI patterns, bird classification AI pipeline (YOLO + OSEA + TOPIQ), GPU device detection

## Key Commands

```bash
# Frame extraction (existing)
PYTHONPATH=src python -m supervideo_frame_extractor <video_or_dir>

# Run tests
PYTHONPATH=src python -m unittest discover -s tests -v

# Backend (planned)
cd backend && go run .

# Client (planned)
cd client && python main.py
```

## Database Schema (Planned)

### Local Client SQLite
- `videos`: video file metadata (path, hash, duration, frame_count)
- `frames`: extracted frame metadata (video_id, frame_number, path)
- `detections`: bird detections per frame (frame_id, bbox, confidence)
- `classifications`: species classification results (detection_id, species, confidence)
- `upload_queue`: pending uploads to central server

### Central Server SQLite
- `clients`: registered client machines
- `videos`: aggregated video records from all clients
- `detections`: aggregated detection results
- `classifications`: aggregated species classifications
- `users`: user accounts (admin, viewer roles)
- `sessions`: authentication sessions

## Critical Invariants

1. **Frame extraction** must handle FFmpeg failures gracefully per-video (already implemented)
2. **AI models** must detect GPU availability and fallback to CPU without crashes
3. **Local DB writes** must be atomic — use transactions for multi-table operations
4. **Upload to central** must be idempotent — use content hashes to prevent duplicates
5. **Client UI** must never freeze — all processing in worker threads
