"""Application settings management."""

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class AppSettings:
    video_directory: str = ""
    server_host: str = "localhost"
    server_port: int = 8080
    api_key: str = ""
    frames_to_extract: str = "5,10,30"
    ffmpeg_binary: str = "ffmpeg"
    yolo_model_path: str = ""
    osea_model_path: str = ""
    confidence_threshold: float = 0.25
    db_path: str = ""

    @property
    def server_url(self) -> str:
        return f"http://{self.server_host}:{self.server_port}"

    def save(self, path: str):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "AppSettings":
        if not os.path.exists(path):
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
