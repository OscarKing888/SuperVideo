"""Download AI model weights for bird classification."""

import os
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    models_dir = project_root / "models"
    models_dir.mkdir(exist_ok=True)

    print("SuperVideo Model Download Script")
    print("=" * 50)
    print()
    print("The following model files are required for bird classification:")
    print()
    print("1. YOLO11L-seg (yolo11l-seg.pt)")
    print("   - Used for bird detection in images")
    print("   - Download from: https://github.com/ultralytics/assets/releases")
    print(f"   - Place at: {models_dir / 'yolo11l-seg.pt'}")
    print()
    print("2. OSEA ResNet34 (model20240824.pth)")
    print("   - Used for bird species classification (10,964 species)")
    print("   - Source: https://github.com/bird-feeder/OSEA")
    print(f"   - Place at: {models_dir / 'model20240824.pth'}")
    print()
    print("3. TOPIQ CFANet (cfanet_iaa_ava_res50-3cd62bb3.pth) [optional]")
    print("   - Used for aesthetic quality scoring")
    print("   - Source: https://github.com/chaofengc/IQA-PyTorch")
    print(f"   - Place at: {models_dir / 'cfanet_iaa_ava_res50-3cd62bb3.pth'}")
    print()
    print("4. Bird Reference Database (bird_reference.sqlite)")
    print("   - Species names and eBird codes for 11K+ species")
    print("   - Copy from E:\\SuperPickyOrig\\birdid\\data\\bird_reference.sqlite")
    data_dir = project_root / "src" / "supervideo_bird_classifier" / "data"
    print(f"   - Place at: {data_dir / 'bird_reference.sqlite'}")
    print()

    # Check which models are already present
    checks = [
        (models_dir / "yolo11l-seg.pt", "YOLO11L-seg"),
        (models_dir / "model20240824.pth", "OSEA ResNet34"),
        (models_dir / "cfanet_iaa_ava_res50-3cd62bb3.pth", "TOPIQ CFANet"),
        (data_dir / "bird_reference.sqlite", "Bird Reference DB"),
    ]

    print("Status:")
    all_ok = True
    for path, name in checks:
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"  [OK] {name}: {path.name} ({size_mb:.1f} MB)")
        else:
            print(f"  [MISSING] {name}: {path}")
            all_ok = False

    if all_ok:
        print("\nAll models are present!")
    else:
        print("\nSome models are missing. Please download them manually.")
        sys.exit(1)


if __name__ == "__main__":
    main()
