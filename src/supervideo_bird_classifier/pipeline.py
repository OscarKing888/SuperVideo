"""Classification pipeline: detect -> crop -> classify -> score."""

from dataclasses import dataclass, field
from typing import List, Optional

from PIL import Image

from supervideo_bird_classifier.classifier import (
    Classifier,
    OSEAClassifier,
    SpeciesResult,
    get_classifier,
)
from supervideo_bird_classifier.detector import (
    BirdDetection,
    Detector,
    YOLOBirdDetector,
)
from supervideo_bird_classifier.scorer import Scorer, TOPIQScorer, get_scorer


@dataclass
class DetectionResult:
    bbox: tuple
    confidence: float


@dataclass
class ClassificationResult:
    species: List[SpeciesResult]
    detection: Optional[DetectionResult] = None
    quality_score: Optional[float] = None


@dataclass
class FrameAnalysis:
    frame_path: str
    frame_number: int
    bird_detected: bool
    classifications: List[ClassificationResult] = field(default_factory=list)
    error: Optional[str] = None


class ClassificationPipeline:
    def __init__(
        self,
        detector: Optional[Detector] = None,
        classifier: Optional[Classifier] = None,
        scorer: Optional[Scorer] = None,
        yolo_model_path: Optional[str] = None,
        osea_model_path: Optional[str] = None,
        use_scorer: bool = False,
    ):
        self._detector = detector
        self._classifier = classifier
        self._scorer = scorer
        self._yolo_path = yolo_model_path
        self._osea_path = osea_model_path
        self._use_scorer = use_scorer

    @property
    def detector(self) -> Optional[Detector]:
        if self._detector is None and self._yolo_path:
            try:
                self._detector = YOLOBirdDetector(self._yolo_path)
            except Exception:
                pass
        return self._detector

    @property
    def classifier(self) -> Classifier:
        if self._classifier is None:
            kwargs = {}
            if self._osea_path:
                kwargs["model_path"] = self._osea_path
            self._classifier = get_classifier(**kwargs)
        return self._classifier

    @property
    def scorer(self) -> Optional[Scorer]:
        if self._scorer is None and self._use_scorer:
            try:
                self._scorer = get_scorer()
            except Exception:
                pass
        return self._scorer

    def analyze_image(
        self,
        image: Image.Image,
        top_k: int = 5,
        use_yolo: bool = True,
    ) -> ClassificationResult:
        detection = None
        classify_image = image

        if use_yolo and self.detector:
            det = self.detector.detect_and_crop(image)
            if det is None:
                return ClassificationResult(species=[], detection=None)
            detection = DetectionResult(bbox=det.bbox, confidence=det.confidence)
            classify_image = det.cropped_image or image

        species = self.classifier.classify(classify_image, top_k=top_k)
        quality = self.scorer.score(classify_image) if self.scorer else None

        return ClassificationResult(
            species=species,
            detection=detection,
            quality_score=quality,
        )

    def analyze_frame(
        self,
        frame_path: str,
        frame_number: int,
        top_k: int = 5,
        use_yolo: bool = True,
    ) -> FrameAnalysis:
        try:
            image = Image.open(frame_path).convert("RGB")
        except Exception as e:
            return FrameAnalysis(
                frame_path=frame_path,
                frame_number=frame_number,
                bird_detected=False,
                error=str(e),
            )

        result = self.analyze_image(image, top_k=top_k, use_yolo=use_yolo)
        return FrameAnalysis(
            frame_path=frame_path,
            frame_number=frame_number,
            bird_detected=len(result.species) > 0,
            classifications=[result] if result.species else [],
        )

    def analyze_frames(
        self,
        frame_paths: List[str],
        frame_numbers: Optional[List[int]] = None,
        top_k: int = 5,
        use_yolo: bool = True,
    ) -> List[FrameAnalysis]:
        if frame_numbers is None:
            frame_numbers = list(range(len(frame_paths)))
        return [
            self.analyze_frame(path, num, top_k=top_k, use_yolo=use_yolo)
            for path, num in zip(frame_paths, frame_numbers)
        ]
