from __future__ import annotations

import argparse
from pathlib import Path

from .config import IniSiblingConfigLoader, parse_frame_list
from .extractors.ffmpeg import FfmpegFrameExtractor
from .models import (
    CliSettings,
    COMMON_VIDEO_EXTENSIONS,
    DEFAULT_FRAME_NUMBERS,
    DEFAULT_VIDEO_EXTENSIONS,
    ResizeOptions,
    VideoJobResult,
    normalize_extensions,
    normalize_frame_numbers,
)
from .scanner import VideoScanner
from .service import ExtractionRequestBuilder, FrameExtractionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract selected video frames to JPG files."
    )
    parser.add_argument(
        "source",
        type=Path,
        help="Video file or directory to process.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Root directory for extracted JPGs. Defaults to sibling *_frames folders.",
    )
    parser.add_argument(
        "--frames",
        default="5,10,30",
        help="Comma or space separated 1-based frame numbers. Default: 5,10,30",
    )
    parser.add_argument(
        "--extensions",
        nargs="+",
        default=None,
        help="Video extensions to scan, for example: mp4 mov avi",
    )
    parser.add_argument(
        "--all-common-video-formats",
        action="store_true",
        help="Scan across a built-in common video extension list.",
    )
    parser.add_argument(
        "--scale-divisor",
        type=float,
        default=None,
        help="Shrink output size by divisor, for example 2 means half size.",
    )
    parser.add_argument(
        "--max-long-side",
        type=int,
        default=None,
        help="Limit the output long edge to the given pixel count.",
    )
    parser.add_argument(
        "--ffmpeg-binary",
        default="ffmpeg",
        help="ffmpeg executable path. Default: ffmpeg",
    )
    parser.add_argument(
        "--non-recursive",
        action="store_true",
        help="Disable recursive scanning for directory input.",
    )
    return parser


def parse_extensions(arguments: argparse.Namespace) -> tuple[str, ...]:
    if arguments.all_common_video_formats:
        return COMMON_VIDEO_EXTENSIONS
    if arguments.extensions:
        expanded: list[str] = []
        for token in arguments.extensions:
            expanded.extend(part for part in token.split(",") if part)
        return normalize_extensions(expanded)
    return DEFAULT_VIDEO_EXTENSIONS


def build_settings(arguments: argparse.Namespace) -> CliSettings:
    frames = normalize_frame_numbers(parse_frame_list(arguments.frames))
    resize_options = ResizeOptions(
        scale_divisor=arguments.scale_divisor,
        max_long_side=arguments.max_long_side,
    )
    return CliSettings(
        source_path=arguments.source,
        frames=frames,
        output_root=arguments.output_root,
        extensions=parse_extensions(arguments),
        resize_options=resize_options,
        recursive=not arguments.non_recursive,
        ffmpeg_binary=arguments.ffmpeg_binary,
    )


def format_result(result: VideoJobResult) -> str:
    if not result.succeeded:
        return f"[ERROR] {result.video_path}: {result.error_message}"

    extracted = ", ".join(str(item.frame_number) for item in result.extracted_frames) or "none"
    parts = [
        f"[OK] {result.video_path}",
        f"output={result.output_dir}",
        f"frames={extracted}",
    ]
    if result.cfg_path is not None:
        parts.append(f"cfg={result.cfg_path}")
    if result.missing_frames:
        missing = ", ".join(str(frame) for frame in result.missing_frames)
        parts.append(f"missing={missing}")
    return " | ".join(parts)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)

    try:
        settings = build_settings(arguments)
        service = FrameExtractionService(
            scanner=VideoScanner(),
            request_builder=ExtractionRequestBuilder(IniSiblingConfigLoader()),
            extractor=FfmpegFrameExtractor(ffmpeg_binary=settings.ffmpeg_binary),
        )
        results = service.run(settings)
        if not results:
            parser.error("No matching video files were found.")
    except Exception as exc:
        parser.exit(status=1, message=f"{exc}\n")

    for result in results:
        print(format_result(result))

    failures = sum(1 for result in results if not result.succeeded)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
