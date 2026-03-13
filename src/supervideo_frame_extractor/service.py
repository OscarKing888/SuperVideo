from __future__ import annotations

from pathlib import Path

from .config import FrameConfigLoader
from .extractors.base import FrameExtractor
from .models import CliSettings, ExtractionRequest, ResizeOptions, VideoJobResult
from .scanner import VideoScanner


class ExtractionRequestBuilder:
    def __init__(self, config_loader: FrameConfigLoader) -> None:
        self._config_loader = config_loader

    def build(
        self,
        video_path: Path,
        settings: CliSettings,
        scan_root: Path | None,
    ) -> ExtractionRequest:
        config = self._config_loader.load(video_path)
        frames = config.frames or settings.frames
        resize_options = self._resolve_resize_options(settings.resize_options, config.resize_options)
        output_dir = self._resolve_output_dir(
            video_path=video_path,
            scan_root=scan_root,
            output_root=settings.output_root,
            cfg_output_dir=config.output_dir,
        )
        return ExtractionRequest(
            video_path=video_path,
            frames=frames,
            output_dir=output_dir,
            resize_options=resize_options,
            cfg_path=config.cfg_path,
        )

    @staticmethod
    def _resolve_resize_options(
        global_options: ResizeOptions,
        cfg_options: ResizeOptions,
    ) -> ResizeOptions:
        return cfg_options if cfg_options.has_override else global_options

    @staticmethod
    def _resolve_output_dir(
        video_path: Path,
        scan_root: Path | None,
        output_root: Path | None,
        cfg_output_dir: Path | None,
    ) -> Path:
        if cfg_output_dir is not None:
            if cfg_output_dir.is_absolute():
                return cfg_output_dir
            return (video_path.parent / cfg_output_dir).resolve()

        if output_root is None:
            return video_path.parent / f"{video_path.stem}_frames"

        base_output_root = output_root.expanduser().resolve()
        if scan_root is None:
            return base_output_root / video_path.stem

        relative_parent = video_path.parent.relative_to(scan_root)
        return base_output_root / relative_parent / video_path.stem


class FrameExtractionService:
    def __init__(
        self,
        scanner: VideoScanner,
        request_builder: ExtractionRequestBuilder,
        extractor: FrameExtractor,
    ) -> None:
        self._scanner = scanner
        self._request_builder = request_builder
        self._extractor = extractor

    def run(self, settings: CliSettings) -> list[VideoJobResult]:
        videos = self._scanner.scan(
            source_path=settings.source_path,
            extensions=settings.extensions,
            recursive=settings.recursive,
        )
        scan_root = (
            settings.source_path.expanduser().resolve()
            if settings.source_path.expanduser().resolve().is_dir()
            else None
        )

        results: list[VideoJobResult] = []
        for video_path in videos:
            try:
                request = self._request_builder.build(video_path, settings, scan_root)
                results.append(self._extractor.extract(request))
            except Exception as exc:
                results.append(
                    VideoJobResult(
                        video_path=video_path,
                        requested_frames=(),
                        error_message=str(exc),
                    )
                )
        return results
