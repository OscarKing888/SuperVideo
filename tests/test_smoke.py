from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_VIDEO = REPO_ROOT / "video" / "test.mp4"


class SmokeTests(unittest.TestCase):
    def test_cli_extracts_default_frames_from_sample_video(self) -> None:
        if not TEST_VIDEO.exists():
            self.skipTest(f"Missing test video: {TEST_VIDEO}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            copied_video = temp_root / "test.mp4"
            shutil.copy2(TEST_VIDEO, copied_video)

            output_root = temp_root / "output"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "supervideo_frame_extractor",
                    str(copied_video),
                    "--output-root",
                    str(output_root),
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            jpg_files = sorted((output_root / "test").glob("*.jpg"))
            self.assertEqual(
                [item.name for item in jpg_files],
                [
                    "test_frame_000005.jpg",
                    "test_frame_000010.jpg",
                    "test_frame_000030.jpg",
                ],
            )

            with Image.open(jpg_files[0]) as image:
                self.assertGreater(image.width, 0)
                self.assertGreater(image.height, 0)

    def test_cli_uses_sibling_cfg_overrides(self) -> None:
        if not TEST_VIDEO.exists():
            self.skipTest(f"Missing test video: {TEST_VIDEO}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            copied_video = temp_root / "bird.mp4"
            copied_cfg = temp_root / "bird.cfg"
            shutil.copy2(TEST_VIDEO, copied_video)
            copied_cfg.write_text(
                "\n".join(
                    [
                        "frames = 2, 4",
                        "output_dir = cfg_frames",
                    ]
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = str(REPO_ROOT / "src")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "supervideo_frame_extractor",
                    str(copied_video),
                    "--frames",
                    "5,10,30",
                ],
                cwd=REPO_ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

            jpg_files = sorted((temp_root / "cfg_frames").glob("*.jpg"))
            self.assertEqual(
                [item.name for item in jpg_files],
                [
                    "bird_frame_000002.jpg",
                    "bird_frame_000004.jpg",
                ],
            )


if __name__ == "__main__":
    unittest.main()
