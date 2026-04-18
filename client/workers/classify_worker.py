"""Worker thread for bird classification pipeline."""

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QThread, Signal

# Ensure src/ is on the path for the classifier and frame extractor modules
_src_dir = str(Path(__file__).parent.parent.parent / "src")
if _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

from client.database.models import Video, Frame, Detection, Classification
from client.database.repository import (
    VideoRepository, FrameRepository, DetectionRepository,
    ClassificationRepository, compute_file_hash,
)


class ClassifyWorker(QThread):
    progress = Signal(int, int)  # current_video, total_videos
    stage = Signal(str)  # current stage description
    video_done = Signal(int, str)  # video_id, summary
    log = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(
        self,
        video_repo: VideoRepository,
        frame_repo: FrameRepository,
        detection_repo: DetectionRepository,
        classification_repo: ClassificationRepository,
        frames_to_extract: str = "5,10,30",
        ffmpeg_binary: str = "ffmpeg",
        yolo_model_path: Optional[str] = None,
        osea_model_path: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._video_repo = video_repo
        self._frame_repo = frame_repo
        self._detection_repo = detection_repo
        self._classification_repo = classification_repo
        self._frames_str = frames_to_extract
        self._ffmpeg = ffmpeg_binary
        self._yolo_path = yolo_model_path
        self._osea_path = osea_model_path
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            from supervideo_frame_extractor.models import CliSettings, ResizeOptions
            from supervideo_frame_extractor.service import FrameExtractionService
            from supervideo_frame_extractor.extractors.ffmpeg import FfmpegFrameExtractor
            from supervideo_frame_extractor.config import IniSiblingConfigLoader
            from supervideo_bird_classifier.pipeline import ClassificationPipeline

            frame_numbers = [int(x.strip()) for x in self._frames_str.split(",")]

            settings = CliSettings(
                source=Path("."),
                frame_numbers=tuple(frame_numbers),
                resize=ResizeOptions(),
                video_extensions=frozenset({".mp4"}),
                scan_all_common=True,
                recursive=True,
                ffmpeg_binary=self._ffmpeg,
                output_root=None,
            )

            extractor = FfmpegFrameExtractor(settings.ffmpeg_binary)
            config_loader = IniSiblingConfigLoader()

            pipeline = ClassificationPipeline(
                yolo_model_path=self._yolo_path,
                osea_model_path=self._osea_path,
            )

            videos = [v for v in self._video_repo.list_all() if v.status == "pending"]
            total = len(videos)

            for idx, video in enumerate(videos):
                if self._cancelled:
                    break

                self.progress.emit(idx, total)
                self.stage.emit(f"Processing: {video.file_name}")
                self._video_repo.update_status(video.id, "processing")

                try:
                    file_hash = compute_file_hash(video.file_path)
                    self._video_repo.update_hash(video.id, file_hash)

                    self.log.emit(f"Extracting frames from {video.file_name}...")
                    self.stage.emit(f"{video.file_name} - Extracting frames")

                    from supervideo_frame_extractor.service import ExtractionRequestBuilder
                    from supervideo_frame_extractor.models import ExtractionRequest

                    video_path = Path(video.file_path)
                    output_dir = video_path.parent / f"{video_path.stem}_frames"
                    output_dir.mkdir(parents=True, exist_ok=True)

                    request = ExtractionRequest(
                        video_path=video_path,
                        output_dir=output_dir,
                        frame_numbers=tuple(frame_numbers),
                        resize=ResizeOptions(),
                    )
                    result = extractor.extract(request)

                    extracted_frames = []
                    for ef in result.frames:
                        frame = Frame(
                            video_id=video.id,
                            frame_number=ef.frame_number,
                            file_path=str(ef.output_path),
                        )
                        frame_id = self._frame_repo.create(frame)
                        if frame_id:
                            frame.id = frame_id
                            extracted_frames.append(frame)

                    self.log.emit(f"Extracted {len(extracted_frames)} frames, classifying birds...")
                    self.stage.emit(f"{video.file_name} - Classifying birds")

                    species_found = []
                    for frame in extracted_frames:
                        if self._cancelled:
                            break

                        analysis = pipeline.analyze_frame(
                            frame.file_path, frame.frame_number, top_k=3
                        )

                        for cr in analysis.classifications:
                            if cr.detection:
                                det = Detection(
                                    frame_id=frame.id,
                                    bbox_x=cr.detection.bbox[0],
                                    bbox_y=cr.detection.bbox[1],
                                    bbox_w=cr.detection.bbox[2] - cr.detection.bbox[0],
                                    bbox_h=cr.detection.bbox[3] - cr.detection.bbox[1],
                                    confidence=cr.detection.confidence,
                                )
                                det_id = self._detection_repo.create(det)

                                for rank, sp in enumerate(cr.species, 1):
                                    cls = Classification(
                                        detection_id=det_id,
                                        species_name=sp.en_name,
                                        species_name_zh=sp.cn_name,
                                        scientific_name=sp.scientific_name,
                                        confidence=sp.confidence,
                                        rank=rank,
                                    )
                                    self._classification_repo.create(cls)
                                    if rank == 1:
                                        species_found.append(sp.cn_name or sp.en_name)

                    self._video_repo.update_status(video.id, "completed")
                    summary = ", ".join(set(species_found)) if species_found else "No birds detected"
                    self.video_done.emit(video.id, summary)
                    self.log.emit(f"Done: {video.file_name} -> {summary}")

                except Exception as e:
                    self._video_repo.update_status(video.id, "error")
                    self.log.emit(f"Error processing {video.file_name}: {e}")

            self.progress.emit(total, total)
            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))
