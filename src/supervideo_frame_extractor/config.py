from __future__ import annotations

from abc import ABC, abstractmethod
from configparser import ConfigParser, MissingSectionHeaderError
from pathlib import Path

from .models import ConfigurationError, FrameConfig, ResizeOptions, normalize_frame_numbers


def parse_frame_list(value: str) -> tuple[int, ...]:
    tokens = [token for token in value.replace(",", " ").split() if token]
    if not tokens:
        raise ConfigurationError("frames must contain at least one frame number.")
    return normalize_frame_numbers([int(token) for token in tokens])


class FrameConfigLoader(ABC):
    @abstractmethod
    def load(self, video_path: Path) -> FrameConfig:
        raise NotImplementedError


class IniSiblingConfigLoader(FrameConfigLoader):
    section_name = "extract"

    def load(self, video_path: Path) -> FrameConfig:
        cfg_path = video_path.with_suffix(".cfg")
        if not cfg_path.exists():
            return FrameConfig()

        raw_text = cfg_path.read_text(encoding="utf-8").strip()
        if not raw_text:
            return FrameConfig(cfg_path=cfg_path)

        parser = ConfigParser()
        parser.optionxform = str
        try:
            parser.read_string(raw_text)
        except MissingSectionHeaderError:
            parser.read_string(f"[{self.section_name}]\n{raw_text}")
        except Exception as exc:
            raise ConfigurationError(f"Failed to parse cfg file: {cfg_path}") from exc

        if parser.has_section(self.section_name):
            section = parser[self.section_name]
        else:
            section = parser.defaults()

        frames_value = section.get("frames")
        output_dir_value = section.get("output_dir")
        scale_divisor_value = section.get("scale_divisor")
        max_long_side_value = section.get("max_long_side")

        try:
            frames = parse_frame_list(frames_value) if frames_value else None
            output_dir = Path(output_dir_value).expanduser() if output_dir_value else None
            resize_options = ResizeOptions(
                scale_divisor=float(scale_divisor_value) if scale_divisor_value else None,
                max_long_side=int(max_long_side_value) if max_long_side_value else None,
            )
        except Exception as exc:
            raise ConfigurationError(f"Invalid values in cfg file: {cfg_path}") from exc

        return FrameConfig(
            cfg_path=cfg_path,
            frames=frames,
            output_dir=output_dir,
            resize_options=resize_options,
        )
