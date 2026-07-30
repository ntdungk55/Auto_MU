import os
import time
import threading
import subprocess
import sys
import importlib
from typing import Optional, Callable

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QPixmap, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QComboBox,
    QMessageBox,
    QGroupBox,
    QScrollArea,
    QFileDialog,
    QDialog,
)

try:
    from PIL import Image
    from PIL import ImageEnhance, ImageFilter, ImageOps
except Exception:
    Image = None

try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None


class _Signals(QObject):
    append_html = pyqtSignal(str)
    append_message = pyqtSignal(object)
    set_busy = pyqtSignal(bool)

_AUTO_INSTALL_STARTED = False


class _PromptTextEdit(QTextEdit):
    """Text input that accepts dropping an image file as an attachment (Messenger-like)."""

    attachment_dropped = pyqtSignal(str)
    send_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.textChanged.connect(self._auto_resize_height)
        self._min_h = 44
        self._max_h = 120
        self.setFixedHeight(self._min_h)

    def _auto_resize_height(self):
        """Grow until max height; then keep fixed and let the editor scroll."""
        try:
            doc_h = int(self.document().size().height()) + 18
            h = max(self._min_h, min(self._max_h, doc_h))
            self.setFixedHeight(h)
        except Exception:
            pass

    def keyPressEvent(self, e: QKeyEvent):
        try:
            if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    super().keyPressEvent(e)
                    return
                self.send_requested.emit()
                return
        except Exception:
            pass
        super().keyPressEvent(e)

    def dragEnterEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                for u in event.mimeData().urls():
                    if not u or not u.isLocalFile():
                        continue
                    p = u.toLocalFile()
                    ext = os.path.splitext(p)[1].lower()
                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        event.acceptProposedAction()
                        return
        except Exception:
            pass
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        try:
            if event.mimeData().hasUrls():
                for u in event.mimeData().urls():
                    if not u or not u.isLocalFile():
                        continue
                    p = u.toLocalFile()
                    ext = os.path.splitext(p)[1].lower()
                    if ext in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                        self.attachment_dropped.emit(p)
                        event.acceptProposedAction()
                        return
        except Exception:
            pass
        super().dropEvent(event)


