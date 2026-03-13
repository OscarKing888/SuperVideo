from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_FRAME_NUMBERS = (5, 10, 30)
DEFAULT_VIDEO_EXTENSIONS = (".mp4",)
COMMON_VIDEO_EXTENSIONS = (
    ".mp4",
    ".avi",
    ".mov",
    ".mkv",
    ".wmv",
    ".flv",
    ".webm",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ts",
    ".mts",
    ".m2ts",
)


class ConfigurationError(ValueError):
    """Raised when user supplied configuration is invalid."""


class ExtractionError(RuntimeError):
    """Raised when a frame extraction backend fails."""


def normalize_frame_numbers(frame_numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    unique = sorted(set(int(number) for number in frame_numbers))
    if not unique:
        raise ConfigurationError("At least one frame number must be provided.")
    if any(number < 1 for number in unique):
        raise ConfigurationError("Frame numbers are 1-based and must be >= 1.")
    return tuple(unique)


def normalize_extensions(extensions: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    normalized = []
    for extension in extensions:
        item = extension.strip().lower()
        if not item:
            continue
        normalized.append(item if item.startswith(".") else f".{item}")
    unique = sorted(set(normalized))
    if not unique:
        raise ConfigurationError("At least one video extension must be provided.")
    return tuple(unique)


@dataclass(frozen=True, slots=True)
class ResizeOptions:
    scale_divisor: float | None = None
    max_long_side: int | None = None

    def __post_init__(self) -> None:
        if self.scale_divisor is not None and self.scale_divisor < 1:
            raise ConfigurationError("scale_divisor must be >= 1.")
        if self.max_long_side is not None and self.max_long_side < 1:
            raise ConfigurationError("max_long_side must be >= 1.")
        if self.scale_divisor is not None and self.max_long_side is not None:
            raise ConfigurationError("scale_divisor and max_long_side cannot be used together.")

    @property
    def has_override(self) -> bool:
        return self.scale_divisor is not None or self.max_long_side is not None


@dataclass(frozen=True, slots=True)
class FrameConfig:
    cfg_path: Path | None = None
    frames: tuple[int, ...] | None = None
    output_dir: Path | None = None
    resize_options: ResizeOptions = field(default_factory=ResizeOptions)


@dataclass(frozen=True, slots=True)
class CliSettings:
    source_path: Path
    frames: tuple[int, ...] = DEFAULT_FRAME_NUMBERS
    output_root: Path | None = None
    extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS
    resize_options: ResizeOptions = field(default_factory=ResizeOptions)
    recursive: bool = True
    ffmpeg_binary: str = "ffmpeg"


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    video_path: Path
    frames: tuple[int, ...]
    output_dir: Path
    resize_options: ResizeOptions
    cfg_path: Path | None = None


@dataclass(frozen=True, slots=True)
class ExtractedFrame:
    frame_number: int
    output_path: Path


@dataclass(slots=True)
class VideoJobResult:
    video_path: Path
    requested_frames: tuple[int, ...]
    output_dir: Path | None = None
    cfg_path: Path | None = None
    extracted_frames: list[ExtractedFrame] = field(default_factory=list)
    missing_frames: tuple[int, ...] = ()
    error_message: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.error_message is None
