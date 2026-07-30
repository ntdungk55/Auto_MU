"""Unit tests for EasyOCR line-based reconstruction."""

import numpy as np

from src.logic.system_executor.ocr_engine import EasyOCREngine


class _FakeEasyOCRReader:
    def __init__(self, results):
        self._results = results

    def readtext(self, img, detail=1, decoder="greedy"):
        return self._results


def test_easyocr_group_results_into_lines_rebuilds_visual_rows():
    results = [
        (
            [[10, 10], [60, 10], [60, 30], [10, 30]],
            "Line1-A",
            0.98,
        ),
        (
            [[70, 12], [120, 12], [120, 32], [70, 32]],
            "Line1-B",
            0.97,
        ),
        (
            [[12, 60], [62, 60], [62, 82], [12, 82]],
            "Line2-A",
            0.96,
        ),
        (
            [[72, 62], [122, 62], [122, 84], [72, 84]],
            "Line2-B",
            0.95,
        ),
    ]

    lines = EasyOCREngine._group_results_into_lines(results)

    assert lines == ["Line1-A Line1-B", "Line2-A Line2-B"]


def test_easyocr_recognize_lines_uses_detail_boxes():
    results = [
        (
            [[10, 10], [60, 10], [60, 30], [10, 30]],
            "Alpha",
            0.98,
        ),
        (
            [[10, 50], [60, 50], [60, 70], [10, 70]],
            "Beta",
            0.97,
        ),
    ]
    engine = EasyOCREngine()
    engine._get_reader = lambda: _FakeEasyOCRReader(results)  # type: ignore[method-assign]

    img = np.zeros((100, 100, 3), dtype=np.uint8)
    lines = engine.recognize_lines(img)
    text = engine.recognize(img)

    assert lines == ["Alpha", "Beta"]
    assert text == "Alpha\nBeta"
