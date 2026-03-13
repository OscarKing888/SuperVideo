from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from ..models import ExtractedFrame, ExtractionError, ExtractionRequest, VideoJobResult
from .base import FrameExtractor


class FfmpegFrameExtractor(FrameExtractor):
    def __init__(self, ffmpeg_binary: str = "ffmpeg") -> None:
        self._ffmpeg_binary = ffmpeg_binary

    def extract(self, request: ExtractionRequest) -> VideoJobResult:
        request.output_dir.mkdir(parents=True, exist_ok=True)

        requested_frames = request.frames
        temp_prefix = f"__extract_{uuid.uuid4().hex}"
        temp_pattern = request.output_dir / f"{temp_prefix}_%06d.jpg"

        command = [
            self._ffmpeg_binary,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(request.video_path),
            "-vf",
            self._build_filter_chain(requested_frames, request.resize_options),
            "-vsync",
            "0",
            "-q:v",
            "2",
            str(temp_pattern),
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError as exc:
            raise ExtractionError(
                f"ffmpeg executable was not found: {self._ffmpeg_binary}"
            ) from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip() or "unknown ffmpeg failure"
            raise ExtractionError(stderr)

        temp_files = sorted(request.output_dir.glob(f"{temp_prefix}_*.jpg"))
        extracted_frames: list[ExtractedFrame] = []

        for frame_number, temp_file in zip(requested_frames, temp_files):
            final_path = request.output_dir / f"{request.video_path.stem}_frame_{frame_number:06d}.jpg"
            if final_path.exists():
                final_path.unlink()
            temp_file.replace(final_path)
            extracted_frames.append(
                ExtractedFrame(frame_number=frame_number, output_path=final_path)
            )

        for extra_file in temp_files[len(extracted_frames) :]:
            extra_file.unlink(missing_ok=True)

        missing_frames = requested_frames[len(extracted_frames) :]
        return VideoJobResult(
            video_path=request.video_path,
            requested_frames=requested_frames,
            output_dir=request.output_dir,
            cfg_path=request.cfg_path,
            extracted_frames=extracted_frames,
            missing_frames=missing_frames,
        )

    def _build_filter_chain(self, frames: tuple[int, ...], resize_options) -> str:
        filters = [self._build_select_filter(frames)]
        scale_filter = self._build_scale_filter(resize_options)
        if scale_filter:
            filters.append(scale_filter)
        return ",".join(filters)

    @staticmethod
    def _build_select_filter(frames: tuple[int, ...]) -> str:
        expressions = "+".join(f"eq(n\\,{frame_number - 1})" for frame_number in frames)
        return f"select='{expressions}'"

    @staticmethod
    def _build_scale_filter(resize_options) -> str | None:
        if resize_options.scale_divisor is not None:
            divisor = resize_options.scale_divisor
            return (
                "scale="
                f"w='max(1,trunc(iw/{divisor}))':"
                f"h='max(1,trunc(ih/{divisor}))':"
                "flags=lanczos"
            )
        if resize_options.max_long_side is not None:
            limit = resize_options.max_long_side
            return (
                "scale="
                f"w='if(gte(iw,ih),min(iw,{limit}),-2)':"
                f"h='if(gte(iw,ih),-2,min(ih,{limit}))':"
                "flags=lanczos"
            )
        return None
