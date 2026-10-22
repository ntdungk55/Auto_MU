"""Small YOLO ONNX detector for CPU runtime inference."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Sequence

import cv2
import numpy as np

from .exceptions import YoloInferenceError
from .model_manager import YoloModelManager
from .types import YoloDetection


class YoloDetector:
    """Run common YOLO export formats through ONNX Runtime on CPU."""

    def __init__(
        self,
        model_path: str | None = None,
        class_names: Sequence[str] | None = None,
        image_size: int = 640,
    ) -> None:
        self.model_manager = YoloModelManager(model_path)
        self.class_names = list(class_names or [])
        self.image_size = max(32, int(image_size))
        self.last_debug: dict[str, float | int] = {}

    def detect_file(
        self,
        image_path: str,
        confidence: float = 0.25,
        iou: float = 0.45,
        class_ids: Iterable[int] | None = None,
    ) -> list[YoloDetection]:
        image = self._read_image(image_path)
        if image is None:
            raise YoloInferenceError(f"Cannot read image: {image_path}")
        return self.detect(image, confidence, iou, class_ids)

    def detect(
        self,
        image_bgr: np.ndarray,
        confidence: float = 0.25,
        iou: float = 0.45,
        class_ids: Iterable[int] | None = None,
    ) -> list[YoloDetection]:
        if image_bgr is None or image_bgr.size == 0:
            raise YoloInferenceError("Input image is empty")
        if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
            raise YoloInferenceError("YOLO input must be a BGR color image")

        session = self.model_manager.get_session()
        input_meta = session.get_inputs()[0]
        input_size = self._input_size(input_meta.shape)
        tensor, ratio, pad = self._preprocess(image_bgr, input_size)
        try:
            raw_outputs = session.run(None, {input_meta.name: tensor})
        except Exception as exc:
            raise YoloInferenceError(f"YOLO inference failed: {exc}") from exc

        allowed = {int(value) for value in class_ids} if class_ids else None
        rows = self._normalise_output(raw_outputs)
        candidates: list[tuple[int, float, float, float, float, float]] = []
        raw_scores: list[float] = []
        for row in rows:
            parsed = self._parse_row(row, -float("inf"))
            if parsed is None:
                continue
            class_id, score, x1, y1, x2, y2 = parsed
            raw_scores.append(score)
            if score < confidence:
                continue
            if allowed is not None and class_id not in allowed:
                continue
            candidates.append((class_id, score, x1, y1, x2, y2))

        kept = self._nms(candidates, float(iou))
        self.last_debug = {
            "raw_candidates": len(raw_scores),
            "max_confidence": max(raw_scores, default=0.0),
            "threshold": float(confidence),
            "candidates_after_threshold": len(candidates),
        }
        height, width = image_bgr.shape[:2]
        detections = []
        for class_id, score, x1, y1, x2, y2 in kept:
            x1 = self._unletterbox(x1, pad[0], ratio, width)
            x2 = self._unletterbox(x2, pad[0], ratio, width)
            y1 = self._unletterbox(y1, pad[1], ratio, height)
            y2 = self._unletterbox(y2, pad[1], ratio, height)
            detections.append(
                YoloDetection(
                    class_id=class_id,
                    class_name=self.class_names[class_id] if class_id < len(self.class_names) else "",
                    confidence=float(score),
                    x1=int(round(x1)), y1=int(round(y1)),
                    x2=int(round(x2)), y2=int(round(y2)),
                )
            )
        return detections

    def _input_size(self, shape: Sequence[object]) -> tuple[int, int]:
        if len(shape) >= 4 and all(isinstance(value, int) for value in shape[-2:]):
            return int(shape[-1]), int(shape[-2])
        return self.image_size, self.image_size

    @staticmethod
    def _read_image(path: str) -> np.ndarray | None:
        try:
            data = np.fromfile(path, dtype=np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except OSError:
            return None

    @staticmethod
    def _preprocess(image: np.ndarray, size: tuple[int, int]):
        target_w, target_h = size
        source_h, source_w = image.shape[:2]
        ratio = min(target_w / source_w, target_h / source_h)
        new_w, new_h = max(1, round(source_w * ratio)), max(1, round(source_h * ratio))
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        pad_x, pad_y = (target_w - new_w) / 2, (target_h - new_h) / 2
        canvas = np.full((target_h, target_w, 3), 114, dtype=np.uint8)
        left, top = round(pad_x), round(pad_y)
        canvas[top:top + new_h, left:left + new_w] = resized
        tensor = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = np.transpose(tensor, (2, 0, 1))[None, ...]
        return tensor, ratio, (pad_x, pad_y)

    @staticmethod
    def _normalise_output(outputs: list[np.ndarray]) -> np.ndarray:
        if not outputs:
            raise YoloInferenceError("YOLO model returned no outputs")
        output = np.asarray(outputs[0])
        while output.ndim > 2 and output.shape[0] == 1:
            output = output[0]
        if output.ndim != 2:
            raise YoloInferenceError(f"Unsupported YOLO output shape: {output.shape}")
        if output.shape[0] < output.shape[1] and output.shape[0] <= 256:
            output = output.T
        return output

    @staticmethod
    def _parse_row(row: np.ndarray, threshold: float):
        if row.shape[0] < 6:
            return None
        if row.shape[0] == 6:
            x1, y1, x2, y2, score, class_id = row[:6]
        else:
            scores = row[4:]
            class_id = int(np.argmax(scores))
            score = float(scores[class_id])
            x, y, w, h = map(float, row[:4])
            x1, y1, x2, y2 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
        score = float(score)
        if score < threshold:
            return None
        return int(class_id), score, float(x1), float(y1), float(x2), float(y2)

    @staticmethod
    def _nms(candidates, iou_threshold: float):
        selected = []
        for candidate in sorted(candidates, key=lambda item: item[1], reverse=True):
            _, _, ax1, ay1, ax2, ay2 = candidate
            area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
            suppressed = False
            for other in selected:
                _, _, bx1, by1, bx2, by2 = other
                inter = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
                union = area_a + max(0.0, bx2 - bx1) * max(0.0, by2 - by1) - inter
                if union > 0 and inter / union > iou_threshold:
                    suppressed = True
                    break
            if not suppressed:
                selected.append(candidate)
        return selected

    @staticmethod
    def _unletterbox(value: float, pad: float, ratio: float, limit: int) -> float:
        return min(max((value - pad) / ratio, 0.0), float(limit))
