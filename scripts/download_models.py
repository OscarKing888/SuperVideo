"""Download AI model weights for bird classification from HuggingFace Hub.

All remote model artifacts come from HuggingFace. The bird reference SQLite is
copied from the SuperPickyOrig project since it is not published publicly.
"""

import logging
import os
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="strict")

try:
    from huggingface_hub import hf_hub_download
except ImportError:
    print(
        "Error: huggingface_hub is not installed. "
        "Please run `pip install huggingface_hub tqdm` first."
    )
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
DATA_DIR = PROJECT_ROOT / "src" / "supervideo_bird_classifier" / "data"

HF_MODELS = [
    {
        "category": "Detection",
        "repo_id": "Ultralytics/YOLO11",
        "filename": "yolo11l-seg.pt",
        "dest_dir": MODELS_DIR,
    },
    {
        "category": "Classification",
        "repo_id": "jamesphotography/SuperPicky-models",
        "filename": "model20240824.pth",
        "dest_dir": MODELS_DIR,
    },
    {
        "category": "Quality Assessment",
        "repo_id": "chaofengc/IQA-PyTorch-Weights",
        "filename": "cfanet_iaa_ava_res50-3cd62bb3.pth",
        "dest_dir": MODELS_DIR,
    },
]

SUPERPICKY_DB_PATH = Path(r"E:\SuperPickyOrig\birdid\data\bird_reference.sqlite")
BIRD_DB_DEST = DATA_DIR / "bird_reference.sqlite"


def _already_present(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def download_from_hf(item: dict) -> bool:
    dest_dir: Path = item["dest_dir"]
    filename: str = item["filename"]
    repo_id: str = item["repo_id"]
    category: str = item["category"]
    target = dest_dir / filename

    dest_dir.mkdir(parents=True, exist_ok=True)

    if _already_present(target):
        size_mb = target.stat().st_size / (1024 * 1024)
        logging.info(f"[{category}] {filename} already present ({size_mb:.1f} MB), skipping.")
        return True

    logging.info(f"[{category}] Downloading {filename} from {repo_id}...")
    try:
        hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(dest_dir),
            local_dir_use_symlinks=False,
        )
    except Exception as exc:
        logging.error(f"[{category}] Failed to download {filename} from {repo_id}: {exc}")
        return False

    if not target.exists():
        logging.error(f"[{category}] Download reported success but {target} is missing.")
        return False
    size_mb = target.stat().st_size / (1024 * 1024)
    logging.info(f"[{category}] OK {filename} ({size_mb:.1f} MB)")
    return True


def copy_bird_reference_db() -> bool:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if _already_present(BIRD_DB_DEST):
        size_mb = BIRD_DB_DEST.stat().st_size / (1024 * 1024)
        logging.info(f"[Database] bird_reference.sqlite already present ({size_mb:.1f} MB), skipping.")
        return True

    if not SUPERPICKY_DB_PATH.exists():
        logging.error(
            f"[Database] Source not found: {SUPERPICKY_DB_PATH}. "
            "Obtain bird_reference.sqlite manually and place it at "
            f"{BIRD_DB_DEST}."
        )
        return False

    logging.info(f"[Database] Copying bird_reference.sqlite from {SUPERPICKY_DB_PATH}...")
    try:
        shutil.copy2(SUPERPICKY_DB_PATH, BIRD_DB_DEST)
    except Exception as exc:
        logging.error(f"[Database] Copy failed: {exc}")
        return False

    size_mb = BIRD_DB_DEST.stat().st_size / (1024 * 1024)
    logging.info(f"[Database] OK bird_reference.sqlite ({size_mb:.1f} MB)")
    return True


def print_status() -> bool:
    logging.info("Status:")
    all_ok = True
    rows = [(MODELS_DIR / m["filename"], m["filename"]) for m in HF_MODELS]
    rows.append((BIRD_DB_DEST, "bird_reference.sqlite"))
    for path, name in rows:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            logging.info(f"  [OK] {name} ({size_mb:.1f} MB) -> {path}")
        else:
            logging.info(f"  [MISSING] {name} -> {path}")
            all_ok = False
    return all_ok


def main() -> int:
    logging.info("SuperVideo Model Download Script (HuggingFace)")
    logging.info(f"Project root: {PROJECT_ROOT}")

    successes = sum(download_from_hf(item) for item in HF_MODELS)
    if copy_bird_reference_db():
        successes += 1

    total = len(HF_MODELS) + 1
    all_present = print_status()

    if successes == total and all_present:
        logging.info(f"All {total} files are ready.")
        return 0

    logging.error(f"Only {successes}/{total} files are ready. See errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
