"""Worker thread for uploading results to central server."""

import json
from typing import Optional

from PySide6.QtCore import QThread, Signal

from client.database.repository import (
    VideoRepository, FrameRepository, DetectionRepository,
    ClassificationRepository, UploadQueueRepository,
)
from client.api.client import SuperVideoAPIClient


class UploadWorker(QThread):
    progress = Signal(int, int)  # current, total
    log = Signal(str)
    finished = Signal(int)  # uploaded count
    error = Signal(str)

    def __init__(
        self,
        video_repo: VideoRepository,
        frame_repo: FrameRepository,
        detection_repo: DetectionRepository,
        classification_repo: ClassificationRepository,
        upload_repo: UploadQueueRepository,
        api_client: SuperVideoAPIClient,
        parent=None,
    ):
        super().__init__(parent)
        self._video_repo = video_repo
        self._frame_repo = frame_repo
        self._detection_repo = detection_repo
        self._classification_repo = classification_repo
        self._upload_repo = upload_repo
        self._api_client = api_client
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            pending = self._upload_repo.list_pending()
            total = len(pending)
            uploaded = 0

            for idx, item in enumerate(pending):
                if self._cancelled:
                    break

                self.progress.emit(idx, total)

                video = self._video_repo.get_by_id(item.video_id)
                if not video or video.status != "completed":
                    self._upload_repo.update_status(item.id, "error", "Video not completed")
                    continue

                try:
                    frames = self._frame_repo.list_by_video(video.id)
                    payload = self._build_payload(video, frames)

                    self.log.emit(f"Uploading: {video.file_name}")
                    self._upload_repo.update_status(item.id, "uploading")

                    self._api_client.upload(payload)

                    self._upload_repo.update_status(item.id, "uploaded")
                    uploaded += 1
                    self.log.emit(f"Uploaded: {video.file_name}")

                except Exception as e:
                    self._upload_repo.update_status(item.id, "error", str(e))
                    self.log.emit(f"Upload failed for {video.file_name}: {e}")

            self.progress.emit(total, total)
            self.finished.emit(uploaded)

        except Exception as e:
            self.error.emit(str(e))

    def _build_payload(self, video, frames) -> dict:
        frame_data = []
        for frame in frames:
            detections = self._detection_repo.list_by_frame(frame.id)
            det_data = []
            for det in detections:
                classifications = self._classification_repo.list_by_detection(det.id)
                cls_data = [
                    {
                        "species_name": c.species_name,
                        "species_name_zh": c.species_name_zh,
                        "scientific_name": c.scientific_name,
                        "confidence": c.confidence,
                        "rank": c.rank,
                    }
                    for c in classifications
                ]
                det_data.append({
                    "bbox_x": det.bbox_x,
                    "bbox_y": det.bbox_y,
                    "bbox_w": det.bbox_w,
                    "bbox_h": det.bbox_h,
                    "confidence": det.confidence,
                    "classifications": cls_data,
                })
            frame_data.append({
                "frame_number": frame.frame_number,
                "detections": det_data,
            })

        return {
            "video": {
                "file_name": video.file_name,
                "file_hash": video.file_hash,
                "duration_ms": video.duration_ms,
                "frame_count": video.frame_count,
            },
            "frames": frame_data,
        }
