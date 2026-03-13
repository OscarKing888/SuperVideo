from __future__ import annotations

from pathlib import Path

from .models import ConfigurationError, normalize_extensions


class VideoScanner:
    def scan(
        self,
        source_path: Path,
        extensions: tuple[str, ...] | list[str],
        recursive: bool = True,
    ) -> list[Path]:
        normalized_extensions = set(normalize_extensions(extensions))
        path = source_path.expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {path}")

        if path.is_file():
            if path.suffix.lower() not in normalized_extensions:
                raise ConfigurationError(
                    f"Unsupported video extension for file: {path.name}."
                )
            return [path]

        iterator = path.rglob("*") if recursive else path.glob("*")
        video_files = [
            item
            for item in iterator
            if item.is_file() and item.suffix.lower() in normalized_extensions
        ]
        return sorted(video_files)
