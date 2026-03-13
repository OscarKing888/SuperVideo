from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ExtractionRequest, VideoJobResult


class FrameExtractor(ABC):
    @abstractmethod
    def extract(self, request: ExtractionRequest) -> VideoJobResult:
        raise NotImplementedError
