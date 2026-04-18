"""SuperVideo Bird Classifier - GPU-accelerated bird species identification."""

from supervideo_bird_classifier.device import get_best_device
from supervideo_bird_classifier.pipeline import ClassificationPipeline

__version__ = "0.1.0"
__all__ = ["get_best_device", "ClassificationPipeline"]
