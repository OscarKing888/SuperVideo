from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from supervideo_frame_extractor.config import IniSiblingConfigLoader
from supervideo_frame_extractor.models import CliSettings, ResizeOptions
from supervideo_frame_extractor.service import ExtractionRequestBuilder


class ConfigAndRequestBuilderTests(unittest.TestCase):
    def test_cfg_overrides_frames_resize_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video_path = root / "bird.mp4"
            video_path.write_bytes(b"")
            cfg_path = root / "bird.cfg"
            cfg_path.write_text(
                "\n".join(
                    [
                        "frames = 8, 16, 32",
                        "output_dir = shots",
                        "max_long_side = 640",
                    ]
                ),
                encoding="utf-8",
            )

            settings = CliSettings(
                source_path=root,
                frames=(5, 10, 30),
                output_root=root / "output",
                resize_options=ResizeOptions(scale_divisor=2),
            )
            request = ExtractionRequestBuilder(IniSiblingConfigLoader()).build(
                video_path=video_path,
                settings=settings,
                scan_root=root,
            )

            self.assertEqual(request.frames, (8, 16, 32))
            self.assertEqual(request.output_dir, (root / "shots").resolve())
            self.assertIsNone(request.resize_options.scale_divisor)
            self.assertEqual(request.resize_options.max_long_side, 640)
            self.assertEqual(request.cfg_path, cfg_path)


if __name__ == "__main__":
    unittest.main()
