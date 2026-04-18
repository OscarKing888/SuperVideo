"""OSEA ResNet34 bird species classifier (10,964 species)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import os
import sqlite3
import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision import models, transforms

from supervideo_bird_classifier.device import get_best_device


@dataclass(frozen=True)
class SpeciesResult:
    class_id: int
    cn_name: str
    en_name: str
    scientific_name: str
    confidence: float
    ebird_code: Optional[str] = None


class Classifier(ABC):
    @abstractmethod
    def classify(self, image: Image.Image, top_k: int = 5) -> List[SpeciesResult]:
        ...


# ImageNet normalization
_IMAGENET_MEAN = [0.485, 0.456, 0.406]
_IMAGENET_STD = [0.229, 0.224, 0.225]

CENTER_CROP_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
])

DIRECT_RESIZE_TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.LANCZOS),
    transforms.ToTensor(),
    transforms.Normalize(mean=_IMAGENET_MEAN, std=_IMAGENET_STD),
])


def _get_resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent.parent.parent
    return base / relative_path


def _torch_load_compat(path: str, *, map_location: str, weights_only: bool):
    try:
        return torch.load(path, map_location=map_location, weights_only=weights_only)
    except TypeError:
        return torch.load(path, map_location=map_location)


def _load_osea_checkpoint(model_path: str):
    try:
        return _torch_load_compat(model_path, map_location="cpu", weights_only=True)
    except Exception as e:
        if "weights_only" in str(e) or "WeightsUnpickler" in str(e):
            return _torch_load_compat(model_path, map_location="cpu", weights_only=False)
        raise


class OSEAClassifier(Classifier):
    NUM_CLASSES = 10964
    DEFAULT_MODEL_PATH = "models/model20240824.pth"
    DEFAULT_DB_PATH = "src/supervideo_bird_classifier/data/bird_reference.sqlite"

    def __init__(
        self,
        model_path: Optional[str] = None,
        db_path: Optional[str] = None,
        use_center_crop: bool = False,
        device: Optional[torch.device] = None,
    ):
        self.device = device or get_best_device()
        self.use_center_crop = use_center_crop
        self.transform = CENTER_CROP_TRANSFORM if use_center_crop else DIRECT_RESIZE_TRANSFORM

        resolved_model = model_path or str(_get_resource_path(self.DEFAULT_MODEL_PATH))
        self.model = self._load_model(resolved_model)

        resolved_db = db_path or str(_get_resource_path(self.DEFAULT_DB_PATH))
        self.bird_info = self._load_bird_info(resolved_db)

    def _load_model(self, model_path: str) -> torch.nn.Module:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"OSEA model not found: {model_path}")

        loaded = _load_osea_checkpoint(model_path)
        if isinstance(loaded, torch.nn.Module):
            model = loaded
        else:
            model = models.resnet34(num_classes=11000)
            state_dict = loaded
            if isinstance(loaded, dict):
                state_dict = loaded.get("state_dict", loaded.get("model_state_dict", loaded))
            model.load_state_dict(state_dict)

        model.to(self.device)
        model.eval()
        return model

    def _load_bird_info(self, db_path: str) -> List[List[str]]:
        if not os.path.exists(db_path):
            return [["Unknown", "Unknown", "", None, None] for _ in range(self.NUM_CLASSES)]

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.execute(
                "SELECT model_class_id, chinese_simplified, english_name, "
                "scientific_name, ebird_code "
                "FROM BirdCountInfo WHERE model_class_id IS NOT NULL "
                "ORDER BY model_class_id"
            )
            rows = cur.fetchall()
        finally:
            conn.close()

        info: List[List[str]] = [["Unknown", "Unknown", "", None, None] for _ in range(self.NUM_CLASSES)]
        for class_id, cn, en, sci, ebird in rows:
            if 0 <= class_id < self.NUM_CLASSES:
                info[class_id] = [cn or "Unknown", en or "Unknown", sci or "", ebird, None]
        return info

    def classify(
        self,
        image: Image.Image,
        top_k: int = 5,
        temperature: float = 0.9,
    ) -> List[SpeciesResult]:
        if image.mode != "RGB":
            image = image.convert("RGB")

        input_tensor = self.transform(image).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(input_tensor)[0]

        output = output[: self.NUM_CLASSES]
        probs = torch.nn.functional.softmax(output / temperature, dim=0)

        k = min(top_k, self.NUM_CLASSES)
        top_probs, top_indices = torch.topk(probs, k)

        results = []
        for i in range(len(top_indices)):
            class_id = top_indices[i].item()
            confidence = top_probs[i].item() * 100
            if confidence < 1.0:
                continue

            info = self.bird_info[class_id]
            results.append(SpeciesResult(
                class_id=class_id,
                cn_name=info[0],
                en_name=info[1],
                scientific_name=info[2],
                confidence=confidence,
                ebird_code=info[3],
            ))
        return results


_singleton: Optional[OSEAClassifier] = None


def get_classifier(**kwargs) -> OSEAClassifier:
    global _singleton
    if _singleton is None:
        _singleton = OSEAClassifier(**kwargs)
    return _singleton
