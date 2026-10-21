"""Errors raised by the optional YOLO backend."""


class YoloError(RuntimeError):
    """Base error for YOLO configuration and inference failures."""


class YoloDependencyError(YoloError):
    """ONNX Runtime is not installed or cannot be imported."""


class YoloModelNotFoundError(YoloError):
    """The configured ONNX model does not exist."""


class YoloInferenceError(YoloError):
    """The model could not run or returned an unsupported output."""
