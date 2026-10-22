"""YOLO inference through the CPU-friendly ONNX Runtime backend."""

from .detector import YoloDetector
from .types import YoloDetection

__all__ = ["YoloDetector", "YoloDetection"]
