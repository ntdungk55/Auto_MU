"""Value objects returned by the YOLO detector."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class YoloDetection:
    """One object detected in an image, using pixel coordinates."""

    class_id: int
    confidence: float
    x1: int
    y1: int
    x2: int
    y2: int
    class_name: str = ""

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        return self.x1, self.y1, self.x2, self.y2
