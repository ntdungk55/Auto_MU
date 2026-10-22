"""Model discovery and lazy ONNX Runtime session creation."""

from __future__ import annotations

import os
import sys
import importlib
from pathlib import Path
from typing import Any

from ...app_paths import get_yolo_models_root
from .exceptions import YoloDependencyError, YoloModelNotFoundError


class YoloModelManager:
    """Resolve runtime models without importing ONNX Runtime at app startup."""

    def __init__(self, model_path: str | None = None) -> None:
        self.model_path = model_path or ""
        self._session: Any = None

    @staticmethod
    def list_models() -> list[str]:
        root = Path(get_yolo_models_root())
        if not root.exists():
            return []
        return sorted(str(path) for path in root.glob("*.onnx") if path.is_file())

    def resolve_model_path(self) -> str:
        if self.model_path:
            path = Path(os.path.abspath(self.model_path))
        else:
            path = Path(get_yolo_models_root()) / "nameplate.onnx"
        if not path.is_file():
            raise YoloModelNotFoundError(
                f"Nameplate model does not exist: {path}. "
                "Train/export nameplate.onnx before enabling YOLO."
            )
        return str(path)

    def get_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            ort = self._import_onnxruntime()
        except Exception as exc:  # pragma: no cover - depends on optional install
            raise YoloDependencyError(
                "onnxruntime import failed: "
                f"{type(exc).__name__}: {exc}. Rebuild the app with ONNX Runtime included."
            ) from exc

        self._session = ort.InferenceSession(
            self.resolve_model_path(),
            providers=["CPUExecutionProvider"],
        )
        return self._session

    @staticmethod
    def _import_onnxruntime() -> Any:
        """Import ONNX Runtime from the active interpreter or project venv.

        Source launches sometimes use the system ``python`` instead of the
        project's venv. The fallback keeps that supported without affecting
        frozen builds, where ONNX Runtime is bundled by PyInstaller.
        """
        try:
            return importlib.import_module("onnxruntime")
        except ModuleNotFoundError as first_error:
            project_root = Path(__file__).resolve().parents[4]
            venv_site = project_root / ".venv" / "Lib" / "site-packages"
            if not venv_site.is_dir() or str(venv_site) in sys.path:
                raise first_error
            sys.path.insert(0, str(venv_site))
            importlib.invalidate_caches()
            return importlib.import_module("onnxruntime")
