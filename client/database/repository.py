"""Repository layer for local SQLite database."""

import sqlite3
import hashlib
import os
from typing import List, Optional, Tuple

from client.database.models import (
    Video, Frame, Detection, Classification, UploadQueueItem,
)


class VideoRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, video: Video) -> int:
        cur = self._conn.execute(
            "INSERT INTO videos (file_path, file_name, file_hash, duration_ms, "
            "frame_count, file_size, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (video.file_path, video.file_name, video.file_hash,
             video.duration_ms, video.frame_count, video.file_size, video.status),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_by_id(self, video_id: int) -> Optional[Video]:
        row = self._conn.execute(
            "SELECT id, file_path, file_name, file_hash, duration_ms, frame_count, "
            "file_size, status, created_at, updated_at FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()
        return self._row_to_video(row) if row else None

    def get_by_path(self, path: str) -> Optional[Video]:
        row = self._conn.execute(
            "SELECT id, file_path, file_name, file_hash, duration_ms, frame_count, "
            "file_size, status, created_at, updated_at FROM videos WHERE file_path = ?",
            (path,),
        ).fetchone()
        return self._row_to_video(row) if row else None

    def list_all(self) -> List[Video]:
        rows = self._conn.execute(
            "SELECT id, file_path, file_name, file_hash, duration_ms, frame_count, "
            "file_size, status, created_at, updated_at FROM videos ORDER BY id"
        ).fetchall()
        return [self._row_to_video(r) for r in rows]

    def update_status(self, video_id: int, status: str):
        self._conn.execute(
            "UPDATE videos SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, video_id),
        )
        self._conn.commit()

    def update_hash(self, video_id: int, file_hash: str):
        self._conn.execute(
            "UPDATE videos SET file_hash = ?, updated_at = datetime('now') WHERE id = ?",
            (file_hash, video_id),
        )
        self._conn.commit()

    def count_by_status(self) -> dict:
        rows = self._conn.execute(
            "SELECT status, COUNT(*) FROM videos GROUP BY status"
        ).fetchall()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _row_to_video(row) -> Video:
        return Video(
            id=row[0], file_path=row[1], file_name=row[2], file_hash=row[3],
            duration_ms=row[4], frame_count=row[5], file_size=row[6],
            status=row[7], created_at=row[8], updated_at=row[9],
        )


class FrameRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, frame: Frame) -> int:
        cur = self._conn.execute(
            "INSERT OR IGNORE INTO frames (video_id, frame_number, file_path, width, height) "
            "VALUES (?, ?, ?, ?, ?)",
            (frame.video_id, frame.frame_number, frame.file_path, frame.width, frame.height),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_by_video(self, video_id: int) -> List[Frame]:
        rows = self._conn.execute(
            "SELECT id, video_id, frame_number, file_path, width, height, created_at "
            "FROM frames WHERE video_id = ? ORDER BY frame_number",
            (video_id,),
        ).fetchall()
        return [Frame(id=r[0], video_id=r[1], frame_number=r[2], file_path=r[3],
                       width=r[4], height=r[5], created_at=r[6]) for r in rows]


class DetectionRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, det: Detection) -> int:
        cur = self._conn.execute(
            "INSERT INTO detections (frame_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (det.frame_id, det.bbox_x, det.bbox_y, det.bbox_w, det.bbox_h, det.confidence),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_by_frame(self, frame_id: int) -> List[Detection]:
        rows = self._conn.execute(
            "SELECT id, frame_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, created_at "
            "FROM detections WHERE frame_id = ? ORDER BY confidence DESC",
            (frame_id,),
        ).fetchall()
        return [Detection(id=r[0], frame_id=r[1], bbox_x=r[2], bbox_y=r[3],
                          bbox_w=r[4], bbox_h=r[5], confidence=r[6], created_at=r[7])
                for r in rows]


class ClassificationRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def create(self, cls: Classification) -> int:
        cur = self._conn.execute(
            "INSERT INTO classifications (detection_id, species_name, species_name_zh, "
            "scientific_name, confidence, rank) VALUES (?, ?, ?, ?, ?, ?)",
            (cls.detection_id, cls.species_name, cls.species_name_zh,
             cls.scientific_name, cls.confidence, cls.rank),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_by_detection(self, detection_id: int) -> List[Classification]:
        rows = self._conn.execute(
            "SELECT id, detection_id, species_name, species_name_zh, scientific_name, "
            "confidence, rank, created_at FROM classifications "
            "WHERE detection_id = ? ORDER BY rank",
            (detection_id,),
        ).fetchall()
        return [Classification(id=r[0], detection_id=r[1], species_name=r[2],
                               species_name_zh=r[3], scientific_name=r[4],
                               confidence=r[5], rank=r[6], created_at=r[7])
                for r in rows]

    def species_summary(self) -> List[Tuple[str, str, int, float]]:
        rows = self._conn.execute(
            "SELECT species_name, species_name_zh, COUNT(*) as cnt, "
            "MAX(confidence) as max_conf FROM classifications "
            "GROUP BY species_name ORDER BY cnt DESC"
        ).fetchall()
        return [(r[0], r[1], r[2], r[3]) for r in rows]


class UploadQueueRepository:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def enqueue(self, video_id: int, server_url: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO upload_queue (video_id, server_url) VALUES (?, ?)",
            (video_id, server_url),
        )
        self._conn.commit()
        return cur.lastrowid

    def list_pending(self) -> List[UploadQueueItem]:
        rows = self._conn.execute(
            "SELECT id, video_id, status, server_url, error_msg, created_at, uploaded_at "
            "FROM upload_queue WHERE status = 'pending' ORDER BY id"
        ).fetchall()
        return [UploadQueueItem(id=r[0], video_id=r[1], status=r[2], server_url=r[3],
                                error_msg=r[4], created_at=r[5], uploaded_at=r[6])
                for r in rows]

    def update_status(self, item_id: int, status: str, error_msg: Optional[str] = None):
        if status == "uploaded":
            self._conn.execute(
                "UPDATE upload_queue SET status = ?, uploaded_at = datetime('now') WHERE id = ?",
                (status, item_id),
            )
        else:
            self._conn.execute(
                "UPDATE upload_queue SET status = ?, error_msg = ? WHERE id = ?",
                (status, error_msg, item_id),
            )
        self._conn.commit()


def compute_file_hash(file_path: str) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
