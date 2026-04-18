"""YOLO-based bird detection from images."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class BirdDetection:
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    cropped_image: Optional[Image.Image] = None


class Detector(ABC):
    @abstractmethod
    def detect(self, image: Image.Image, confidence_threshold: float = 0.25) -> List[BirdDetection]:
        ...

    @abstractmethod
    def detect_and_crop(
        self,
        image: Image.Image,
        confidence_threshold: float = 0.25,
        padding_ratio: float = 0.15,
    ) -> Optional[BirdDetection]:
        ...


class YOLOBirdDetector(Detector):
    BIRD_CLASS_ID = 14  # COCO dataset bird class

    def __init__(self, model_path: str):
        from ultralytics import YOLO
        self._model = YOLO(model_path)

    def detect(self, image: Image.Image, confidence_threshold: float = 0.25) -> List[BirdDetection]:
        img_array = np.array(image)
        results = self._model(img_array, conf=confidence_threshold, verbose=False)

        detections = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].cpu().numpy())
                if class_id != self.BIRD_CLASS_ID:
                    continue
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                detections.append(BirdDetection(
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    confidence=float(box.conf[0].cpu().numpy()),
                ))
        return detections

    def detect_and_crop(
        self,
        image: Image.Image,
        confidence_threshold: float = 0.25,
        padding_ratio: float = 0.15,
    ) -> Optional[BirdDetection]:
        detections = self.detect(image, confidence_threshold)
        if not detections:
            return None

        best = max(detections, key=lambda d: d.confidence)
        cropped = self._smart_square_crop(image, best.bbox, padding_ratio)
        return BirdDetection(
            bbox=best.bbox,
            confidence=best.confidence,
            cropped_image=cropped,
        )

    @staticmethod
    def _smart_square_crop(
        image: Image.Image,
        bbox: Tuple[int, int, int, int],
        padding_ratio: float,
        fill_color: Tuple[int, int, int] = (0, 0, 0),
    ) -> Image.Image:
        x1, y1, x2, y2 = bbox
        img_w, img_h = image.size

        max_side = max(x2 - x1, y2 - y1)
        target_side = int(max_side * (1 + padding_ratio))

        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        half = target_side // 2

        crop_x1 = max(0, cx - half)
        crop_y1 = max(0, cy - half)
        crop_x2 = min(img_w, cx + half)
        crop_y2 = min(img_h, cy + half)

        cropped = image.crop((crop_x1, crop_y1, crop_x2, crop_y2))
        crop_w, crop_h = cropped.size

        if crop_w != crop_h:
            sq_size = max(crop_w, crop_h)
            square = Image.new("RGB", (sq_size, sq_size), fill_color)
            square.paste(cropped, ((sq_size - crop_w) // 2, (sq_size - crop_h) // 2))
            return square

        return cropped
