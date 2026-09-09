"""Load the one mandatory system prompt shared by every AI model adapter."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import sys


SYSTEM_PROMPT_RELATIVE_PATH = Path("prompt") / "system_prompt" / "scenario_engine_system_prompt.md"
MAX_SYSTEM_PROMPT_BYTES = 1_000_000


@dataclass(frozen=True)
class LoadedSystemPrompt:
    text: str
    path: Path
    sha256: str


class SystemPromptLoader:
    """Resolve source/frozen paths and fail fast on a missing or empty prompt."""

    def __init__(self, scenario_engine_root: str | Path | None = None) -> None:
        self._explicit_root = Path(scenario_engine_root) if scenario_engine_root is not None else None

    @staticmethod
    def default_scenario_engine_root() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / "scenario_engine"
        return Path(__file__).resolve().parents[3] / "scenario_engine"

    @property
    def prompt_path(self) -> Path:
        root = self._explicit_root or self.default_scenario_engine_root()
        return root / SYSTEM_PROMPT_RELATIVE_PATH

    def load(self) -> LoadedSystemPrompt:
        path = self.prompt_path
        try:
            size = path.stat().st_size
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Không tìm thấy system prompt dùng chung: {path}") from exc
        except OSError as exc:
            raise RuntimeError(f"Không thể đọc thông tin system prompt: {path}: {exc}") from exc
        if size > MAX_SYSTEM_PROMPT_BYTES:
            raise ValueError(f"System prompt vượt quá {MAX_SYSTEM_PROMPT_BYTES} bytes: {path}")
        try:
            text = path.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as exc:
            raise RuntimeError(f"Không thể đọc system prompt UTF-8: {path}: {exc}") from exc
        if not text:
            raise ValueError(f"System prompt không được để trống: {path}")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return LoadedSystemPrompt(text=text, path=path, sha256=digest)