class _ChatBubble(QWidget):
    def __init__(self, text: str, side: str = "left", image_path: str | None = None, meta: str | None = None, parent=None):
        super().__init__(parent)
        outer = QHBoxLayout()
        outer.setContentsMargins(6, 2, 6, 2)

        bubble = QWidget()
        bubble_l = QVBoxLayout()
        bubble_l.setContentsMargins(10, 8, 10, 8)
        bubble_l.setSpacing(6)

        label = QLabel(text or "")
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        bubble_l.addWidget(label)

        if image_path:
            pm = QPixmap(image_path)
            img = QLabel()
            if not pm.isNull():
                img.setPixmap(pm.scaled(240, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                img.setText(os.path.basename(image_path))
            bubble_l.addWidget(img)

        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setStyleSheet("color:#9aa0a6;font-size:11px;")
            bubble_l.addWidget(meta_lbl)

        bubble.setLayout(bubble_l)

        if side == "right":
            bubble.setStyleSheet("background:#1b74e4;color:#fff;border-radius:14px;")
            outer.addStretch(1)
            outer.addWidget(bubble, 0)
        elif side == "system":
            bubble.setStyleSheet("background:#1f1f1f;color:#d0d0d0;border-radius:10px;")
            outer.addStretch(1)
            outer.addWidget(bubble, 0)
            outer.addStretch(1)
        else:
            bubble.setStyleSheet("background:#2b2b2b;color:#e6e6e6;border-radius:14px;")
            outer.addWidget(bubble, 0)
            outer.addStretch(1)

        self.setLayout(outer)


class GeminiSettingsDialog(QDialog):
    """Settings dialog for Gemini chat (API key + model)."""

    def __init__(
        self,
        parent=None,
        initial_key: str = "",
        initial_model: str = "gemini-1.5-flash",
        on_save_key: Callable[[str], None] | None = None,
        on_clear_key: Callable[[], None] | None = None,
        on_save_model: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Gemini Settings")
        self.setFixedWidth(520)
        self._on_save_key = on_save_key
        self._on_clear_key = on_clear_key
        self._on_save_model = on_save_model

        layout = QVBoxLayout()

        # Key row
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API key:"))
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setText(initial_key or "")
        key_row.addWidget(self.key_input, 1)

        self.save_key_btn = QPushButton("Lưu key")
        self.save_key_btn.clicked.connect(self._save_key_clicked)
        key_row.addWidget(self.save_key_btn)

        self.clear_key_btn = QPushButton("Xóa key đã lưu")
        self.clear_key_btn.clicked.connect(self._clear_key_clicked)
        key_row.addWidget(self.clear_key_btn)
        layout.addLayout(key_row)

        # Model row
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(
            [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.0-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.0-pro",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
                "Custom…",
            ]
        )
        model_row.addWidget(self.model_combo, 1)

        self.custom_model_input = QLineEdit()
        self.custom_model_input.setPlaceholderText("vd: gemini-2.5-pro")
        model_row.addWidget(self.custom_model_input, 1)
        layout.addLayout(model_row)

        # Init model selection
        initial_model = (initial_model or "gemini-1.5-flash").strip()
        idx = self.model_combo.findText(initial_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
            self.custom_model_input.setVisible(False)
        else:
            self.model_combo.setCurrentText("Custom…")
            self.custom_model_input.setText(initial_model)
            self.custom_model_input.setVisible(True)
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.close_btn = QPushButton("Đóng")
        self.close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self.close_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _on_model_changed(self, _idx: int):
        try:
            is_custom = str(self.model_combo.currentText()) == "Custom…"
        except Exception:
            is_custom = False
        self.custom_model_input.setVisible(bool(is_custom))

    def selected_model(self) -> str:
        name = str(self.model_combo.currentText() or "").strip()
        if name == "Custom…":
            name = str(self.custom_model_input.text() or "").strip()
        return name

    def _save_key_clicked(self):
        if self._on_save_key is None:
            return
        k = (self.key_input.text() or "").strip()
        if not k:
            QMessageBox.warning(self, "Thiếu key", "Không có API key để lưu.")
            return
        try:
            self._on_save_key(k)
        except Exception as e:
            QMessageBox.warning(self, "Lỗi lưu key", str(e))

    def _clear_key_clicked(self):
        if self._on_clear_key is None:
            return
        try:
            self._on_clear_key()
            self.key_input.clear()
        except Exception as e:
            QMessageBox.warning(self, "Lỗi xóa key", str(e))

    def save_model(self):
        if self._on_save_model is None:
            return
        name = self.selected_model()
        if not name:
            return
        try:
            self._on_save_model(name)
        except Exception:
            pass


class GeminiChatWidget(QWidget):
    """A lightweight Gemini chat tab with optional image input and response timing."""

    def __init__(
        self,
        parent=None,
        load_saved_key: Callable[[], str] | None = None,
        save_key: Callable[[str], None] | None = None,
        clear_saved_key: Callable[[], None] | None = None,
        load_saved_model: Callable[[], str] | None = None,
        save_model: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self._signals = _Signals()
        self._signals.append_html.connect(self._append_system_text, Qt.ConnectionType.QueuedConnection)
        self._signals.append_message.connect(self._append_message, Qt.ConnectionType.QueuedConnection)
        self._signals.set_busy.connect(self._set_busy, Qt.ConnectionType.QueuedConnection)

        self._chat = None
        self._current_model_name = ""
        self._installing_sdk = False
        self._load_saved_key = load_saved_key
        self._save_key_cb = save_key
        self._clear_saved_key_cb = clear_saved_key
        self._load_saved_model = load_saved_model
        self._save_model_cb = save_model

        self._build_ui()
        self._append_system_text("Đang khởi tạo Gemini…")
        self._auto_install_sdk_if_missing()
        QTimer.singleShot(0, self._ensure_connected)
        # More reliable auto-scroll: wait for scroll range to update after layout changes.
        self._pending_scroll_to_bottom = False
        try:
            self.scroll.verticalScrollBar().rangeChanged.connect(self._on_scroll_range_changed)
        except Exception:
            pass

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header (minimal)
        header_row = QHBoxLayout()
        self.title_lbl = QLabel("<b>Gemini Chat</b>")
        header_row.addWidget(self.title_lbl, 0)
        header_row.addStretch(1)
        self.status_lbl = QLabel("Not connected")
        self.status_lbl.setStyleSheet("color:#9aa0a6;")
        header_row.addWidget(self.status_lbl, 0)
        layout.addLayout(header_row)

        # Chat area (bubbles)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background:#0f0f0f;border:1px solid #222;")
        self.chat_container = QWidget()
        self.chat_layout = QVBoxLayout()
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.setSpacing(6)
        self.chat_container.setLayout(self.chat_layout)
        self.scroll.setWidget(self.chat_container)
        layout.addWidget(self.scroll, 1)

        self._chat_spacer = QWidget()
        self._chat_spacer.setMinimumHeight(1)
        self.chat_layout.addWidget(self._chat_spacer)

        # Attachment preview (hidden until attached)
        self.attach_row = QWidget()
        attach_l = QHBoxLayout()
        attach_l.setContentsMargins(0, 0, 0, 0)
        self.attach_row.setLayout(attach_l)
        self.attach_thumb = QLabel("")
        self.attach_thumb.setMinimumHeight(46)
        self.attach_thumb.setMinimumWidth(80)
        self.attach_thumb.setStyleSheet("background:#111;border:1px dashed #666;padding:6px;")
        self.attach_name = QLabel("")
        self.attach_name.setStyleSheet("color:#aaa;")
        self.clear_attach_btn = QPushButton("Xóa")
        self.clear_attach_btn.clicked.connect(self._clear_attachment)
        attach_l.addWidget(self.attach_thumb, 0)
        attach_l.addWidget(self.attach_name, 1)
        attach_l.addWidget(self.clear_attach_btn, 0)
        layout.addWidget(self.attach_row)
        self._attach_path: Optional[str] = None

        # Input bar (buttons near Send)
        input_bar = QHBoxLayout()
        self.prompt = _PromptTextEdit()
        self.prompt.attachment_dropped.connect(self._set_attachment_from_drop)
        self.prompt.send_requested.connect(self._send)
        self.prompt.setPlaceholderText("Nhập câu hỏi… (Enter để gửi, Shift+Enter xuống dòng, kéo‑thả ảnh vào đây)")
        self.prompt.setMinimumHeight(44)
        self.prompt.setStyleSheet("background:#111;color:#e6e6e6;border:1px solid #222;border-radius:12px;")
        input_bar.addWidget(self.prompt, 1)

        self.attach_btn = QPushButton("Đính kèm")
        self.attach_btn.clicked.connect(self._pick_image)
        input_bar.addWidget(self.attach_btn, 0)

        self.install_btn = QPushButton("Cài SDK")
        self.install_btn.clicked.connect(self._install_gemini_sdk)
        input_bar.addWidget(self.install_btn, 0)

        self.settings_btn = QPushButton("Setting")
        self.settings_btn.clicked.connect(self._open_settings)
        input_bar.addWidget(self.settings_btn, 0)

        self.send_btn = QPushButton("Gửi")
        self.send_btn.clicked.connect(self._send)
        input_bar.addWidget(self.send_btn, 0)
        layout.addLayout(input_bar)

        self.setLayout(layout)
        self._append_system_text("Sẵn sàng. Kéo‑thả ảnh vào ô nhập để đính kèm, rồi bấm Gửi.")
        self._refresh_attachment_ui()
        self._refresh_install_button()
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _current_key(self) -> str:
        try:
            if self._load_saved_key is not None:
                k = str(self._load_saved_key() or "").strip()
                if k:
                    return k
        except Exception:
            pass
        return str(os.environ.get("GEMINI_API_KEY", "") or "").strip()

    def _current_model(self) -> str:
        try:
            if self._load_saved_model is not None:
                m = str(self._load_saved_model() or "").strip()
                if m:
                    return m
        except Exception:
            pass
        return "gemini-1.5-flash"

    def _refresh_attachment_ui(self):
        try:
            has = bool(self._attach_path)
            self.clear_attach_btn.setEnabled(has)
            self.attach_name.setText(os.path.basename(self._attach_path) if has else "")
            self.attach_row.setVisible(has)
            if not has:
                self.attach_thumb.setPixmap(QPixmap())
        except Exception:
            pass

    def _clear_attachment(self):
        self._attach_path = None
        self._refresh_attachment_ui()

    def _set_attachment_from_drop(self, path: str):
        try:
            if not path or not os.path.exists(path):
                return
            ext = os.path.splitext(path)[1].lower()
            if ext not in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                return
            self._attach_path = path
            pm = QPixmap(path)
            if not pm.isNull():
                self.attach_thumb.setPixmap(pm.scaled(120, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self._refresh_attachment_ui()
        except Exception:
            return

    def _pick_image(self):
        try:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Chọn ảnh",
                "",
                "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
            )
            if path:
                self._set_attachment_from_drop(path)
        except Exception:
            return

    def _refresh_install_button(self):
        try:
            # Auto-install will run; keep this as a retry button when install fails.
            self.install_btn.setEnabled((genai is None) and (not self._installing_sdk))
            self.install_btn.setVisible(genai is None)
        except Exception:
            pass

    def _auto_install_sdk_if_missing(self):
        global _AUTO_INSTALL_STARTED
        if genai is not None:
            self._refresh_install_button()
            return
        # Avoid auto-install loops across multiple widget instances.
        if _AUTO_INSTALL_STARTED:
            self._signals.append_html.emit("SDK chưa có. Bạn có thể bấm 'Cài Gemini SDK' để thử lại.")
            self._refresh_install_button()
            return
        _AUTO_INSTALL_STARTED = True
        self._install_gemini_sdk(auto=True)

    def _try_import_sdk(self) -> bool:
        """Try importing Gemini SDK and PIL after a pip install (no restart)."""
        global genai, Image
        ok = True
        try:
            if genai is None:
                genai = importlib.import_module("google.generativeai")
        except Exception:
            ok = False
        try:
            if Image is None:
                Image = importlib.import_module("PIL.Image").Image  # type: ignore
        except Exception:
            # PIL is optional for text-only usage
            pass
        self._refresh_install_button()
        return ok

    def _install_gemini_sdk(self, auto: bool = False):
        """Install Gemini SDK via pip using current Python executable.

        auto=True: used on first open; keep UI fully hands-off.
        """
        if genai is not None:
            self._signals.append_html.emit("SDK đã có sẵn.")
            self._refresh_install_button()
            return
        if self._installing_sdk:
            return

        self._installing_sdk = True
        self._signals.set_busy.emit(True)
        self._signals.append_html.emit("Đang cài Gemini SDK (pip)..." if not auto else "Thiếu SDK → đang tự cài (pip)...")
        self._refresh_install_button()

        def _worker():
            t0 = time.perf_counter()
            try:
                cmd = [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--disable-pip-version-check",
                    "--no-input",
                    "google-generativeai",
                ]
                p = subprocess.run(cmd, capture_output=True, text=True)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                if p.returncode != 0:
                    msg = (p.stderr or p.stdout or "").strip()
                    self._signals.append_html.emit(f"[pip failed] {msg}\n(time: {dt_ms/1000.0:.2f}s)")
                    return

                ok = self._try_import_sdk()
                if not ok:
                    self._signals.append_html.emit("[import failed] Cài xong nhưng không import được SDK. Hãy thử cài lại hoặc restart app.")
                    return
                self._signals.append_html.emit(f"Cài xong. Bạn bấm Kết nối lại. (time: {dt_ms/1000.0:.2f}s)")
            except Exception as e:
                self._signals.append_html.emit(f"[pip error] {str(e)}")
            finally:
                self._installing_sdk = False
                self._signals.set_busy.emit(False)
                self._refresh_install_button()

        threading.Thread(target=_worker, daemon=True).start()

    def _open_settings(self):
        dlg = GeminiSettingsDialog(
            parent=self,
            initial_key=self._current_key(),
            initial_model=self._current_model(),
            on_save_key=self._save_key_cb,
            on_clear_key=self._clear_saved_key_cb,
            on_save_model=self._save_model_cb,
        )
        if dlg.exec():
            # Save selected model & reconnect
            try:
                if self._save_model_cb is not None:
                    self._save_model_cb(dlg.selected_model())
            except Exception:
                pass
            self._ensure_connected(force_reconnect=True)

    def _append_bubble(self, text: str, side: str, image_path: str | None = None, meta: str | None = None):
        try:
            idx = max(0, self.chat_layout.count() - 1)
            self.chat_layout.insertWidget(idx, _ChatBubble(text=text, side=side, image_path=image_path, meta=meta))
            self._pending_scroll_to_bottom = True
            QTimer.singleShot(0, self._scroll_to_bottom)
            QTimer.singleShot(30, self._scroll_to_bottom)
        except Exception:
            pass

    def _on_scroll_range_changed(self, _min: int, _max: int):
        """Called after layout updates change the scroll range."""
        try:
            if self._pending_scroll_to_bottom:
                self._pending_scroll_to_bottom = False
                self._scroll_to_bottom()
        except Exception:
            pass

    def _scroll_to_bottom(self):
        try:
            sb = self.scroll.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    def _append_system_text(self, text: str):
        self._append_bubble(text, side="system")

    def _append_message(self, payload: object):
        try:
            if not isinstance(payload, dict):
                return
            self._append_bubble(
                text=str(payload.get("text", "") or ""),
                side=str(payload.get("side", "left") or "left"),
                image_path=payload.get("image_path"),
                meta=payload.get("meta"),
            )
        except Exception:
            return

    def _set_busy(self, busy: bool):
        try:
            self.send_btn.setEnabled(not busy)
            self.attach_btn.setEnabled(not busy)
            self.settings_btn.setEnabled(not busy)
            self.install_btn.setEnabled((not busy) and (genai is None) and (not self._installing_sdk))
        except Exception:
            pass

    def _ensure_sdk(self) -> bool:
        if genai is None:
            # Auto-trigger install; user doesn't need to do anything.
            self._auto_install_sdk_if_missing()
            return False
        return True

    def _connect_gemini(self):
        if not self._ensure_sdk():
            return

        key = self._current_key()
        if not key:
            QMessageBox.warning(self, "Thiếu API key", "Bạn hãy nhập API key (hoặc set GEMINI_API_KEY).")
            return

        model_name = self._current_model()
        if not model_name:
            QMessageBox.warning(self, "Thiếu model", "Bạn hãy chọn model.")
            return

        try:
            genai.configure(api_key=key)
            # Light validation: ensure model exists/accessible (no generation call)
            try:
                if hasattr(genai, "get_model"):
                    genai.get_model(f"models/{model_name}")  # type: ignore
            except Exception as e:
                raise RuntimeError(f"Model không dùng được: {e}") from e
            model = genai.GenerativeModel(model_name)
            self._chat = model.start_chat(history=[])
            self._current_model_name = model_name
            self._append_system_text(f"Connected: {model_name}")
            try:
                self.status_lbl.setText(f"Connected | {model_name}")
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(self, "Model không dùng được", str(e))
            self._chat = None
            self._current_model_name = ""
            try:
                self.status_lbl.setText("Not connected")
            except Exception:
                pass

    def _ensure_connected(self, force_reconnect: bool = False):
        """Auto-connect when entering tab (if key exists)."""
        if genai is None:
            return
        try:
            if not force_reconnect and self._chat is not None:
                return
        except Exception:
            pass
        if not self._current_key():
            try:
                self.status_lbl.setText("No API key")
            except Exception:
                pass
            return
        self._connect_gemini()

    def showEvent(self, event):
        try:
            super().showEvent(event)
        except Exception:
            pass
        QTimer.singleShot(0, self._ensure_connected)
        QTimer.singleShot(0, self._scroll_to_bottom)

    def _send(self):
        if not self._ensure_sdk():
            return
        if self._chat is None:
            self._connect_gemini()
            if self._chat is None:
                return

        prompt = (self.prompt.toPlainText() or "").strip()
        img_path = self._attach_path
        if not prompt and not img_path:
            return

        # Snapshot inputs (avoid UI thread races)
        model_name = self._current_model_name

        self.prompt.clear()
        self._signals.set_busy.emit(True)

        self._append_bubble(prompt if prompt else "", side="right", image_path=img_path)
        if img_path:
            self._attach_path = None
            self._refresh_attachment_ui()

        def _worker():
            t0 = time.perf_counter()
            try:
                parts = []
                if prompt:
                    parts.append(prompt)
                if img_path and Image is not None:
                    try:
                        parts.append(self._prepare_image_for_vision(img_path))
                    except Exception:
                        pass
                # If PIL missing or image failed, fall back to text-only prompt
                if not parts:
                    parts = [prompt or ""]

                resp = self._chat.send_message(parts)
                dt_ms = (time.perf_counter() - t0) * 1000.0
                txt = ""
                try:
                    txt = getattr(resp, "text", "") or ""
                except Exception:
                    txt = ""
                self._signals.append_message.emit(
                    {
                        "side": "left",
                        "text": txt,
                        "meta": f"{dt_ms/1000.0:.2f}s | {model_name}",
                    }
                )
            except Exception as e:
                dt_ms = (time.perf_counter() - t0) * 1000.0
                self._signals.append_message.emit(
                    {
                        "side": "system",
                        "text": f"Lỗi: {str(e)}",
                        "meta": f"{dt_ms/1000.0:.2f}s",
                    }
                )
            finally:
                self._signals.set_busy.emit(False)

        threading.Thread(target=_worker, daemon=True).start()

    @staticmethod
    def _prepare_image_for_vision(img_path: str):
        """Improve readability for text-heavy screenshots before sending to Gemini.

        Conservative pipeline: EXIF transpose, upscale (2x when small), mild contrast, and unsharp mask.
        """
        if Image is None:
            raise RuntimeError("PIL not available")
        im = Image.open(img_path)
        try:
            im = ImageOps.exif_transpose(im)
        except Exception:
            pass

        # Convert to RGB for consistent downstream handling
        try:
            if getattr(im, "mode", "") not in ("RGB", "L"):
                im = im.convert("RGB")
        except Exception:
            pass

        w, h = im.size
        # Upscale small screenshots to help OCR-like reading in vision models
        scale = 1
        if max(w, h) < 900:
            scale = 2
        if max(w, h) < 500:
            scale = 3

        if scale > 1:
            nw, nh = int(w * scale), int(h * scale)
            # cap to avoid extremely large images
            cap = 2200
            if max(nw, nh) > cap:
                ratio = cap / float(max(nw, nh))
                nw, nh = int(nw * ratio), int(nh * ratio)
            im = im.resize((nw, nh), resample=Image.Resampling.LANCZOS)

        # Light grayscale+autocontrast tends to help small Vietnamese diacritics
        try:
            g = im.convert("L")
            g = ImageOps.autocontrast(g, cutoff=1)
            im = g.convert("RGB")
        except Exception:
            pass

        try:
            im = ImageEnhance.Contrast(im).enhance(1.25)
        except Exception:
            pass

        try:
            im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=160, threshold=3))
        except Exception:
            pass

        return im

    @staticmethod
    def _escape(s: str) -> str:
        try:
            return (
                str(s)
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
        except Exception:
            return ""


