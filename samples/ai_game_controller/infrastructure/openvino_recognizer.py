"""OpenVINO recognizer adapter."""

from __future__ import annotations

from typing import Any


class OpenVINORecognizer:
    """Run recognizer-only OCR batches on configured CPU and Intel GPU devices."""

    def recognize(self, images: list[Any]) -> list[dict[str, Any]]:
        """Recognize one image batch after model runtime wiring is implemented."""
        raise NotImplementedError("OpenVINO recognition is not implemented yet")
