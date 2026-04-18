"""Data models for the client database."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Video:
    id: Optional[int] = None
    file_path: str = ""
    file_name: str = ""
    file_hash: Optional[str] = None
    duration_ms: Optional[int] = None
    frame_count: Optional[int] = None
    file_size: Optional[int] = None
    status: str = "pending"
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Frame:
    id: Optional[int] = None
    video_id: int = 0
    frame_number: int = 0
    file_path: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: Optional[str] = None


@dataclass
class Detection:
    id: Optional[int] = None
    frame_id: int = 0
    bbox_x: float = 0.0
    bbox_y: float = 0.0
    bbox_w: float = 0.0
    bbox_h: float = 0.0
    confidence: float = 0.0
    created_at: Optional[str] = None


@dataclass
class Classification:
    id: Optional[int] = None
    detection_id: int = 0
    species_name: str = ""
    species_name_zh: Optional[str] = None
    scientific_name: Optional[str] = None
    confidence: float = 0.0
    rank: int = 1
    created_at: Optional[str] = None


@dataclass
class UploadQueueItem:
    id: Optional[int] = None
    video_id: int = 0
    status: str = "pending"
    server_url: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: Optional[str] = None
    uploaded_at: Optional[str] = None
