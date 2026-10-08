import sys
import threading
import ctypes
import os
import json
from datetime import datetime

# Set DPI awareness BEFORE importing PyQt6 for high-quality screenshots
def _set_dpi_awareness():
    """Set DPI awareness for high-quality window capture."""
    try:
        # Windows 10 1607+ (best quality)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)  # PER_MONITOR_AWARE_V2
        return
    except Exception:
        pass
    try:
        # Windows 8.1+
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        # Windows Vista+
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

_set_dpi_awareness()


def _release_modifier_keys_fast():
    """Release common modifier keys directly via Win32 without constructing heavy objects."""
    try:
        user32 = ctypes.windll.user32
        key_up = 0x0002
        for vk_code in (0x12, 0x11, 0x10, 0x5B, 0x5C):
            try:
                user32.keybd_event(vk_code, 0, key_up, 0)
            except Exception:
                pass
    except Exception:
        pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget, 
                             QLabel, QTextEdit, QComboBox, QPushButton, QHBoxLayout,
                             QMessageBox, QToolBar, QStackedWidget, QDialog, QGroupBox, QRadioButton, QSpinBox, QCheckBox,
                             QTableWidget, QTableWidgetItem, QToolButton, QListWidget, QListWidgetItem, QMenu)
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QEvent
from PyQt6.QtGui import QTextOption, QColor, QBrush, QKeySequence
from PyQt6.QtGui import QAction
import time
from src.logic.action_type import ActionType, AutoAction
from src.logic.system_executor import SystemExecutor
from src.logic.window_detector import WindowDetector
from src.logic.tool_manager import ToolManager, Tool
from src.ui.tool_editor_window import ToolEditorWindow
from src.ui.tool_settings_dialog import ToolSettingsDialog
from src.ui.gemini_chat_widget import AIChatWorkspace
from src.ui.teaching_algorithm_lab_widget import TeachingAlgorithmLabWidget
from src.logic.dpapi import protect_to_b64, unprotect_from_b64

try:
    import keyboard  # type: ignore
except Exception:
    keyboard = None

try:
    import win32gui  # type: ignore
except Exception:
    win32gui = None

# --- 1. DOMAIN LAYER ---
# (Sử dụng Enum và Dataclass từ action_type.py)

# --- 2. ENGINE LAYER ---
class AutoBotEngine:
    def __init__(self, signals, executor: SystemExecutor = None, tool_manager=None):
        self.signals = signals
        self.executor = executor  # Sẽ được set sau
        self.tool_manager = tool_manager  # For reloading settings
        self.is_running = False
        self.should_stop_completely = False
        # Cancel only the current cycle/loop iteration (apply new settings next cycle)
        self.cancel_cycle_requested = False
        self.current_tool: Tool = None
        self.current_action_index = 0  # Lưu index action hiện tại để tiếp tục khi dừng
        self.loop_cycles_done = 0
        # Telegram timeout notification deduplication (tool_name -> timestamp)
        self._last_timeout_notification: dict[str, float] = {}
        # Emergency hotkey monitoring
        self._emergency_stop_event = threading.Event()
        self._hotkey_thread = None
        self._hotkey_thread_running = False
    
    def _emit_phase(self, phase: str):
        """Emit phase to UI if supported by signals object."""
        try:
            if hasattr(self.signals, "phase"):
                self.signals.phase.emit(str(phase))
        except Exception:
            pass
    
    def _start_emergency_hotkey_monitor(self):
        """Start monitoring F12 for emergency stop using global hotkey."""
        if not keyboard:
            return
        
        if self._hotkey_thread and self._hotkey_thread.is_alive():
            return  # Already running
        
        self._emergency_stop_event.clear()
        self._hotkey_thread_running = True
        
        def on_f12_pressed():
            """Callback when F12 is pressed."""
            self._emergency_stop_event.set()
            # Unlock input immediately
            if self.executor and hasattr(self.executor, 'mouse_controller'):
                try:
                    self.executor.mouse_controller.block_input(False)
                    self.signals.log.emit("<b style='color:red;'>🔓 Emergency unlock (F12)</b>")
                except Exception:
                    pass
            self.stop_completely()
        
        try:
            # Use global hotkey hook (works even when input is blocked)
            keyboard.add_hotkey('f12', on_f12_pressed, suppress=False)
            self.signals.log.emit("<b style='color:gray;'>[Hotkey] F12 đã được đăng ký</b>")
        except Exception as e:
            self.signals.log.emit(f"<b style='color:orange;'>[Hotkey] Không thể đăng ký F12: {e}</b>")
    
    def _stop_emergency_hotkey_monitor(self):
        """Stop monitoring emergency hotkey."""
        self._hotkey_thread_running = False
        try:
            keyboard.remove_hotkey('f12')
        except Exception:
            pass
        self._hotkey_thread = None
    
    def request_cancel_cycle(self):
        """Request cancelling current cycle ASAP. Only makes sense for looping tools."""
        try:
            self.cancel_cycle_requested = True
        except Exception:
            pass

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep, but return False if stop/cancel requested."""
        try:
            seconds = float(seconds or 0)
        except Exception:
            seconds = 0.0
        if seconds <= 0:
            return True
        end = time.time() + seconds
        while time.time() < end:
            if (not self.is_running) or self.should_stop_completely:
                return False
            if bool(getattr(self, "cancel_cycle_requested", False)):
                return False
            remaining = end - time.time()
            time.sleep(0.05 if remaining > 0.05 else max(0.0, remaining))
        return True

    def start(self, tool: Tool, resume: bool = False, target_window_hwnd=None):
        """Bắt đầu hoặc tiếp tục chạy tool
        resume: True nếu tiếp tục từ step hiện tại, False để bắt đầu từ đầu
        target_window_hwnd: Window handle để focus trước khi chạy"""
        if not resume:
            # Bắt đầu mới: reset tất cả
            self.should_stop_completely = False
            self.current_tool = tool
            self.current_action_index = 0
            self.loop_cycles_done = 0
            self.signals.log.emit(f"<b>BẮT ĐẦU:</b> Tool: {tool.name}")
        else:
            # Tiếp tục: giữ nguyên current_action_index
            if not self.current_tool or self.current_tool.name != tool.name:
                # Tool khác, reset
                self.current_tool = tool
                self.current_action_index = 0
                self.loop_cycles_done = 0
                self.signals.log.emit(f"<b>BẮT ĐẦU:</b> Tool: {tool.name}")
            else:
                self.signals.log.emit(f"<b>TIẾP TỤC:</b> Tool: {tool.name} từ step {self.current_action_index + 1}")
        
        # Focus vào window trước khi chạy (chỉ khi bắt đầu mới, không phải resume)
        if not resume and target_window_hwnd:
            from src.logic.window_detector import WindowDetector
            window_detector = WindowDetector()
            window_detector.set_foreground_window(target_window_hwnd)
            self.signals.log.emit(f"Đã focus vào window game")
            time.sleep(0.2)  # Đợi window ổn định
        
        if not self.is_running:
            self.is_running = True
            # Start emergency hotkey monitoring if input blocking enabled
            if bool(getattr(self.current_tool, "block_input_enabled", False)):
                self._start_emergency_hotkey_monitor()
            threading.Thread(target=self._run, daemon=True).start()
    
    def stop(self):
        """Dừng tạm thời (có thể tiếp tục)"""
        self.is_running = False
        self._stop_emergency_hotkey_monitor()
        # Unlock input if blocked
        if self.executor and hasattr(self.executor, 'mouse_controller'):
            try:
                self.executor.mouse_controller.block_input(False)
            except Exception:
                pass
        self._emit_phase("idle")
        self.signals.log.emit(f"<b style='color:orange;'>ĐÃ DỪNG (có thể tiếp tục với F5)</b>")
    
    def stop_completely(self):
        """Dừng hoàn toàn (reset về đầu)"""
        self.is_running = False
        self.should_stop_completely = True
        self.current_tool = None
        self.current_action_index = 0
        self.loop_cycles_done = 0
        self._stop_emergency_hotkey_monitor()
        # Unlock input if blocked
        if self.executor and hasattr(self.executor, 'mouse_controller'):
            try:
                self.executor.mouse_controller.block_input(False)
            except Exception:
                pass
        self._emit_phase("idle")
        self.signals.log.emit(f"<b style='color:red;'>ĐÃ DỪNG HOÀN TOÀN (reset về đầu)</b>")
    
    def _should_send_timeout_notification(self, tool_name: str) -> bool:
        """Check if timeout notification should be sent (deduplication).
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            True if should send, False if duplicate within 60s
        """
        now = time.time()
        last_sent = self._last_timeout_notification.get(tool_name, 0.0)
        
        # Send if more than 60 seconds since last notification
        if now - last_sent > 60.0:
            self._last_timeout_notification[tool_name] = now
            return True
        
        return False
    
    def _send_timeout_notification(self, tool_name: str, action_name: str):
        """Send Telegram notification for timeout.
        
        Args:
            tool_name: Name of the tool
            action_name: Name of the action that timed out
        """
        try:
            from src.logic.system_executor.telegram_notifier import TelegramNotifier
            
            # Create notifier with log function
            notifier = TelegramNotifier(ui_log_func=lambda msg: self.signals.log.emit(msg))
            
            # Build message
            message = f"⏱️ <b>Timeout</b>\n\nTool: {tool_name}\nAction: {action_name}"
            
            # Send notification
            notifier.send_simple(message)
        except Exception as e:
            # Don't crash tool if notification fails
            try:
                self.signals.log.emit(f"<b style='color:orange;'>[Telegram]</b> Lỗi gửi notification: {e}")
            except Exception:
                pass
    
    def _run(self):
        """Chạy tool trong thread riêng"""
        if not self.current_tool:
            return

        # ---- Run timing stats (per tool run) ----
        def _ms(sec: float) -> float:
            try:
                return float(sec) * 1000.0
            except Exception:
                return 0.0

        tool_name = ""
        try:
            tool_name = str(getattr(self.current_tool, "name", "") or "")
        except Exception:
            tool_name = ""

        run_t0 = time.perf_counter()
        run_reason: str | None = None  # "COMPLETED" | "STOPPED" | "CANCELLED" | None

        total_step_processing_s = 0.0
        total_step_delay_s = 0.0
        total_cycle_pre_delay_s = 0.0
        total_cycle_post_delay_s = 0.0
        cycles_completed = 0

        # Track current cycle
        cycle_no = 0

        def _esc_html(s: str) -> str:
            try:
                return (
                    str(s)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                )
            except Exception:
                return ""

        def _emit_cycle_report(cn: int, lines: list[str]):
            """Emit a per-cycle REPORT section as ONE log entry (avoid interleaving with other logs)."""
            try:
                body = "\n".join([str(x) for x in (lines or []) if x is not None])
            except Exception:
                body = ""

            html = (
                "<div style='background:#0f0f0f;border:1px dashed #777;padding:6px;'>"
                f"<div style='color:#ffffff;font-weight:bold;'>═══════ 📄 REPORT VÒNG {cn} - BẮT ĐẦU 📄 ═══════</div>"
                f"<pre style='margin:6px 0 6px 0;color:#e6e6e6;white-space:pre-wrap;word-break:break-word;'>{_esc_html(body)}</pre>"
                f"<div style='color:#ffffff;font-weight:bold;'>═══════ 📄 REPORT VÒNG {cn} - KẾT THÚC 📄 ═══════</div>"
                "</div>"
            )
            try:
                self.signals.log.emit(html)
            except Exception:
                pass

        def _build_cycle_report_lines(cn: int, step_proc_s: float, step_delay_s: float, pre_s: float, post_s: float, steps_detail):
            """Build per-cycle report lines: totals + per-step breakdown (plain text lines)."""
            out = [
                (
                    f"[Cycle {cn}] Step xử lý: {_ms(step_proc_s):.0f}ms | "
                    f"Delay step: {_ms(step_delay_s):.0f}ms | "
                    f"Delay trước: {_ms(pre_s):.0f}ms | "
                    f"Delay sau: {_ms(post_s):.0f}ms"
                )
            ]
            try:
                for (idx, nm, ps, ds) in (steps_detail or []):
                    out.append(f"[Cycle {cn}] Step {idx}: {nm} | chạy {_ms(ps):.0f}ms | delay {_ms(ds):.0f}ms")
            except Exception:
                pass
            return out

        while self.is_running and not self.should_stop_completely and self.current_tool:
            # Re-read settings each cycle so updates apply immediately on next cycle.
            loop_enabled = bool(getattr(self.current_tool, "loop_enabled", False))
            loop_mode = getattr(self.current_tool, "loop_mode", "forever")
            loop_count = int(getattr(self.current_tool, "loop_count", 1) or 1)
            loop_pre_delay = int(getattr(self.current_tool, "loop_pre_delay_100ms", 0) or 0) / 10.0
            loop_post_delay = int(getattr(self.current_tool, "loop_post_delay_100ms", 0) or 0) / 10.0

            # If cancellation was requested:
            if bool(getattr(self, "cancel_cycle_requested", False)):
                # For non-loop tools: treat as stop completely (safety).
                if not loop_enabled:
                    run_reason = "STOPPED"
                    self.stop_completely()
                    return
                # For loop tools: cancel current cycle and start a new cycle with fresh settings.
                self.cancel_cycle_requested = False
                self.current_action_index = 0
                # don't increment loop_cycles_done
                continue

            # Start of a new cycle
            cycle_no += 1
            
            # Emit cycle_started signal for Status Panel
            try:
                self.signals.cycle_started.emit(cycle_no)
            except Exception:
                pass
            
            cycle_step_processing_s = 0.0
            cycle_step_delay_s = 0.0
            cycle_pre_delay_s = 0.0
            cycle_post_delay_s = 0.0
            cycle_steps_detail: list[tuple[int, str, float, float]] = []  # (idx, name, proc_s, delay_s)

            try:
                self.signals.log.emit(
                    "<div style='background:#1b1b1b;border:1px solid #444;padding:6px;'>"
                    "<div style='width:100%;text-align:left;font-weight:bold;color:#ffffff;'>"
                    f"{'█ '*17}… [VÒNG {cycle_no}] BẮT ĐẦU …{' █'*15}"
                    "</div>"
                    "</div>"
                )
            except Exception:
                pass

            if cycle_no == 1:
                try:
                    self.signals.log.emit(f"<b>[Tool]</b> <b style='color:cyan;'>BẮT ĐẦU TOOL</b>: {tool_name}")
                except Exception:
                    pass
                # Theo yêu cầu: mỗi lần chạy tool (vòng 1) sẽ xóa cache match.
                try:
                    if hasattr(self, "executor") and self.executor:
                        self.executor.clear_last_match_cache()
                except Exception:
                    pass

            # Trễ trước mỗi vòng lặp (kể cả vòng đầu tiên, mặc định = 0)
            # Theo yêu cầu: trễ trước luôn có tác dụng (kể cả không lặp)
            if loop_pre_delay > 0:
                self._emit_phase("delay_cycle_pre")
                _t0 = time.perf_counter()
                ok = self._sleep_interruptible(loop_pre_delay)
                cycle_pre_delay_s += max(0.0, time.perf_counter() - _t0)
                self._emit_phase("idle")
                if not ok:
                    # stop requested
                    if not self.is_running or self.should_stop_completely:
                        # treat as stopped/ended
                        run_reason = run_reason or "STOPPED"
                        return
                    # cancel cycle requested
                    if bool(getattr(self, "cancel_cycle_requested", False)):
                        # handled at top of while
                        continue

            # Chạy tuần tự các action
            for i in range(self.current_action_index, len(self.current_tool.actions)):
                if not self.is_running or self.should_stop_completely:
                    break
                if bool(getattr(self, "cancel_cycle_requested", False)):
                    break

                action = self.current_tool.actions[i]
                self.current_action_index = i
                
                # Build display text with mode suffix for MOUSE_CLICK
                action_display = f"{action.name} - {action.action_type.value}"
                if action.action_type == ActionType.MOUSE_CLICK:
                    if bool(getattr(action, "click_by_coordinate", False)):
                        action_display += " (tọa độ)"
                    else:
                        action_display += " (hình ảnh)"
                
                self.signals.log.emit(f"<b>Step {i+1}/{len(self.current_tool.actions)}:</b> {action_display}")
                
                # Emit action_started signal for Status Panel
                try:
                    self.signals.action_started.emit(i, str(getattr(action, "name", "") or ""))
                except Exception:
                    pass

                # New behavior (no ActionMode): 
                # - KEYBOARD: execute immediately
                # - WAIT: just sleep for timeout duration
                # - MOUSE_CLICK / IMAGE_DETECT: always wait for image using timeout/check_interval
                
                # Check if input blocking is enabled
                block_input_enabled = bool(getattr(self.current_tool, "block_input_enabled", False))
                block_input_duration = float(getattr(self.current_tool, "block_input_duration", 3.0) or 3.0)
                unlock_timer = None
                
                # Check emergency stop before action
                if self._emergency_stop_event.is_set():
                    self.signals.log.emit("<b style='color:red;'>⚠️ Emergency stop: Đã dừng tool do hotkey</b>")
                    # Unlock input
                    if self.executor and hasattr(self.executor, 'mouse_controller'):
                        try:
                            self.executor.mouse_controller.block_input(False)
                        except Exception:
                            pass
                    self.stop_completely()
                    return
                
                if action.action_type == ActionType.KEYBOARD:
                    unlock_timer = None
                    did_block = False
                    try:
                        self._emit_phase("processing")
                        
                        # Step 1: Focus window (KHÔNG block input, để focus thành công)
                        # Focus được thực hiện TRONG execute()
                        
                        # Step 2: Block USER input (nhưng tool vẫn gửi được qua SendInput)
                        if block_input_enabled and self.executor and hasattr(self.executor, 'mouse_controller'):
                            success_block = self.executor.mouse_controller.block_input(True)
                            if success_block:
                                did_block = True
                                block_start_time = time.perf_counter()
                                self.signals.log.emit(f"<b style='color:orange;'>🔒 Đã khóa user input (tool vẫn gửi được)</b>")
                                
                                # Start timer to unlock after duration (backup)
                                def unlock_after_timeout():
                                    try:
                                        self.executor.mouse_controller.block_input(False)
                                        elapsed = time.perf_counter() - block_start_time
                                        self.signals.log.emit(f"<b style='color:green;'>🔓 Đã mở khóa input (timeout {elapsed:.2f}s)</b>")
                                    except Exception:
                                        pass
                                unlock_timer = threading.Timer(block_input_duration, unlock_after_timeout)
                                unlock_timer.daemon = True
                                unlock_timer.start()
                            else:
                                self.signals.log.emit("<b style='color:orange;'>⚠️ Không thể khóa input (cần quyền admin?)</b>")
                        
                        # Step 3: Delay (để chắc chắn đã focus)
                        time.sleep(0.1)
                        
                        # Step 4: Execute action (focus + press key bằng SendInput, không bị block)
                        _t0 = time.perf_counter()
                        success = self.executor.execute(action)
                        step_proc_s = max(0.0, time.perf_counter() - _t0)
                        
                        self._emit_phase("idle")
                        
                    finally:
                        # CRITICAL: LUÔN unlock khi action xong (cancel timer nếu còn)
                        if unlock_timer:
                            unlock_timer.cancel()
                        if did_block and self.executor and hasattr(self.executor, 'mouse_controller'):
                            try:
                                self.executor.mouse_controller.block_input(False)
                                elapsed = time.perf_counter() - block_start_time
                                self.signals.log.emit(f"<b style='color:green;'>🔓 Đã mở khóa input (sau delay {elapsed:.2f}s)</b>")
                            except Exception:
                                pass
                    
                    if bool(getattr(self, "cancel_cycle_requested", False)):
                        break
                    self.signals.log.emit(f"<b style='color:green;'>✓ Thành công</b>" if success else f"<b style='color:red;'>✗ Thất bại</b>")
                    if action.delay and action.delay > 0:
                        self._emit_phase("delay_action")
                    _t1 = time.perf_counter()
                    ok = self._sleep_interruptible(action.delay)
                    step_delay_s = max(0.0, time.perf_counter() - _t1)
                    self._emit_phase("idle")
                    cycle_step_processing_s += step_proc_s
                    cycle_step_delay_s += step_delay_s
                    cycle_steps_detail.append((i + 1, str(getattr(action, "name", "") or ""), step_proc_s, step_delay_s))
                    # Emit action_finished signal for Status Panel
                    try:
                        self.signals.action_finished.emit(i, str(getattr(action, "name", "") or ""), _ms(step_proc_s + step_delay_s))
                    except Exception:
                        pass
                    if not ok:
                        break
                    # Goto step on success
                    if success and bool(getattr(action, "goto_step_enabled", False)):
                        goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                        if goto_idx == 0:
                            # Restart cycle from beginning (with loop_pre_delay)
                            self.signals.log.emit(f"<b style='color:cyan;'>🔄 Restart cycle từ đầu</b>")
                            self.current_action_index = 0
                            break  # break for loop to restart cycle
                        elif 1 <= goto_idx <= len(self.current_tool.actions):
                            # goto_idx is 1-based step number, convert to 0-based array index
                            target_index = goto_idx - 1
                            self.signals.log.emit(f"<b style='color:cyan;'>🔄 Nhảy về Step {goto_idx}</b>")
                            self.current_action_index = target_index
                            break  # break for loop to restart from target_index
                        else:
                            # Invalid goto_idx: out of range
                            self.signals.log.emit(f"<b style='color:orange;'>⚠️ Goto step không hợp lệ: {goto_idx} (phải từ 0-{len(self.current_tool.actions)})</b>")
                elif action.action_type == ActionType.WAIT:
                    # WAIT action: just sleep for timeout duration
                    wait_time = float(getattr(action, "timeout", 1.0) or 1.0)
                    self.signals.log.emit(f"<b style='color:cyan;'>⏳ Đang chờ {wait_time:.1f} giây...</b>")
                    self._emit_phase("processing")
                    _t0 = time.perf_counter()
                    ok = self._sleep_interruptible(wait_time)
                    step_proc_s = max(0.0, time.perf_counter() - _t0)
                    self._emit_phase("idle")
                    cycle_step_processing_s += step_proc_s
                    cycle_steps_detail.append((i + 1, str(getattr(action, "name", "") or ""), step_proc_s, 0.0))
                    # Emit action_finished signal for Status Panel
                    try:
                        self.signals.action_finished.emit(i, str(getattr(action, "name", "") or ""), _ms(step_proc_s))
                    except Exception:
                        pass
                    if not ok:
                        break
                    self.signals.log.emit(f"<b style='color:green;'>✓ Đã chờ xong</b>")
                else:
                    unlock_timer = None
                    did_block = False
                    try:
                        self._emit_phase("processing")
                        
                        # Block input NGAY TRƯỚC execute (only for MOUSE_CLICK and IMAGE_DETECT, NOT for READ_PASSIVE)
                        should_block = (
                            block_input_enabled 
                            and action.action_type in (ActionType.MOUSE_CLICK, ActionType.IMAGE_DETECT)
                            and self.executor 
                            and hasattr(self.executor, 'mouse_controller')
                        )
                        
                        if should_block:
                            success_block = self.executor.mouse_controller.block_input(True)
                            if success_block:
                                did_block = True
                                block_start_time = time.perf_counter()
                                self.signals.log.emit(f"<b style='color:orange;'>🔒 Đã khóa input (tối đa {block_input_duration:.1f}s)</b>")
                                
                                # Wait 100ms after blocking for system to stabilize
                                time.sleep(0.1)
                                
                                # Start timer to unlock after duration (backup)
                                def unlock_after_timeout():
                                    try:
                                        self.executor.mouse_controller.block_input(False)
                                        elapsed = time.perf_counter() - block_start_time
                                        self.signals.log.emit(f"<b style='color:green;'>🔓 Đã mở khóa input (timeout {elapsed:.2f}s)</b>")
                                    except Exception:
                                        pass
                                unlock_timer = threading.Timer(block_input_duration, unlock_after_timeout)
                                unlock_timer.daemon = True
                                unlock_timer.start()
                            else:
                                self.signals.log.emit("<b style='color:orange;'>⚠️ Không thể khóa input (cần quyền admin?)</b>")
                        
                        # Execute action
                        timeout = float(getattr(action, "timeout", 30.0) or 30.0)
                        _t0 = time.perf_counter()
                        success = self.executor.execute_with_timeout(action, timeout=timeout)
                        step_proc_s = max(0.0, time.perf_counter() - _t0)
                        self._emit_phase("idle")
                        
                    finally:
                        # CRITICAL: LUÔN unlock khi action xong (cancel timer nếu còn)
                        if unlock_timer:
                            unlock_timer.cancel()
                        if did_block and self.executor and hasattr(self.executor, 'mouse_controller'):
                            try:
                                self.executor.mouse_controller.block_input(False)
                                elapsed = time.perf_counter() - block_start_time
                                self.signals.log.emit(f"<b style='color:green;'>🔓 Đã mở khóa input (action xong {elapsed:.2f}s)</b>")
                            except Exception:
                                pass
                    
                    # None = cancelled (settings update)
                    if success is None:
                        break
                    if bool(getattr(self, "cancel_cycle_requested", False)):
                        break
                    if success:
                        self.signals.log.emit(f"<b style='color:green;'>✓ Đã tìm thấy ảnh</b>")
                        if action.delay and action.delay > 0:
                            self._emit_phase("delay_action")
                        _t1 = time.perf_counter()
                        ok = self._sleep_interruptible(action.delay)
                        step_delay_s = max(0.0, time.perf_counter() - _t1)
                        self._emit_phase("idle")
                        cycle_step_processing_s += step_proc_s
                        cycle_step_delay_s += step_delay_s
                        cycle_steps_detail.append((i + 1, str(getattr(action, "name", "") or ""), step_proc_s, step_delay_s))
                        # Emit action_finished signal for Status Panel
                        try:
                            self.signals.action_finished.emit(i, str(getattr(action, "name", "") or ""), _ms(step_proc_s + step_delay_s))
                        except Exception:
                            pass
                        if not ok:
                            break
                        # Goto step on success
                        if bool(getattr(action, "goto_step_enabled", False)):
                            goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                            if goto_idx == 0:
                                # Restart cycle from beginning (with loop_pre_delay)
                                self.signals.log.emit(f"<b style='color:cyan;'>🔄 Restart cycle từ đầu</b>")
                                self.current_action_index = 0
                                break  # break for loop to restart cycle
                            elif 1 <= goto_idx <= len(self.current_tool.actions):
                                # goto_idx is 1-based step number, convert to 0-based array index
                                target_index = goto_idx - 1
                                self.signals.log.emit(f"<b style='color:cyan;'>🔄 Nhảy về Step {goto_idx}</b>")
                                self.current_action_index = target_index
                                break  # break for loop to restart from target_index
                            else:
                                # Invalid goto_idx: out of range
                                self.signals.log.emit(f"<b style='color:orange;'>⚠️ Goto step không hợp lệ: {goto_idx} (phải từ 0-{len(self.current_tool.actions)})</b>")
                    else:
                        # Add failure step into the cycle report (even on timeout)
                        step_delay_s = 0.0
                        cycle_step_processing_s += step_proc_s
                        cycle_steps_detail.append((i + 1, str(getattr(action, "name", "") or ""), step_proc_s, step_delay_s))

                        # Diagnostics: best_score/threshold/... from executor (log only on TIMEOUT per request)
                        diag = None
                        try:
                            diag = self.executor.get_last_wait_diagnostics() if self.executor else None
                        except Exception:
                            diag = None

                        if diag:
                            try:
                                bs = float(diag.get("best_score", 0.0))
                                th = float(diag.get("threshold", 0.0))
                                self.signals.log.emit(
                                    "<b style='color:red;'>✗ TIMEOUT</b> "
                                    f"(Cycle {cycle_no}, Step {i+1}: {action.name}) "
                                    f"best_score={bs:.3f}, threshold={th:.3f}"
                                )
                            except Exception:
                                self.signals.log.emit(
                                    f"<b style='color:red;'>✗ TIMEOUT: Không tìm thấy ảnh sau {timeout} giây</b>"
                                )
                        else:
                            self.signals.log.emit(f"<b style='color:red;'>✗ TIMEOUT: Không tìm thấy ảnh sau {timeout} giây</b>")

                        # Theo yêu cầu: nếu step fail/timeout thì xóa cache match để vòng sau bắt buộc detect lại
                        try:
                            if hasattr(self, "executor") and self.executor:
                                self.executor.clear_last_match_cache()
                        except Exception:
                            pass

                        # Action-level override: nếu bật, bỏ qua step này và chạy step sau
                        if bool(getattr(action, "continue_on_timeout", False)):
                            self.signals.log.emit("<b style='color:orange;'>Timeout → bỏ qua step này và làm tiếp step sau</b>")
                            if action.delay and action.delay > 0:
                                self._emit_phase("delay_action")
                            _t1 = time.perf_counter()
                            ok = self._sleep_interruptible(action.delay)
                            step_delay_s = max(0.0, time.perf_counter() - _t1)
                            self._emit_phase("idle")
                            cycle_step_processing_s += step_proc_s
                            cycle_step_delay_s += step_delay_s
                            cycle_steps_detail.append((i + 1, str(getattr(action, "name", "") or ""), step_proc_s, step_delay_s))
                            if not ok:
                                break
                            continue
                        
                        # Timeout goto step: nhảy về step cụ thể khi timeout
                        if bool(getattr(action, "timeout_goto_enabled", False)):
                            timeout_goto_idx = int(getattr(action, "timeout_goto_step_index", 0) or 0)
                            if timeout_goto_idx == 0:
                                # Restart cycle from beginning (with loop_pre_delay)
                                self.signals.log.emit(f"<b style='color:orange;'>Timeout → Restart cycle từ đầu</b>")
                                self.current_action_index = 0
                                break  # break for loop to restart cycle
                            elif 1 <= timeout_goto_idx <= len(self.current_tool.actions):
                                # timeout_goto_idx is 1-based step number, convert to 0-based array index
                                target_index = timeout_goto_idx - 1
                                self.signals.log.emit(f"<b style='color:orange;'>Timeout → nhảy về Step {timeout_goto_idx}</b>")
                                self.current_action_index = target_index
                                break  # break for loop to restart from target_index
                            else:
                                # Invalid timeout_goto_idx: out of range
                                self.signals.log.emit(f"<b style='color:orange;'>⚠️ Timeout goto step không hợp lệ: {timeout_goto_idx} (phải từ 0-{len(self.current_tool.actions)})</b>")

                        restart_on_timeout = bool(getattr(self.current_tool, "restart_on_timeout", False))

                        if restart_on_timeout:
                            self.signals.log.emit("<b style='color:orange;'>Timeout → chạy lại từ đầu (reset về step 1)</b>")
                            # Emit partial REPORT for this cycle (include error details)
                            try:
                                lines = _build_cycle_report_lines(
                                    cycle_no,
                                    cycle_step_processing_s,
                                    cycle_step_delay_s,
                                    cycle_pre_delay_s,
                                    cycle_post_delay_s,
                                    cycle_steps_detail,
                                )
                                try:
                                    if diag:
                                        lines.append(
                                            f"[Cycle {cycle_no}] TIMEOUT tại Step {i+1}: {action.name} | "
                                            f"best_score={float(diag.get('best_score', 0.0)):.3f} "
                                            f"(threshold={float(diag.get('threshold', 0.0)):.3f})"
                                        )
                                except Exception:
                                    pass
                                _emit_cycle_report(cycle_no, lines)
                            except Exception:
                                pass
                            # Reset về step 1 và chạy lại từ đầu (giữ is_running=True)
                            self.current_action_index = 0
                            # Thoát vòng for để quay lại while loop bên ngoài (loop/restart)
                            break

                        # Default behavior: STOP COMPLETELY (not pause)
                        # BUG FIX: Timeout should stop completely by default, not pause
                        self.signals.log.emit(f"<b style='color:red;'>Tool đã dừng hoàn toàn do TIMEOUT.</b>")
                        
                        # Send Telegram notification if enabled
                        if bool(getattr(self.current_tool, "notify_on_timeout", False)):
                            if self._should_send_timeout_notification(self.current_tool.name):
                                self._send_timeout_notification(self.current_tool.name, action.name)
                        
                        # Emit action_finished to clear process tracking timer
                        try:
                            self.signals.action_finished.emit(i, str(getattr(action, "name", "") or ""), _ms(step_proc_s))
                        except Exception:
                            pass
                        self.stop_completely()
                        return

            # If cancellation was requested mid-cycle, reset and continue to next cycle (only if loop enabled)
            if bool(getattr(self, "cancel_cycle_requested", False)):
                loop_enabled = bool(getattr(self.current_tool, "loop_enabled", False))
                if not loop_enabled:
                    run_reason = "STOPPED"
                    self.stop_completely()
                    return
                self.cancel_cycle_requested = False
                self.current_action_index = 0
                continue

            if not self.is_running or self.should_stop_completely:
                break

            # Nếu vừa timeout và restart_on_timeout, current_action_index đã reset về 0 trong loop for.
            # Hoặc nếu vừa goto step, current_action_index đã set về goto_idx.
            # Trường hợp này: bỏ qua phần "kết thúc 1 vòng" và bắt đầu lại từ current_action_index.
            # Check: nếu current_action_index != i (có jump xảy ra) hoặc chưa chạy đến action cuối
            if self.current_action_index != i or i < len(self.current_tool.actions) - 1:
                # Có goto, restart, hoặc chưa hết vòng
                continue

            # Hết 1 vòng tool (chạy đến action cuối mà không có goto/restart)
            self.loop_cycles_done += 1
            self.current_action_index = 0
            cycles_completed += 1

            if not loop_enabled:
                # Theo yêu cầu: trễ sau luôn có tác dụng (kể cả không lặp)
                if loop_post_delay > 0:
                    self._emit_phase("delay_cycle_post")
                    _t0 = time.perf_counter()
                    ok = self._sleep_interruptible(loop_post_delay)
                    cycle_post_delay_s += max(0.0, time.perf_counter() - _t0)
                    self._emit_phase("idle")
                    if not ok:
                        return
                # Aggregate totals
                total_step_processing_s += cycle_step_processing_s
                total_step_delay_s += cycle_step_delay_s
                total_cycle_pre_delay_s += cycle_pre_delay_s
                total_cycle_post_delay_s += cycle_post_delay_s

                try:
                    self.signals.log.emit(
                        "<div style='background:#1b1b1b;border:1px solid #444;padding:6px;'>"
                        "<div style='width:100%;text-align:left;font-weight:bold;color:#69f0ae;'>"
                        f"{'■ '*17}[VÒNG {cycle_no}] KẾT THÚC{' ■'*15}"
                        "</div>"
                        "</div>"
                    )
                    self.signals.log.emit(
                        f"<span style='color:gray;'>[Cycle {cycle_no}]</span> "
                        f"Step xử lý: <b>{_ms(cycle_step_processing_s):.0f}ms</b> | "
                        f"Delay step: <b>{_ms(cycle_step_delay_s):.0f}ms</b> | "
                        f"Delay trước: <b>{_ms(cycle_pre_delay_s):.0f}ms</b> | "
                        f"Delay sau: <b>{_ms(cycle_post_delay_s):.0f}ms</b>"
                    )
                    for (idx, nm, ps, ds) in cycle_steps_detail:
                        self.signals.log.emit(
                            f"<span style='color:gray;'>[Cycle {cycle_no}]</span> "
                            f"Step {idx}: <code>{nm}</code> | xử lý {_ms(ps):.0f}ms | delay {_ms(ds):.0f}ms"
                        )
                except Exception:
                    pass

                # Tool end summary
                try:
                    # Report per-cycle (no FINAL REPORT as requested)
                    report_lines = _build_cycle_report_lines(
                        cycle_no,
                        cycle_step_processing_s,
                        cycle_step_delay_s,
                        cycle_pre_delay_s,
                        cycle_post_delay_s,
                        cycle_steps_detail,
                    )
                    _emit_cycle_report(cycle_no, report_lines)
                except Exception:
                    pass

                self.signals.log.emit("<b style='color:green;'>✓ ĐÃ HOÀN THÀNH TẤT CẢ CÁC BƯỚC</b>")
                self.signals.log.emit("<b style='color:green;'>DỪNG TOOL</b>")
                self.stop_completely()
                return

            if loop_mode == "count" and self.loop_cycles_done >= loop_count:
                # Aggregate totals before stopping (no post-delay when stop on count)
                total_step_processing_s += cycle_step_processing_s
                total_step_delay_s += cycle_step_delay_s
                total_cycle_pre_delay_s += cycle_pre_delay_s
                total_cycle_post_delay_s += cycle_post_delay_s
                try:
                    self.signals.log.emit(
                        "<div style='background:#1b1b1b;border:1px solid #444;padding:6px;'>"
                        "<div style='width:100%;text-align:left;font-weight:bold;color:#69f0ae;'>"
                        f"{'■ '*17}[VÒNG {cycle_no}] KẾT THÚC{' ■'*15}"
                        "</div>"
                        "</div>"
                    )
                    self.signals.log.emit(
                        f"<span style='color:gray;'>[Cycle {cycle_no}]</span> "
                        f"Step xử lý: <b>{_ms(cycle_step_processing_s):.0f}ms</b> | "
                        f"Delay step: <b>{_ms(cycle_step_delay_s):.0f}ms</b> | "
                        f"Delay trước: <b>{_ms(cycle_pre_delay_s):.0f}ms</b> | "
                        f"Delay sau: <b>{_ms(cycle_post_delay_s):.0f}ms</b>"
                    )
                except Exception:
                    pass
                self.signals.log.emit(f"<b style='color:green;'>✓ ĐÃ LẶP ĐỦ {loop_count} LẦN</b>")
                self.signals.log.emit("<b style='color:green;'>DỪNG TOOL</b>")
                try:
                    report_lines = _build_cycle_report_lines(
                        cycle_no,
                        cycle_step_processing_s,
                        cycle_step_delay_s,
                        cycle_pre_delay_s,
                        cycle_post_delay_s,
                        cycle_steps_detail,
                    )
                    _emit_cycle_report(cycle_no, report_lines)
                except Exception:
                    pass
                self.stop_completely()
                return

            # Trễ sau mỗi vòng lặp (chỉ khi còn tiếp tục lặp)
            if loop_post_delay > 0:
                self._emit_phase("delay_cycle_post")
                _t0 = time.perf_counter()
                ok = self._sleep_interruptible(loop_post_delay)
                cycle_post_delay_s += max(0.0, time.perf_counter() - _t0)
                self._emit_phase("idle")
                if not ok:
                    return

            # Aggregate totals for a completed cycle
            total_step_processing_s += cycle_step_processing_s
            total_step_delay_s += cycle_step_delay_s
            total_cycle_pre_delay_s += cycle_pre_delay_s
            total_cycle_post_delay_s += cycle_post_delay_s
            try:
                self.signals.log.emit(
                    "<div style='background:#1b1b1b;border:1px solid #444;padding:6px;'>"
                    "<div style='width:100%;text-align:left;font-weight:bold;color:#69f0ae;'>"
                    f"{'■ '*17}[VÒNG {cycle_no}] KẾT THÚC{' ■'*15}"
                    "</div>"
                    "</div>"
                )
                self.signals.log.emit(
                    f"<span style='color:gray;'>[Cycle {cycle_no}]</span> "
                    f"Step xử lý: <b>{_ms(cycle_step_processing_s):.0f}ms</b> | "
                    f"Delay step: <b>{_ms(cycle_step_delay_s):.0f}ms</b> | "
                    f"Delay trước: <b>{_ms(cycle_pre_delay_s):.0f}ms</b> | "
                    f"Delay sau: <b>{_ms(cycle_post_delay_s):.0f}ms</b>"
                )
            except Exception:
                pass

            # Per-cycle REPORT block (always emitted on cycle end)
            try:
                report_lines = _build_cycle_report_lines(
                    cycle_no,
                    cycle_step_processing_s,
                    cycle_step_delay_s,
                    cycle_pre_delay_s,
                    cycle_post_delay_s,
                    cycle_steps_detail,
                )
                _emit_cycle_report(cycle_no, report_lines)
            except Exception:
                pass

            # Reload tool settings for next cycle
            if self.tool_manager and self.current_tool:
                try:
                    # Always reload by tool ID (UUID), not display name
                    reloaded_tool = self.tool_manager.load_tool(self.current_tool.id)
                    if reloaded_tool:
                        self.current_tool = reloaded_tool
                except Exception:
                    pass

            # Loop forever (hoặc chưa đủ count)
            self.signals.log.emit(f"<span style='color:gray;'>[Loop]</span> Đang lặp lại... (đã xong {self.loop_cycles_done} vòng)")

# --- 3. PRESENTATION LAYER (UI) ---
class BotSignals(QObject):
    log = pyqtSignal(str)
    tool_log = pyqtSignal(str, str)  # (tool_name, html_msg)
    global_esc = pyqtSignal()
    global_stop_all = pyqtSignal()

class ToolSignals(QObject):
    log = pyqtSignal(str)
    phase = pyqtSignal(str)  # "processing" | "delay" | "idle"
    action_started = pyqtSignal(int, str)  # (action_index, action_name)
    action_finished = pyqtSignal(int, str, float)  # (action_index, action_name, elapsed_ms)
    cycle_started = pyqtSignal(int)  # cycle_number


class RunningLockDialog(QDialog):
    """Dialog thông báo 'đang chạy tool'. ESC / X / nút Tắt => dừng hoàn toàn."""

    request_stop = pyqtSignal()

    def __init__(self, tool_name: str, parent=None):
        super().__init__(parent)
        self._ignore_close_request = False
        self._tool_name = tool_name

        self.setWindowTitle("Đang chạy tool")
        self.setFixedSize(380, 150)
        # IMPORTANT: Don't steal focus. Otherwise bot key/click can go to this dialog instead of the game window.
        try:
            self.setWindowModality(Qt.WindowModality.NonModal)
        except Exception:
            pass
        try:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        except Exception:
            pass
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        except Exception:
            pass
        try:
            self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        except Exception:
            pass

        layout = QVBoxLayout()
        title = QLabel(f"<b>Đang chạy:</b> {tool_name}")
        hint = QLabel("Nhấn <b>ESC</b> hoặc bấm <b>X</b> / <b>Tắt</b> để dừng hoàn toàn.")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        stop_btn = QPushButton("Tắt")
        stop_btn.clicked.connect(self._emit_stop_and_close)
        btn_row.addWidget(stop_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def close_silently(self):
        """Close without requesting stop (used when tool stops by itself)."""
        self._ignore_close_request = True
        try:
            self.close()
        finally:
            self._ignore_close_request = False

    def ensure_topmost_no_activate(self):
        """Force TOPMOST without stealing focus (Windows only)."""
        try:
            hwnd = int(self.winId())
        except Exception:
            return
        try:
            user32 = ctypes.windll.user32
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOACTIVATE = 0x0010
            SWP_SHOWWINDOW = 0x0040
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)
        except Exception:
            pass

    def _emit_stop_and_close(self):
        try:
            self.request_stop.emit()
        except Exception:
            pass
        self.close()

    def keyPressEvent(self, event):
        try:
            if event.key() == Qt.Key.Key_Escape:
                self._emit_stop_and_close()
                return
        except Exception:
            pass
        return super().keyPressEvent(event)

    def closeEvent(self, event):
        if not self._ignore_close_request:
            try:
                self.request_stop.emit()
            except Exception:
                pass
        return super().closeEvent(event)

class ToolRunner:
    """Per-tool runner: owns its own executor + engine thread state."""
    def __init__(self, tool: Tool, tool_name: str, target_window_hwnd: int, on_log_cb, on_phase_cb, tool_manager):
        self.tool = tool
        self.tool_name = tool_name
        self.tool_manager = tool_manager
        self.signals = ToolSignals()
        self.executor = SystemExecutor(target_window_hwnd=target_window_hwnd)
        self.engine = AutoBotEngine(self.signals, self.executor, tool_manager)
        self.executor.engine = self.engine
        # forward logs to main window with tool context (thread-safe via Qt signal)
        self.signals.log.connect(lambda msg: on_log_cb(self.tool_name, msg), Qt.ConnectionType.QueuedConnection)
        self.signals.phase.connect(lambda ph: on_phase_cb(self.tool_name, ph), Qt.ConnectionType.QueuedConnection)
        
        # User input detection settings (per-tool)
        self.user_input_mode = "ignore"  # "ignore" | "pause" | "stop"
        self.pause_duration = 5  # seconds (1-300)
        self.is_paused_by_user = False
        self._pause_timer = None
        
        # User input detector
        self.user_input_detector = None
        self._target_hwnd = target_window_hwnd

    @property
    def is_running(self) -> bool:
        return bool(getattr(self.engine, "is_running", False))

    @property
    def is_stopped(self) -> bool:
        return self.engine.current_tool is None

    def pause(self):
        self.engine.stop()

    def stop(self):
        self._stop_user_input_detector()
        self.engine.stop_completely()
        # Release all modifier keys to prevent stuck keys
        if self.executor:
            try:
                self.executor.release_all_modifier_keys()
            except:
                pass

    def run_or_resume(self, target_window_hwnd: int):
        """Run from start if stopped, otherwise resume from last step (paused)."""
        self.executor.set_target_window(target_window_hwnd)
        self._target_hwnd = target_window_hwnd
        resume = (self.engine.current_tool is not None and self.engine.current_tool.name == self.tool.name)
        
        # Start user input detector if mode is not "ignore"
        if self.user_input_mode != "ignore":
            self._start_user_input_detector()
        
        self.engine.start(self.tool, resume=resume, target_window_hwnd=target_window_hwnd)
    
    def _start_user_input_detector(self):
        """Start user input detector."""
        if self.user_input_detector:
            return
        
        try:
            from src.logic.user_input_detector import UserInputDetector
            self.user_input_detector = UserInputDetector(
                target_hwnd=self._target_hwnd,
                ui_log_func=lambda msg: self.signals.log.emit(msg)
            )
            self.user_input_detector.user_input_detected.connect(
                self._on_user_input_detected,
                Qt.ConnectionType.QueuedConnection
            )
            # Pass detector to executor for set_tool_acting() calls
            self.executor.set_user_input_detector(self.user_input_detector)
            self.user_input_detector.start_listening()
        except Exception as e:
            self.signals.log.emit(f"<b style='color:orange;'>[UserInput]</b> Failed to start detector: {e}")
    
    def _stop_user_input_detector(self):
        """Stop user input detector."""
        if self.user_input_detector:
            try:
                self.user_input_detector.stop_listening()
            except Exception:
                pass
            self.user_input_detector = None
    
    def _on_user_input_detected(self, input_type: str):
        """Handle user input detection.
        
        Args:
            input_type: "mouse" or "keyboard"
        """
        if self.user_input_mode == "ignore":
            return
        
        if not self.is_running:
            return
        
        self.signals.log.emit(f"<b style='color:yellow;'>[UserInput]</b> Detected {input_type} input from user")
        
        if self.user_input_mode == "stop":
            self.signals.log.emit("<b style='color:red;'>[UserInput]</b> Stopping tool due to user input")
            self.stop()
        
        elif self.user_input_mode == "pause":
            if not self.is_paused_by_user:
                self.is_paused_by_user = True
                self.signals.log.emit(f"<b style='color:orange;'>[UserInput]</b> Pausing for {self.pause_duration}s")
                self.pause()
                
                # Start timer to resume
                from PyQt6.QtCore import QTimer
                self._pause_timer = QTimer()
                self._pause_timer.setSingleShot(True)
                self._pause_timer.timeout.connect(self._resume_after_pause)
                self._pause_timer.start(self.pause_duration * 1000)
    
    def _resume_after_pause(self):
        """Resume after user input pause."""
        if self.is_paused_by_user:
            self.is_paused_by_user = False
            self.signals.log.emit("<b style='color:green;'>[UserInput]</b> Resuming after pause")
            self.run_or_resume(self._target_hwnd)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auto Bot")
        self.resize(500, 700)  # Default: only left panel (log hidden)
        
        self.signals = BotSignals()
        # Multi-tool runners (same target window)
        self.runners: dict[str, ToolRunner] = {}
        self._lock_dialogs: dict[str, RunningLockDialog] = {}
        self._last_phase: dict[str, str] = {}
        self._esc_hook_installed = False
        self._global_stop_all_hotkey = None
        self.tool_logs: dict[str, list[str]] = {"ALL": []}
        self.auto_scroll_log = True
        self.signals.tool_log.connect(self._on_tool_log)
        self.signals.global_esc.connect(self._on_global_esc, Qt.ConnectionType.QueuedConnection)
        self.signals.global_stop_all.connect(self._on_global_stop_all, Qt.ConnectionType.QueuedConnection)
        
        self.target_window_hwnd = None
        self.window_detector = WindowDetector()
        self.tool_manager = ToolManager()
        self._app_state_path = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "app_state.json")
        self._loading_tool_settings = False
        
        self.create_toolbar()
        self.stacked_widget = QStackedWidget()
        self.home_widget = self.create_home_widget()
        self.stacked_widget.addWidget(self.home_widget)
        self.hotkey_widget = self.create_hotkey_widget()
        self.stacked_widget.addWidget(self.hotkey_widget)
        self.gemini_widget = self.create_gemini_widget()
        self.stacked_widget.addWidget(self.gemini_widget)
        self.teaching_lab_widget = TeachingAlgorithmLabWidget()
        self.stacked_widget.addWidget(self.teaching_lab_widget)
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.setCurrentIndex(0)  # Default to Home

        # Make the selected AI provider credentials available to runtime actions.
        try:
            provider = self._get_saved_ai_provider()
            k = self._get_saved_ai_key(provider)
            if k:
                os.environ[f"{provider.upper()}_API_KEY"] = k
            os.environ["AI_PROVIDER"] = provider
        except Exception:
            pass
        try:
            m = self._get_saved_ai_model(provider)
            if m:
                os.environ["AI_MODEL_NAME"] = m
        except Exception:
            pass

        # Restore last selected tool (after UI + combos exist)
        self._restore_last_selected_tool()
        
        # Restore window size from app_state
        self._restore_window_size()

        self._register_close_all_dialogs_shortcut()
        self._register_global_stop_all_hotkey()
        
        # NOTE: Removed global hotkeys (F5/F6/F7/F8) because we support multi-tool running now.

    def _register_close_all_dialogs_shortcut(self):
        """Register app-wide shortcut handling to close all dialogs/windows except the main window."""
        self.close_all_dialogs_action = QAction("Close All Dialogs", self)
        self.close_all_dialogs_action.setShortcut(QKeySequence("Ctrl+Shift+W"))
        self.close_all_dialogs_action.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        self.close_all_dialogs_action.triggered.connect(self._close_all_dialogs_shortcut_triggered)
        self.addAction(self.close_all_dialogs_action)
        try:
            app = QApplication.instance()
            if app:
                app.installEventFilter(self)
        except Exception:
            pass

    def eventFilter(self, obj, event):
        """Catch Ctrl+Shift+W globally, including inside modal dialogs opened with exec()."""
        try:
            if event and event.type() == QEvent.Type.KeyPress:
                key = event.key()
                modifiers = event.modifiers()
                if (
                    key == Qt.Key.Key_W
                    and modifiers == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
                ):
                    self._close_all_dialogs_shortcut_triggered()
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _close_all_dialogs_shortcut_triggered(self):
        """Handle Ctrl+Shift+W shortcut."""
        try:
            self.signals.log.emit("<b>[Ctrl+Shift+W]</b> Close all dialogs/windows")
        except Exception:
            pass
        self.close_all_child_windows()

    def _register_global_stop_all_hotkey(self):
        """Register Ctrl+Shift+F12 as a global emergency stop for all runners."""
        if keyboard is None or self._global_stop_all_hotkey is not None:
            return

        def on_ctrl_shift_f12_pressed():
            self.signals.global_stop_all.emit()

        try:
            self._global_stop_all_hotkey = keyboard.add_hotkey(
                "ctrl+shift+f12",
                on_ctrl_shift_f12_pressed,
                suppress=False,
            )
            self._ui_log_system("<b style='color:gray;'>[Hotkey]</b> Ctrl+Shift+F12 da duoc dang ky")
        except Exception as e:
            self._global_stop_all_hotkey = None
            self._ui_log_system(f"<b style='color:orange;'>[Hotkey]</b> Khong the dang ky Ctrl+Shift+F12: {e}")

    def _unregister_global_stop_all_hotkey(self):
        """Remove the global Ctrl+Shift+F12 hotkey if it was registered."""
        if keyboard is None or self._global_stop_all_hotkey is None:
            return
        try:
            keyboard.remove_hotkey(self._global_stop_all_hotkey)
        except Exception:
            pass
        self._global_stop_all_hotkey = None

    def _stop_all_runners_completely(self) -> int:
        """Stop every active runner and reset it to the beginning."""
        stopped = 0
        for tool_name, runner in list(self.runners.items()):
            if not runner or runner.is_stopped:
                continue
            try:
                runner.stop()
                stopped += 1
            except Exception:
                continue
            self._close_lock_dialog(tool_name, silent=True)
            self._update_runner_row(tool_name)
        return stopped

    def _on_global_stop_all(self):
        """Handle the global Ctrl+Shift+F12 emergency stop."""
        stopped = self._stop_all_runners_completely()
        if stopped > 0:
            self._ui_log_system(
                f"<b style='color:red;'>[Ctrl+Shift+F12]</b> Emergency stop all: da dung hoan toan {stopped} tool"
            )
        else:
            self._ui_log_system(
                "<b style='color:gray;'>[Ctrl+Shift+F12]</b> Khong co tool nao dang hoat dong"
            )

    def _selected_runner_name(self) -> str | None:
        try:
            if not hasattr(self, "running_table"):
                return None
            row = self.running_table.currentRow()
            if row < 0:
                return None
            item = self.running_table.item(row, 0)
            return item.text() if item else None
        except Exception:
            return None

    def _trigger_pause_selected_runner(self):
        name = self._selected_runner_name()
        if not name:
            return
        runner = self.runners.get(name)
        if not runner:
            return
        runner.pause()
        self._update_runner_row(name)

    def _trigger_stop_selected_runner(self):
        name = self._selected_runner_name()
        if not name:
            return
        runner = self.runners.get(name)
        if not runner:
            return
        runner.stop()
        self._update_runner_row(name)
    
    def create_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Home action
        self.home_action = QAction("Home", self)
        self.home_action.setToolTip("Chạy Tool")
        self.home_action.setCheckable(True)
        self.home_action.setChecked(True)
        self.home_action.triggered.connect(lambda: self.on_toolbar_action_clicked(0))
        toolbar.addAction(self.home_action)

        # Game HotKey action
        self.hotkey_action = QAction("Game HotKey", self)
        self.hotkey_action.setToolTip("Cheat-sheet hotkey của game")
        self.hotkey_action.setCheckable(True)
        self.hotkey_action.triggered.connect(lambda: self.on_toolbar_action_clicked(1))
        toolbar.addAction(self.hotkey_action)

        # AI Chat action
        self.gemini_action = QAction("AI Chat", self)
        self.gemini_action.setToolTip("Chat với AI (kéo & thả ảnh để phân tích)")
        self.gemini_action.setCheckable(True)
        self.gemini_action.triggered.connect(lambda: self.on_toolbar_action_clicked(2))
        toolbar.addAction(self.gemini_action)

        # Image Preprocessing Lab action
        self.teaching_lab_action = QAction("Hiệu chỉnh", self)
        self.teaching_lab_action.setToolTip("Tạo teaching image và test thuật toán trên window game")
        self.teaching_lab_action.setCheckable(True)
        self.teaching_lab_action.triggered.connect(lambda: self.on_toolbar_action_clicked(3))
        toolbar.addAction(self.teaching_lab_action)
        
        # Settings menu button (dropdown)
        settings_menu_btn = QToolButton()
        settings_menu_btn.setText("Settings")
        settings_menu_btn.setToolTip("Cài đặt Telegram & AI")
        settings_menu_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        
        # Create menu for settings
        settings_menu = QMenu(settings_menu_btn)
        
        telegram_action = QAction("Telegram Settings", self)
        telegram_action.triggered.connect(self._open_telegram_settings_dialog)
        settings_menu.addAction(telegram_action)
        
        gemini_settings_action = QAction("AI Provider Settings", self)
        gemini_settings_action.triggered.connect(self._open_gemini_settings_dialog)
        settings_menu.addAction(gemini_settings_action)
        
        settings_menu_btn.setMenu(settings_menu)
        toolbar.addWidget(settings_menu_btn)

        # Ensure only one action is checked at a time
        def _set_checked_only(action: QAction):
            try:
                self.home_action.setChecked(action is self.home_action)
                self.hotkey_action.setChecked(action is self.hotkey_action)
                self.gemini_action.setChecked(action is self.gemini_action)
                self.teaching_lab_action.setChecked(action is self.teaching_lab_action)
            except Exception:
                pass

        self.home_action.triggered.connect(lambda: _set_checked_only(self.home_action))
        self.hotkey_action.triggered.connect(lambda: _set_checked_only(self.hotkey_action))
        self.gemini_action.triggered.connect(lambda: _set_checked_only(self.gemini_action))
        self.teaching_lab_action.triggered.connect(lambda: _set_checked_only(self.teaching_lab_action))
    
    def on_toolbar_action_clicked(self, index):
        """Xử lý khi click vào toolbar action"""
        if index == 0:
            self.home_action.setChecked(True)
        elif index == 1:
            self.hotkey_action.setChecked(True)
        elif index == 2:
            self.gemini_action.setChecked(True)
        elif index == 3:
            self.teaching_lab_action.setChecked(True)
        
        # Chuyển màn hình chính.
        self.stacked_widget.setCurrentIndex(index)

        # Nếu về Home thì đóng tất cả các dialog/cửa sổ phụ để tránh lạc UI
        if index == 0:
            self.close_all_child_windows()

    def create_gemini_widget(self):
        """Tạo widget cho màn hình AI Chat."""
        return AIChatWorkspace(
            load_saved_key=self._get_saved_ai_key,
            save_key=self._save_ai_key,
            clear_saved_key=self._clear_saved_ai_key,
            load_saved_model=self._get_saved_ai_model,
            save_model=self._save_ai_model,
            load_saved_provider=self._get_saved_ai_provider,
            save_provider=self._save_ai_provider,
            load_auto_messages_for_target=self._load_ai_auto_messages_for_target,
            save_auto_messages_for_target=self._save_ai_auto_messages_for_target,
            load_event_registrations_for_target=self._load_ai_event_registrations_for_target,
            save_event_registrations_for_target=self._save_ai_event_registrations_for_target,
            load_ai_settings_for_target=self._load_ai_settings_for_target,
            save_ai_settings_for_target=self._save_ai_settings_for_target,
            create_ai_process_controller=self._create_ai_process_controller,
        )

    def _create_ai_process_controller(self, provider: str, api_key: str, model_name: str):
        """Create the event-AI controller with all configured providers."""
        from samples.ai_game_controller.main import create_ai_process_controller

        if provider == "ollama":
            provider_configs = {
                "ollama": {
                    "model_name": model_name or "gemma4:e2b",
                    "base_url": os.environ.get("OLLAMA_BASE_URL", "https://myllm.mcp88.uk/v1"),
                    "cf_access_client_id": os.environ.get("CF_ACCESS_CLIENT_ID", ""),
                    "cf_access_client_secret": os.environ.get("CF_ACCESS_CLIENT_SECRET", ""),
                }
            }
        else:
            provider_configs = {
                provider: {
                    "api_key": api_key,
                    "model_name": model_name,
                }
            }
        controller, _ = create_ai_process_controller(
            provider=provider,
            api_key=api_key,
            model_name=model_name,
            provider_configs=provider_configs,
        )
        return controller
    
    def _open_telegram_settings_dialog(self):
        """Mở dialog cài đặt Telegram."""
        from src.logic.notifications.config_dialog import TelegramConfigDialog
        dialog = TelegramConfigDialog(self)
        dialog.exec()
    
    def _open_gemini_settings_dialog(self):
        """Mở dialog cài đặt AI dùng chung với tab chat."""
        self.gemini_widget._open_settings()

    def _get_saved_ai_provider(self) -> str:
        return str(self._load_app_state().get("ai_provider", "openrouter") or "openrouter").strip().casefold()

    def _save_ai_provider(self, provider: str) -> None:
        provider = str(provider or "openrouter").strip().casefold()
        if provider not in {"openrouter", "gemini", "ollama"}:
            raise ValueError(f"AI provider không hỗ trợ: {provider}")
        state = self._load_app_state()
        state["ai_provider"] = provider
        self._save_app_state(state)
        os.environ["AI_PROVIDER"] = provider

    def _save_ai_auto_messages(self, messages: list[dict]) -> None:
        state = self._load_app_state()
        state["ai_auto_messages"] = messages
        self._save_app_state(state)

    def _load_ai_event_registrations_for_target(self, target: object) -> list[dict]:
        """Load shared event definitions with enablement isolated per target."""
        if target is None:
            return []
        state = self._load_app_state()
        definitions = state.get("ai_event_registrations", [])
        if not isinstance(definitions, list) or not definitions:
            legacy = state.get("ai_event_registrations_by_process", {})
            if isinstance(legacy, dict):
                merged: dict[str, dict] = {}
                for candidate in legacy.values():
                    if isinstance(candidate, list):
                        for item in candidate:
                            if isinstance(item, dict) and item.get("event_id"):
                                merged.setdefault(str(item["event_id"]), dict(item))
                definitions = list(merged.values())
        definitions = [dict(item) for item in definitions if isinstance(item, dict) and item.get("event_id")]
        enabled_by_process = state.get("ai_event_enabled_by_process", {})
        key = self._ai_process_key(target)
        enabled = enabled_by_process.get(key, {}) if isinstance(enabled_by_process, dict) else {}
        result = []
        for item in definitions:
            event_id = str(item["event_id"])
            value = dict(item)
            value["enabled"] = bool(enabled.get(event_id, False)) if isinstance(enabled, dict) else False
            result.append(value)
        return result

    def _save_ai_event_registrations_for_target(self, target: object, events: list[dict]) -> None:
        """Persist shared definitions and only this target's enabled flags."""
        state = self._load_app_state()
        old_definitions = state.get("ai_event_registrations", [])
        old_by_id = {
            str(item.get("event_id")): item for item in old_definitions
            if isinstance(item, dict) and item.get("event_id")
        } if isinstance(old_definitions, list) else {}
        definitions = []
        enabled = {}
        for item in events:
            if not item.get("event_id"):
                continue
            event_id = str(item["event_id"])
            definition = dict(item)
            if event_id in old_by_id:
                definition["enabled"] = bool(old_by_id[event_id].get("enabled", True))
            else:
                definition["enabled"] = bool(item.get("enabled", True))
            definitions.append(definition)
            enabled[event_id] = bool(item.get("enabled", True))
        state["ai_event_registrations"] = definitions
        enabled_by_process = state.setdefault("ai_event_enabled_by_process", {})
        if isinstance(enabled_by_process, dict):
            enabled_by_process[self._ai_process_key(target)] = enabled
        self._save_app_state(state)

    @staticmethod
    def _ai_process_key(target: object) -> str:
        return str(int(getattr(target, "hwnd", 0) or 0))

    def _load_ai_auto_messages_for_target(self, target: object) -> list[dict]:
        state = self._load_app_state()
        definitions = state.get("ai_auto_messages", [])
        schedules = state.get("ai_auto_schedules_by_process", {}).get(self._ai_process_key(target), {})
        legacy_rules = state.get("ai_auto_messages_by_process", {}).get(self._ai_process_key(target), [])
        if not isinstance(definitions, list):
            definitions = []
        if not isinstance(schedules, dict):
            schedules = {}
        if not definitions and isinstance(legacy_rules, list):
            definitions = legacy_rules
            schedules = {str(rule.get("id")): dict(rule) for rule in legacy_rules if isinstance(rule, dict) and rule.get("id")}
        rules = []
        for definition in definitions:
            if not isinstance(definition, dict) or not definition.get("id") or not definition.get("text"):
                continue
            rule_id = str(definition["id"])
            rules.append({"id": rule_id, "text": str(definition["text"]), **dict(schedules.get(rule_id, {}))})
        return rules

    def _save_ai_auto_messages_for_target(self, target: object, messages: list[dict]) -> None:
        state = self._load_app_state()
        state["ai_auto_messages"] = [
            {"id": str(rule.get("id") or ""), "text": str(rule.get("text") or "")}
            for rule in messages if rule.get("id") and rule.get("text")
        ]
        by_process = state.setdefault("ai_auto_schedules_by_process", {})
        by_process[self._ai_process_key(target)] = {
            str(rule["id"]): {
                "enabled": bool(rule.get("enabled", False)),
                "kind": str(rule.get("kind", "interval")),
                "interval_seconds": int(rule.get("interval_seconds", 300)),
                "time": str(rule.get("time", "00:00")),
            }
            for rule in messages if rule.get("id")
        }
        self._save_app_state(state)

    def _load_ai_settings_for_target(self, target: object) -> dict[str, str]:
        state = self._load_app_state()
        settings = state.get("ai_chat_settings_by_process", {}).get(self._ai_process_key(target), {})
        if not isinstance(settings, dict):
            settings = {}
        provider = str(settings.get("provider", self._get_saved_ai_provider()) or "openrouter").strip().casefold()
        model = str(settings.get("model", "") or "").strip()
        if not model:
            model = self._get_saved_ai_model(provider)
        return {"provider": provider, "model": model}

    def _save_ai_settings_for_target(self, target: object, provider: str, model: str) -> None:
        clean_provider = str(provider or "").strip().casefold()
        clean_model = str(model or "").strip()
        if clean_provider not in {"openrouter", "gemini", "ollama"}:
            raise ValueError("Provider của tab AI Chat không hợp lệ")
        state = self._load_app_state()
        by_process = state.setdefault("ai_chat_settings_by_process", {})
        by_process[self._ai_process_key(target)] = {
            "provider": clean_provider,
            "model": clean_model,
        }
        self._save_app_state(state)

    def _get_saved_ai_key(self, provider: str) -> str:
        provider = str(provider or "openrouter").strip().casefold()
        state = self._load_app_state()
        b64 = str(state.get(f"{provider}_api_key_dpapi_b64", "") or "")
        if not b64:
            return ""
        try:
            return unprotect_from_b64(b64)
        except Exception:
            return ""

    def _save_ai_key(self, provider: str, plaintext_key: str) -> None:
        provider = str(provider or "openrouter").strip().casefold()
        key = str(plaintext_key or "").strip()
        if not key:
            return
        state = self._load_app_state()
        state[f"{provider}_api_key_dpapi_b64"] = protect_to_b64(key)
        self._save_app_state(state)
        os.environ[f"{provider.upper()}_API_KEY"] = key

    def _clear_saved_ai_key(self, provider: str) -> None:
        state = self._load_app_state()
        state.pop(f"{str(provider or '').strip().casefold()}_api_key_dpapi_b64", None)
        self._save_app_state(state)

    def _get_saved_ai_model(self, provider: str) -> str:
        provider = str(provider or "openrouter").strip().casefold()
        state = self._load_app_state()
        return str(state.get(f"{provider}_model_name", state.get("ai_model_name", "")) or "")

    def _save_ai_model(self, provider: str, model_name: str) -> None:
        provider = str(provider or "openrouter").strip().casefold()
        model_name = str(model_name or "").strip()
        state = self._load_app_state()
        state_key = f"{provider}_model_name"
        if model_name:
            state[state_key] = model_name
        else:
            state[state_key] = ""
        self._save_app_state(state)
        if provider == self._get_saved_ai_provider():
            if model_name:
                os.environ["AI_MODEL_NAME"] = model_name
            else:
                os.environ.pop("AI_MODEL_NAME", None)

    def _get_saved_gemini_key(self) -> str:
        """Load Gemini API key from app_state.json (DPAPI-protected)."""
        state = self._load_app_state()
        b64 = str(state.get("gemini_api_key_dpapi_b64", "") or "")
        if not b64:
            return ""
        try:
            return unprotect_from_b64(b64)
        except Exception:
            # If decrypt fails (different user/machine), treat as missing.
            return ""

    def _save_gemini_key(self, plaintext_key: str):
        """Save Gemini API key into app_state.json (DPAPI-protected)."""
        if not plaintext_key:
            return
        b64 = protect_to_b64(str(plaintext_key))
        state = self._load_app_state()
        state["gemini_api_key_dpapi_b64"] = b64
        self._save_app_state(state)

    def _clear_saved_gemini_key(self):
        state = self._load_app_state()
        if "gemini_api_key_dpapi_b64" in state:
            try:
                del state["gemini_api_key_dpapi_b64"]
            except Exception:
                state["gemini_api_key_dpapi_b64"] = ""
        self._save_app_state(state)

    def _get_saved_gemini_model(self) -> str:
        state = self._load_app_state()
        try:
            return str(state.get("gemini_model_name", "") or "")
        except Exception:
            return ""

    def _save_gemini_model(self, model_name: str):
        model_name = str(model_name or "").strip()
        if not model_name:
            return
        state = self._load_app_state()
        state["gemini_model_name"] = model_name
        self._save_app_state(state)

    def create_hotkey_widget(self):
        """Tạo widget cho màn hình Game HotKey"""
        widget = QWidget()
        layout = QVBoxLayout()

        title = QLabel("<b>Game HotKey</b>")
        layout.addWidget(title)

        self.hotkey_text = QTextEdit()
        self.hotkey_text.setReadOnly(True)
        self.hotkey_text.setStyleSheet("background: #111; color: #e6e6e6;")
        self.hotkey_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.hotkey_text.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)

        hotkey_content = """==================== MU ONLINE S15 – GAMETHUVN FULL HOTKEY CHEAT-SHEET ====================

A) ĐIỀU KHIỂN CƠ BẢN
- Chuột trái (LMB): đi / chọn mục tiêu / tương tác NPC / nhặt (tùy tình huống)
- Chuột phải (RMB): đánh / dùng skill đang chọn
- Lăn chuột: zoom gần/xa
- Chuột giữa (Wheel click): (một số client) bật/tắt MU Helper
- SPACE: nhặt item dưới đất
- ALT: hiện/ẩn tên item rơi
- ALT + LMB: nhặt/nói chuyện “xuyên” qua quái/người (đỡ bị click nhầm)
- CTRL + LMB: đánh người chơi (PK)
- ALT + RMB lên người chơi: mở menu lệnh/command nhanh

B) SKILL / BÌNH / PHÍM NHANH
- 1 2 3 4 5 6 7 8 9 0 : chọn/dùng skill theo slot
- CTRL + (1–9,0): gán skill vào số (rê chuột lên skill trong danh sách rồi bấm)
- Q / W / E / R: dùng nhanh bình/consumable theo slot (HP/MP/… tùy bạn set)

C) AUTO – GAMETHU (CẮM CHUỘT)
- Z: mở bảng Auto/Helper (chỉnh nhặt, skill, phạm vi, lọc đồ…)
- HOME: bật/tắt Auto
- END: kẹp/giữ chuột phải (giữ đánh)  (bấm 1–2 lần để khóa/mở)

D) MENU SỰ KIỆN – GAMETHU
- S: mở menu sự kiện/hệ thống (Tower / PvP Arena / Boss / Jewel… tùy server đang mở gì)
- SHIFT + S: lệnh party/di chuyển nhóm (dùng khi party có cơ chế “chỉ định Helper”)

E) ẨN HIỂN THỊ / GIẢM LAG
- H: ẩn người chơi (giảm lag khi đông)
- CTRL + F8: ẩn màn hình game (tùy client)

F) CỬA SỔ (UI) NHANH
- C: Character/Stats
- SHIFT + C: thông tin mở rộng (nếu client có)
- I hoặc V: Inventory
- I rồi S: mở Personal Store (shop cá nhân)
- P: danh sách shop cá nhân (Personal Store List)
- K: Gremory Case
- X: Shop (Cash/In-game shop tùy server)
- M: Move/Warp
- T: Quest
- G: Guild
- B: Gens
- F: Friends/Mailbox
- N: Party & Guild Matching
- Y: Muun inventory
- A: Master Skill Tree
- CTRL + A: Enhance/Skill Tree nâng cao (nếu có)
- D: danh sách command/lệnh nhanh
- O: Options
- ESC: System menu
- F1: Help/Guide (nếu client có trang hướng dẫn hotkey)

G) MINI-MAP
- TAB: bật/tắt mini-map
- - / + : thu/phóng kích thước mini-map (tùy client)
- [ / ] : chỉnh độ trong/đậm (opacity) mini-map (tùy client)

H) CHAT / MACRO / EMOJI
- ENTER: mở chat / gửi / đóng
- TAB (khi đang chat): chuyển chat ↔ whisper (tùy client)
- ↑ / ↓ : gọi lại tin nhắn vừa gửi
- F5 / F9 / F10 / F11 / F12: bật/tắt hiển thị các kênh chat (tùy client)
- ALT + 0–9: dùng macro (nếu server/client cho và bạn đã set macro)
- SHIFT + 1 / 2 / 3 / 4: emoji (Gamethu)

I) CAMERA 3D (PHÍM HAY BỊ KHÁC THEO CLIENT)
- Toggle 3D camera: có thể là F6 hoặc F9 hoặc F10 (tùy bản client)
- Reset góc nhìn: thường là F11 (tùy bản client)

J) GHI CHÚ QUAN TRỌNG (ĐỠ BỊ “SAI PHÍM”)
- END ở MU gốc hay là Hunting Log, nhưng Gamethu thường dùng END cho auto/kẹp chuột.
- Một số phím (Camera 3D / MU Helper / mini-map chỉnh opacity) phụ thuộc client server pack.

=========================================================================================="""

        self.hotkey_text.setPlainText(hotkey_content)
        layout.addWidget(self.hotkey_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        copy_btn = QPushButton("Copy")
        copy_btn.setToolTip("Copy toàn bộ nội dung hotkey")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.hotkey_text.toPlainText()))
        btn_row.addWidget(copy_btn)
        layout.addLayout(btn_row)

        widget.setLayout(layout)
        return widget

    def close_all_child_windows(self):
        """Đóng tất cả window/dialog trừ main window.
        Lưu ý: nhiều window đang được tạo với parent=self (ví dụ ToolEditorWindow),
        nên không nằm trong topLevelWidgets(). Vì vậy dùng allWidgets() và isWindow()."""
        app = QApplication.instance()
        if not app:
            return

        def _is_candidate(win: QWidget) -> bool:
            try:
                if win is None or win is self:
                    return False
                if not win.isWindow():
                    return False
                if hasattr(win, "isVisible") and not win.isVisible():
                    return False
                return True
            except Exception:
                return False

        # Pass 1: đóng tất cả QDialog trước (để thoát exec()/modal loop)
        for w in list(app.allWidgets()):
            if not _is_candidate(w):
                continue
            if isinstance(w, QDialog):
                try:
                    self.signals.log.emit(f"<span style='color:gray;'>[F8]</span> Close dialog: {w.windowTitle()}")
                    w.done(0)
                    w.hide()
                    w.deleteLater()
                except Exception:
                    continue

        # Flush events để đảm bảo dialog đã thoát
        try:
            app.processEvents()
        except Exception:
            pass

        # Pass 2: đóng tất cả window còn lại
        for w in list(app.allWidgets()):
            if not _is_candidate(w):
                continue
            try:
                self.signals.log.emit(f"<span style='color:gray;'>[F8]</span> Close window: {w.windowTitle()}")
                w.hide()
                w.close()
                w.deleteLater()
            except Exception:
                continue

        try:
            app.processEvents()
        except Exception:
            pass

    def focus_home_and_close_dialogs(self):
        """Quay về Home và đóng tất cả dialog/cửa sổ phụ."""
        try:
            self.signals.log.emit("<b>[F8]</b> Focus Home + close all dialogs/windows")
        except Exception:
            pass

        try:
            self.stacked_widget.setCurrentIndex(0)
            self.home_action.setChecked(True)
        except Exception:
            pass

        self.close_all_child_windows()

        # Bring main window to front
        try:
            self.showNormal()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass
    
    def create_home_widget(self):
        """Tạo widget cho màn hình Home (chạy tool)"""
        widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Left panel: Tool controls and running list
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Chọn tool
        tool_layout = QHBoxLayout()
        tool_layout.addWidget(QLabel("Chọn tool:"))
        self.tool_combo = QComboBox()
        self.tool_combo.currentIndexChanged.connect(self._on_tool_combo_changed)
        tool_layout.addWidget(self.tool_combo)
        self.create_tool_btn = QPushButton("Tạo Tool")
        self.create_tool_btn.clicked.connect(self.create_tool)
        tool_layout.addWidget(self.create_tool_btn)
        self.edit_tool_btn = QPushButton("Sửa Tool")
        self.edit_tool_btn.clicked.connect(self.edit_tool)
        tool_layout.addWidget(self.edit_tool_btn)
        self.copy_tool_btn = QPushButton("Sao chép Tool")
        self.copy_tool_btn.clicked.connect(self.copy_tool)
        tool_layout.addWidget(self.copy_tool_btn)
        self.delete_tool_btn = QPushButton("Xóa Tool")
        self.delete_tool_btn.clicked.connect(self.delete_tool)
        tool_layout.addWidget(self.delete_tool_btn)
        left_layout.addLayout(tool_layout)

        # Populate tools
        self.refresh_tools()

        # Running tool list (multi-tool)
        running_header = QHBoxLayout()
        running_header.addWidget(QLabel("<b>Danh sách tool đang chạy:</b>"))
        running_header.addStretch()
        self.add_to_running_btn = QPushButton("Add tool")
        self.add_to_running_btn.clicked.connect(self.add_selected_tool_to_running_list)
        running_header.addWidget(self.add_to_running_btn)
        left_layout.addLayout(running_header)

        self.running_table = QTableWidget(0, 8)
        self.running_table.setHorizontalHeaderLabels(["Tool", "Window game", "Trạng thái", "Run/Pause", "Stop", "Setting", "Process", "Remove"])
        self.running_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.running_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.running_table.verticalHeader().setVisible(False)
        self.running_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.running_table.setColumnWidth(0, 150)
        self.running_table.setColumnWidth(1, 230)
        self.running_table.setColumnWidth(2, 90)
        self.running_table.setColumnWidth(3, 70)
        self.running_table.setColumnWidth(4, 50)
        self.running_table.setColumnWidth(5, 60)
        self.running_table.setColumnWidth(6, 60)
        self.running_table.setColumnWidth(7, 60)
        left_layout.addWidget(self.running_table, 1)  # stretch factor 1
        
        # Expand/Collapse button for log panel (at bottom of left panel)
        left_footer = QHBoxLayout()
        left_footer.addStretch()
        self.log_expand_btn = QToolButton()
        self.log_expand_btn.setText("▶")  # Expand log icon (default: collapsed)
        self.log_expand_btn.setToolTip("Mở rộng log panel")
        self.log_expand_btn.clicked.connect(self._toggle_log_panel)
        left_footer.addWidget(self.log_expand_btn)
        left_layout.addLayout(left_footer)
        
        left_panel.setLayout(left_layout)
        left_panel.setMinimumWidth(200)  # Minimum width for left panel
        
        # Track expanded tools and their action rows
        self._expanded_tools: dict[str, bool] = {}
        self._tool_action_rows: dict[str, list[int]] = {}  # tool_name -> list of action row indices
        
        # Timer for updating action elapsed time
        from PyQt6.QtCore import QTimer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status_time)
        self._current_tool_action_times: dict[str, tuple[int, float]] = {}  # tool_name -> (action_index, start_time)

        # Right panel: Log area
        self.log_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("<b>Log:</b>"))

        self.log_filter_combo = QComboBox()
        self.log_filter_combo.addItem("ALL")
        self.log_filter_combo.setMinimumWidth(150)
        try:
            self.log_filter_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        except Exception:
            pass
        self.log_filter_combo.currentTextChanged.connect(self._reload_log_view)
        log_header.addWidget(self.log_filter_combo)

        log_header.addStretch()
        
        self.log_autoscroll_btn = QToolButton()
        self.log_autoscroll_btn.setCheckable(True)
        self.log_autoscroll_btn.setChecked(True)
        self.log_autoscroll_btn.setToolTip("Auto-scroll log mới nhất (bật/tắt)")
        self.log_autoscroll_btn.setText("☑")
        self.log_autoscroll_btn.toggled.connect(self._on_autoscroll_toggled)
        log_header.addWidget(self.log_autoscroll_btn)
        
        # Clear log button
        self.clear_log_btn = QToolButton()
        self.clear_log_btn.setToolTip("Xóa toàn bộ log")
        self.clear_log_btn.setText("🗑")
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        log_header.addWidget(self.clear_log_btn)

        right_layout.addLayout(log_header)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background: #1e1e1e; color: #00ff00;")
        # Wrap line to fit the log panel width (avoid infinite horizontal lines)
        self.log_area.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_area.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        right_layout.addWidget(self.log_area, 1)  # stretch factor 1
        
        self.log_panel.setLayout(right_layout)

        # Use QSplitter to allow resizing between left and right panels
        from PyQt6.QtWidgets import QSplitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(left_panel)
        self.main_splitter.addWidget(self.log_panel)
        self.main_splitter.setSizes([500, 0])  # Initial: log hidden
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)
        
        # Track log panel state (default: collapsed/hidden)
        self._log_panel_collapsed = True
        self._log_panel_last_size = 400
        
        # Hide log panel by default
        self.log_panel.setVisible(False)
        
        main_layout.addWidget(self.main_splitter)

        widget.setLayout(main_layout)
        return widget

    # --- Multi-tool: running list ---
    def _get_game_windows(self):
        try:
            return self.window_detector.find_game_windows()
        except Exception:
            return []

    def _populate_game_window_combo(self, combo: QComboBox, selected_title: str = ""):
        combo.blockSignals(True)
        combo.clear()
        windows = getattr(self, "_game_windows", None)
        if windows is None:
            windows = self._get_game_windows()
            self._game_windows = windows

        combo.addItem("Chọn window game", None)
        for hwnd, title in windows:
            combo.addItem(title, hwnd)

        idx = combo.findText(str(selected_title or ""))
        if idx < 0 and not selected_title and len(windows) == 1:
            idx = 1
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def _runner_window_combo(self, tool_name: str):
        row = self._find_runner_row(tool_name)
        if row < 0:
            return None
        widget = self.running_table.cellWidget(row, 1)
        return widget if isinstance(widget, QComboBox) else None

    def _on_runner_window_changed(self, tool_name: str):
        combo = self._runner_window_combo(tool_name)
        if not combo:
            return
        hwnd = combo.currentData()
        title = combo.currentText() if hwnd else ""
        runner = self.runners.get(tool_name)
        if not runner:
            return
        runner.tool.target_window_title = title
        if hwnd:
            try:
                runner.executor.set_target_window(hwnd)
                runner._target_hwnd = hwnd
            except Exception:
                pass
        try:
            self.tool_manager.save_tool(runner.tool)
        except Exception as e:
            self._ui_log_system(f"<span style='color:red;'>[Window]</span> Save target window failed: {e}")

    def _resolve_runner_window_hwnd(self, tool_name: str):
        combo = self._runner_window_combo(tool_name)
        if combo:
            hwnd = combo.currentData()
            if hwnd:
                return hwnd

        runner = self.runners.get(tool_name)
        selected_title = str(getattr(getattr(runner, "tool", None), "target_window_title", "") or "")
        if selected_title:
            for hwnd, title in self._get_game_windows():
                if title == selected_title:
                    return hwnd
            QMessageBox.warning(self, "Cảnh báo", f"Window game đã lưu không còn tồn tại:\n{selected_title}")
            return None

        QMessageBox.warning(self, "Cảnh báo", f"Chưa chọn window game cho tool: {tool_name}")
        return None

    def add_selected_tool_to_running_list(self):
        tool_name = self.tool_combo.currentText() if hasattr(self, "tool_combo") else ""
        if not tool_name or tool_name == "Chưa có tool nào":
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn tool!")
            return
        if tool_name in self.runners:
            QMessageBox.information(self, "Thông báo", f"Tool '{tool_name}' đã có trong danh sách.")
            return

        # Load tool by display name (tool_name) via ToolManager, which knows mapping name -> ID
        tool = self.tool_manager.get_tool_by_name(tool_name)
        if not tool:
            QMessageBox.warning(self, "Lỗi", f"Không load được tool: {tool_name}")
            return

        # Route tool logs through MainWindow Qt signal to guarantee UI-thread updates
        self.runners[tool_name] = ToolRunner(
            tool,
            tool_name,
            None,
            lambda tn, msg: self.signals.tool_log.emit(tn, msg),
            lambda tn, ph: self._on_tool_phase(tn, ph),
            self.tool_manager,
        )
        
        # Load user input detection settings from tool
        runner = self.runners[tool_name]
        runner.user_input_mode = getattr(tool, "user_input_mode", "ignore") or "ignore"
        runner.pause_duration = getattr(tool, "pause_duration", 5) or 5
        
        # Connect Status Panel signals
        runner.signals.action_started.connect(
            lambda idx, name, tn=tool_name: self._on_action_started(tn, idx, name),
            Qt.ConnectionType.QueuedConnection
        )
        runner.signals.action_finished.connect(
            lambda idx, name, ms, tn=tool_name: self._on_action_finished(tn, idx, name, ms),
            Qt.ConnectionType.QueuedConnection
        )
        runner.signals.cycle_started.connect(
            lambda cn, tn=tool_name: self._on_cycle_started(tn, cn),
            Qt.ConnectionType.QueuedConnection
        )
        
        self.tool_logs.setdefault(tool_name, [])
        # update log filter list
        if self.log_filter_combo.findText(tool_name) < 0:
            self.log_filter_combo.addItem(tool_name)
        self._add_runner_row(tool_name)
        self._ui_log_system(f"<span style='color:gray;'>[Runner]</span> Added: <b>{tool_name}</b>")

    def _add_runner_row(self, tool_name: str):
        row = self.running_table.rowCount()
        self.running_table.insertRow(row)
        self.running_table.setItem(row, 0, QTableWidgetItem(tool_name))
        window_combo = QComboBox()
        runner = self.runners.get(tool_name)
        selected_title = str(getattr(getattr(runner, "tool", None), "target_window_title", "") or "")
        self._populate_game_window_combo(window_combo, selected_title)
        window_combo.currentIndexChanged.connect(lambda _idx, tn=tool_name: self._on_runner_window_changed(tn))
        self.running_table.setCellWidget(row, 1, window_combo)
        self._on_runner_window_changed(tool_name)
        self.running_table.setItem(row, 2, QTableWidgetItem("Stopped"))

        run_btn = QPushButton("Run")
        run_btn.clicked.connect(lambda: self._toggle_run_pause(tool_name))
        self.running_table.setCellWidget(row, 3, run_btn)

        stop_btn = QPushButton("Stop")
        stop_btn.clicked.connect(lambda: self._stop_runner(tool_name))
        self.running_table.setCellWidget(row, 4, stop_btn)

        setting_btn = QPushButton("Setting")
        setting_btn.clicked.connect(lambda: self._open_tool_settings(tool_name))
        self.running_table.setCellWidget(row, 5, setting_btn)

        process_btn = QPushButton("▶")
        process_btn.setToolTip("Xem danh sách action")
        process_btn.clicked.connect(lambda: self._toggle_process_expand(tool_name))
        self.running_table.setCellWidget(row, 6, process_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_runner(tool_name))
        self.running_table.setCellWidget(row, 7, remove_btn)

        self._update_runner_row(tool_name)

    def _find_runner_row(self, tool_name: str) -> int:
        for r in range(self.running_table.rowCount()):
            it = self.running_table.item(r, 0)
            if it and it.text() == tool_name:
                return r
        return -1

    def _update_runner_row(self, tool_name: str):
        row = self._find_runner_row(tool_name)
        if row < 0:
            return
        runner = self.runners.get(tool_name)
        if not runner:
            return
        status_item = self.running_table.item(row, 2)
        if not status_item:
            status_item = QTableWidgetItem("")
            self.running_table.setItem(row, 2, status_item)

        if runner.is_running:
            status_item.setText("Running")
            btn: QPushButton = self.running_table.cellWidget(row, 3)
            if btn:
                btn.setText("Pause")
        else:
            # paused vs stopped
            if runner.is_stopped:
                status_item.setText("Stopped")
            else:
                status_item.setText("Paused")
            btn: QPushButton = self.running_table.cellWidget(row, 3)
            if btn:
                btn.setText("Run")

    def _toggle_run_pause(self, tool_name: str):
        runner = self.runners.get(tool_name)
        if not runner:
            return
        if runner.is_running:
            runner.pause()
            self._close_lock_dialog(tool_name, silent=True)
        else:
            target_hwnd = self._resolve_runner_window_hwnd(tool_name)
            if not target_hwnd:
                return
            runner.run_or_resume(target_hwnd)
            # Mode 3: show immediately (includes delays; first phase may come after pre-delay)
            if self._get_tool_lock_mode(tool_name) == 2:
                dlg = self._ensure_lock_dialog(tool_name)
                try:
                    if not dlg.isVisible():
                        dlg.show()
                except Exception:
                    pass
        self._update_runner_row(tool_name)

    def _stop_runner(self, tool_name: str):
        runner = self.runners.get(tool_name)
        if not runner:
            return
        runner.stop()
        self._close_lock_dialog(tool_name, silent=True)
        self._update_runner_row(tool_name)

    def _remove_runner(self, tool_name: str):
        # Collapse action rows first if expanded
        if self._expanded_tools.get(tool_name, False):
            self._collapse_tool_actions(tool_name)
        
        runner = self.runners.get(tool_name)
        if runner:
            runner.stop()
        self._close_lock_dialog(tool_name, silent=True)
        if tool_name in self.runners:
            del self.runners[tool_name]
        
        # Clean up tracking
        if tool_name in self._expanded_tools:
            del self._expanded_tools[tool_name]
        if tool_name in self._tool_action_rows:
            del self._tool_action_rows[tool_name]
        if tool_name in self._current_tool_action_times:
            del self._current_tool_action_times[tool_name]
        
        row = self._find_runner_row(tool_name)
        if row >= 0:
            self.running_table.removeRow(row)
        
        # Recalculate action rows for remaining expanded tools
        self._recalculate_action_rows()
        
        # keep logs, but remove filter option
        idx = self.log_filter_combo.findText(tool_name)
        if idx >= 0:
            current = self.log_filter_combo.currentText()
            self.log_filter_combo.removeItem(idx)
            if current == tool_name:
                self.log_filter_combo.setCurrentText("ALL")
        self._ui_log_system(f"<span style='color:gray;'>[Runner]</span> Removed: <b>{tool_name}</b>")

    def _open_tool_settings(self, tool_name: str):
        # Find tool by name to get ID
        tool = self.tool_manager.get_tool_by_name(tool_name)
        if not tool:
            QMessageBox.warning(self, "Cảnh báo", f"Không tìm thấy tool: {tool_name}")
            return
        
        dlg = ToolSettingsDialog(tool.id, self.tool_manager, parent=self)
        if dlg.exec():
            # Settings saved to JSON by dialog
            # Reload tool and update runner immediately
            runner = self.runners.get(tool_name)
            if runner:
                reloaded_tool = self.tool_manager.load_tool(tool.id)
                if reloaded_tool:
                    runner.tool = reloaded_tool
                    # Also update current_tool if this runner is running
                    if runner.current_tool and runner.current_tool.name == tool_name:
                        runner.current_tool = reloaded_tool
            self._ui_log_system(
                f"<span style='color:gray;'>[Setting]</span> <b>{tool_name}</b>: đã lưu và áp dụng setting"
            )

    def _install_global_esc_hook(self):
        """Install a global ESC hook (so ESC works even when the game window has focus)."""
        if self._esc_hook_installed:
            return
        if keyboard is None:
            return
        try:
            keyboard.on_press_key("esc", lambda _e: self.signals.global_esc.emit(), suppress=False)
            self._esc_hook_installed = True
        except Exception:
            self._esc_hook_installed = False

    def _on_global_esc(self):
        """Global ESC handler: stop a running tool that is in show-dialog modes."""
        preferred = self._selected_runner_name()
        if preferred:
            r = self.runners.get(preferred)
            if r and r.is_running and self._get_tool_lock_mode(preferred) != 0:
                self._on_lock_dialog_stop(preferred)
                return

        for name, r in list(self.runners.items()):
            try:
                if r and r.is_running and self._get_tool_lock_mode(name) != 0:
                    self._on_lock_dialog_stop(name)
                    return
            except Exception:
                continue

    # --- Running lock dialog (per tool) ---
    def _get_tool_lock_mode(self, tool_name: str) -> int:
        runner = self.runners.get(tool_name)
        if not runner:
            return 0
        try:
            return int(getattr(runner.tool, "run_lock_mode", 0) or 0)
        except Exception:
            return 0

    def _ensure_lock_dialog(self, tool_name: str) -> RunningLockDialog:
        dlg = self._lock_dialogs.get(tool_name)
        if dlg is not None:
            return dlg
        dlg = RunningLockDialog(tool_name, parent=self)
        dlg.request_stop.connect(lambda: self._on_lock_dialog_stop(tool_name))
        self._lock_dialogs[tool_name] = dlg
        self._install_global_esc_hook()
        return dlg

    def _position_lock_dialog_near_target(self, dlg: RunningLockDialog, tool_name: str = None):
        """Place dialog outside the target game window so it doesn't cover bot clicks."""
        try:
            target_hwnd = None
            if tool_name and tool_name in self.runners:
                target_hwnd = getattr(self.runners[tool_name], "_target_hwnd", None)
            if not target_hwnd:
                target_hwnd = self.target_window_hwnd
            if not target_hwnd:
                return
        except Exception:
            return
        if win32gui is None:
            return

        try:
            left, top, right, bottom = win32gui.GetWindowRect(target_hwnd)
        except Exception:
            return

        try:
            dw = int(dlg.width())
            dh = int(dlg.height())
        except Exception:
            dw, dh = 380, 150

        # Virtual screen bounds
        try:
            SM_XVIRTUALSCREEN = 76
            SM_YVIRTUALSCREEN = 77
            SM_CXVIRTUALSCREEN = 78
            SM_CYVIRTUALSCREEN = 79
            vx = ctypes.windll.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
            vy = ctypes.windll.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
            vw = ctypes.windll.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
            vh = ctypes.windll.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        except Exception:
            vx, vy, vw, vh = 0, 0, 1920, 1080

        pad = 10
        # Prefer right side; fallback left
        x = right + pad
        if x + dw > vx + vw:
            x = left - dw - pad
        # Align to top of window; clamp to screen
        y = top
        if y + dh > vy + vh:
            y = (vy + vh) - dh - pad
        if y < vy:
            y = vy + pad
        if x < vx:
            x = vx + pad
        if x + dw > vx + vw:
            x = (vx + vw) - dw - pad

        try:
            dlg.move(int(x), int(y))
        except Exception:
            pass

    def _close_lock_dialog(self, tool_name: str, silent: bool = True):
        dlg = self._lock_dialogs.get(tool_name)
        if not dlg:
            return
        try:
            if silent:
                dlg.close_silently()
            else:
                dlg.close()
        except Exception:
            pass
        try:
            dlg.hide()
        except Exception:
            pass

    def _on_lock_dialog_stop(self, tool_name: str):
        # ESC / X / Tắt => stop completely
        runner = self.runners.get(tool_name)
        if runner:
            runner.stop()
            self._update_runner_row(tool_name)
        # ensure dialog is closed without re-triggering stop
        self._close_lock_dialog(tool_name, silent=True)

    def _on_tool_phase(self, tool_name: str, phase: str):
        """Engine phase callback (queued to UI thread)."""
        self._last_phase[tool_name] = str(phase)

        runner = self.runners.get(tool_name)
        if not runner:
            self._close_lock_dialog(tool_name, silent=True)
            return

        # If tool isn't running, never keep the dialog open.
        if not runner.is_running:
            self._close_lock_dialog(tool_name, silent=True)
            return

        mode = self._get_tool_lock_mode(tool_name)

        # Mode 1: no dialog
        if mode == 0:
            self._close_lock_dialog(tool_name, silent=True)
            return

        # Mode 2 (UI label): show during the whole tool execution, but hide ONLY at cycle pre/post delay.
        if mode == 1:
            if str(phase) in ("delay_cycle_pre", "delay_cycle_post"):
                self._close_lock_dialog(tool_name, silent=True)
                return

            # Any other phase while running -> keep dialog visible
            # (prevents flicker/hide during internal 'idle' between steps)
            dlg = self._ensure_lock_dialog(tool_name)
            try:
                if not dlg.isVisible():
                    dlg.show()
                self._position_lock_dialog_near_target(dlg, tool_name)
                dlg.ensure_topmost_no_activate()
            except Exception:
                pass
            return

        # Mode 3: always show while running (include delays)
        if mode == 2:
            dlg = self._ensure_lock_dialog(tool_name)
            try:
                if not dlg.isVisible():
                    dlg.show()
                self._position_lock_dialog_near_target(dlg, tool_name)
                dlg.ensure_topmost_no_activate()
            except Exception:
                pass
            return

    # --- Shared log viewer ---
    def _on_autoscroll_toggled(self, checked: bool):
        self.auto_scroll_log = bool(checked)
        # Update checkbox-style icon
        try:
            self.log_autoscroll_btn.setText("☑" if checked else "☐")
        except Exception:
            pass
    
    def _on_clear_log(self):
        """Clear all log content."""
        try:
            self.log_area.clear()
        except Exception:
            pass
    
    def _toggle_log_panel(self):
        """Toggle log panel expand/collapse - hide/show completely."""
        BASE_WINDOW_WIDTH = 500  # Base width when log is hidden
        
        if self._log_panel_collapsed:
            # Expand: show log panel and grow window width
            self.log_panel.setVisible(True)
            
            sizes = self.main_splitter.sizes()
            sizes[1] = self._log_panel_last_size
            self.main_splitter.setSizes(sizes)
            
            # Grow window width to base + log panel width
            new_window_width = BASE_WINDOW_WIDTH + self._log_panel_last_size
            self.resize(new_window_width, self.height())
            
            self.log_expand_btn.setText("◀")
            self.log_expand_btn.setToolTip("Thu gọn log panel")
            self._log_panel_collapsed = False
        else:
            # Collapse: hide log panel completely and shrink window width to base
            sizes = self.main_splitter.sizes()
            self._log_panel_last_size = sizes[1]
            
            self.log_panel.setVisible(False)
            
            # Shrink window width back to base width
            self.resize(BASE_WINDOW_WIDTH, self.height())
            
            self.log_expand_btn.setText("▶")
            self.log_expand_btn.setToolTip("Mở rộng log panel")
            self._log_panel_collapsed = True

    def _ui_log_system(self, msg: str):
        """App/system log (not tied to a tool)."""
        self._on_tool_log("ALL", msg)

    def _on_tool_log(self, tool_name: str, msg: str):
        # store per tool + all
        self.tool_logs.setdefault(tool_name, []).append(msg)
        self.tool_logs.setdefault("ALL", []).append(f"<span style='color:gray;'>[{tool_name}]</span> {msg}" if tool_name != "ALL" else msg)

        # Auto refresh runner status (e.g. when tool finishes it will emit "DỪNG TOOL")
        try:
            if tool_name in self.runners:
                self._update_runner_row(tool_name)
        except Exception:
            pass

        # display depending on filter
        current = self.log_filter_combo.currentText() if hasattr(self, "log_filter_combo") else "ALL"
        if current == "ALL":
            self._append_log_to_view(self.tool_logs["ALL"][-1])
        elif current == tool_name:
            self._append_log_to_view(msg)

    def _append_log_to_view(self, msg: str):
        if not hasattr(self, "log_area"):
            return
        # Add timestamp to log message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        msg_with_timestamp = f"<span style='color:gray;'>[{timestamp}]</span> {msg}"
        
        # Limit log to 1000 lines - save to file before clearing
        doc = self.log_area.document()
        if doc.blockCount() > 1000:
            # Save current log to file before clearing
            try:
                log_dir = os.path.join("logs", datetime.now().strftime("%Y%m%d"))
                os.makedirs(log_dir, exist_ok=True)
                log_filename = f"ui_log_{datetime.now().strftime('%H%M%S')}.txt"
                log_filepath = os.path.join(log_dir, log_filename)
                
                # Get all text from log area
                all_text = self.log_area.toPlainText()
                
                # Save to file
                with open(log_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"=== UI Log saved at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    f.write(f"Total lines: {doc.blockCount()}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(all_text)
                
                print(f"[INFO] Saved {doc.blockCount()} log lines to: {log_filepath}")
            except Exception as e:
                print(f"[ERROR] Failed to save log: {e}")
            
            # Remove first 100 lines to avoid frequent trimming
            cursor = self.log_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            for _ in range(100):
                cursor.select(cursor.SelectionType.BlockUnderCursor)
                cursor.removeSelectedText()
                cursor.deleteChar()  # Remove newline
        
        sb = self.log_area.verticalScrollBar()
        prev = sb.value()
        self.log_area.append(msg_with_timestamp)
        if self.auto_scroll_log:
            try:
                self.log_area.moveCursor(self.log_area.textCursor().MoveOperation.End)
                self.log_area.ensureCursorVisible()
            except Exception:
                pass
        else:
            try:
                sb.setValue(prev)
            except Exception:
                pass

    def _reload_log_view(self, _text: str):
        if not hasattr(self, "log_area"):
            return
        selected = self.log_filter_combo.currentText()
        self.log_area.clear()
        for line in self.tool_logs.get(selected, []):
            self.log_area.append(line)

    def _update_loop_ui_visibility(self):
        enabled = bool(self.loop_checkbox.isChecked()) if hasattr(self, "loop_checkbox") else False
        if hasattr(self, "loop_forever_radio"):
            self.loop_forever_radio.setVisible(enabled)
        if hasattr(self, "loop_count_radio"):
            self.loop_count_radio.setVisible(enabled)
        if hasattr(self, "loop_count_spin"):
            self.loop_count_spin.setVisible(enabled and self.loop_count_radio.isChecked())
        if hasattr(self, "loop_pre_delay_spin"):
            self.loop_pre_delay_spin.setVisible(enabled)
        if hasattr(self, "loop_post_delay_spin"):
            self.loop_post_delay_spin.setVisible(enabled)

    def _load_selected_tool_settings(self):
        """Load selected tool settings into UI."""
        # During startup, refresh_tools may run before these widgets exist
        if not hasattr(self, "loop_checkbox"):
            return
        if not hasattr(self, "tool_combo"):
            return
        
        current_index = self.tool_combo.currentIndex()
        tool_id = self.tool_combo.itemData(current_index)
        
        if not tool_id:
            return
        
        tool = self.tool_manager.load_tool(tool_id)
        if not tool:
            return

        self._loading_tool_settings = True
        try:
            self.loop_checkbox.setChecked(bool(getattr(tool, "loop_enabled", False)))
            mode = getattr(tool, "loop_mode", "forever")
            if mode == "count":
                self.loop_count_radio.setChecked(True)
            else:
                self.loop_forever_radio.setChecked(True)
            self.loop_count_spin.setValue(int(getattr(tool, "loop_count", 1) or 1))
            self.loop_pre_delay_spin.setValue(int(getattr(tool, "loop_pre_delay_100ms", 0) or 0))
            self.loop_post_delay_spin.setValue(int(getattr(tool, "loop_post_delay_100ms", 0) or 0))
            self.stop_on_timeout_checkbox.setChecked(bool(getattr(tool, "stop_on_timeout", True)))
            self.restart_on_timeout_checkbox.setChecked(bool(getattr(tool, "restart_on_timeout", False)))
            self._update_loop_ui_visibility()
        finally:
            self._loading_tool_settings = False

    def _save_selected_tool_settings(self):
        """Persist current tool settings into the tool json."""
        current_index = self.tool_combo.currentIndex()
        tool_id = self.tool_combo.itemData(current_index)
        
        if not tool_id:
            return
        
        tool = self.tool_manager.load_tool(tool_id)
        if not tool:
            return

        tool.loop_enabled = bool(self.loop_checkbox.isChecked())
        tool.loop_mode = "count" if self.loop_count_radio.isChecked() else "forever"
        tool.loop_count = int(self.loop_count_spin.value())
        tool.loop_pre_delay_100ms = int(self.loop_pre_delay_spin.value())
        tool.loop_post_delay_100ms = int(self.loop_post_delay_spin.value())
        tool.stop_on_timeout = bool(self.stop_on_timeout_checkbox.isChecked())
        tool.restart_on_timeout = bool(self.restart_on_timeout_checkbox.isChecked())
        if tool.restart_on_timeout:
            tool.stop_on_timeout = False
        self.tool_manager.save_tool(tool)

    def _on_timeout_behavior_toggled(self, _checked: bool):
        """Enforce mutual exclusivity between stop_on_timeout and restart_on_timeout."""
        if getattr(self, "_loading_tool_settings", False):
            return
        # If restart is checked -> stop must be off
        if self.restart_on_timeout_checkbox.isChecked():
            self.stop_on_timeout_checkbox.setChecked(False)
        # If stop is checked -> restart must be off
        if self.stop_on_timeout_checkbox.isChecked():
            self.restart_on_timeout_checkbox.setChecked(False)
        self._save_selected_tool_settings()

    def _on_tool_settings_changed(self, *_args):
        if getattr(self, "_loading_tool_settings", False):
            return
        self._update_loop_ui_visibility()
        self._save_selected_tool_settings()

    def _load_app_state(self) -> dict:
        try:
            if os.path.exists(self._app_state_path):
                with open(self._app_state_path, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    def _save_app_state(self, state: dict):
        try:
            with open(self._app_state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_tool_combo_changed(self, _index: int):
        """Persist last selected tool ID and update button states."""
        try:
            current_index = self.tool_combo.currentIndex()
            tool_id = self.tool_combo.itemData(current_index)
        except Exception:
            return

        # Update copy button state
        has_tool = bool(tool_id and tool_id != "Chưa có tool nào")
        if hasattr(self, 'copy_tool_btn'):
            self.copy_tool_btn.setEnabled(has_tool)

        if not tool_id:
            return

        state = self._load_app_state()
        state["last_tool_id"] = tool_id  # Save ID instead of name
        self._save_app_state(state)
        # Load tool settings every time user selects a tool
        try:
            self._load_selected_tool_settings()
        except Exception:
            pass

    def _restore_last_selected_tool(self):
        """Restore last selected tool if it still exists."""
        state = self._load_app_state()
        last_tool_id = state.get("last_tool_id")
        
        # Fallback: try old format (tool name)
        if not last_tool_id:
            last_tool_name = state.get("last_tool_name")
            if last_tool_name:
                # Find tool by name
                tool = self.tool_manager.get_tool_by_name(last_tool_name)
                if tool:
                    last_tool_id = tool.id
        
        if not last_tool_id:
            return
        
        try:
            # Find combo index by tool ID
            for i in range(self.tool_combo.count()):
                if self.tool_combo.itemData(i) == last_tool_id:
                    self.tool_combo.setCurrentIndex(i)
                    break
        except Exception:
            pass
    
    def _restore_window_size(self):
        """Restore window size from app_state."""
        state = self._load_app_state()
        width = state.get("window_width")
        height = state.get("window_height")
        
        # Only restore height, not width (width is controlled by log panel state)
        # Default width is 500px (log hidden), will expand to 900px when log is shown
        if height:
            try:
                self.resize(500, int(height))  # Always start with base width
            except Exception:
                pass
    
    def _save_window_size(self):
        """Save current window size to app_state."""
        state = self._load_app_state()
        # Only save height (width is controlled by log panel state)
        state["window_height"] = self.height()
        self._save_app_state(state)
    
    def closeEvent(self, event):
        """Save window size before closing and cleanup stuck keys."""
        self._unregister_global_stop_all_hotkey()
        # Release all modifier keys to prevent stuck keys
        for runner in self.runners.values():
            if runner.executor:
                try:
                    runner.executor.release_all_modifier_keys()
                except:
                    pass
        _release_modifier_keys_fast()
        
        self._save_window_size()
        super().closeEvent(event)
    
    def refresh_tools(self):
        """Làm mới danh sách tools"""
        # Tạm thời ngắt kết nối signal để tránh ghi đè last_tool_name
        self.tool_combo.currentIndexChanged.disconnect(self._on_tool_combo_changed)
        
        self.tool_combo.clear()
        tools = self.tool_manager.list_tools()  # Returns [(id, name), ...]
        if not tools:
            self.tool_combo.addItem("Chưa có tool nào")
        else:
            for tool_id, tool_name in tools:
                self.tool_combo.addItem(tool_name, userData=tool_id)  # Store ID in userData
        
        # Kết nối lại signal
        self.tool_combo.currentIndexChanged.connect(self._on_tool_combo_changed)
        
        # Sau khi refresh, thử restore lại tool gần nhất
        self._restore_last_selected_tool()
        # Và load setting của tool hiện tại (nếu UI đã sẵn sàng)
        if hasattr(self, "loop_checkbox"):
            self._load_selected_tool_settings()
        
        # Update copy button state
        if hasattr(self, 'copy_tool_btn'):
            current_index = self.tool_combo.currentIndex()
            tool_id = self.tool_combo.itemData(current_index) if current_index >= 0 else None
            has_tool = bool(tool_id and tool_id != "Chưa có tool nào")
            self.copy_tool_btn.setEnabled(has_tool)
    
    def create_tool(self):
        """Tạo tool mới"""
        editor = ToolEditorWindow(tool_id=None, parent=self, target_window_hwnd=None, main_window=self)
        editor.tool_saved.connect(self.refresh_tools)
        editor.show()
    
    def edit_tool(self):
        """Sửa tool"""
        current_index = self.tool_combo.currentIndex()
        tool_id = self.tool_combo.itemData(current_index)
        
        if not tool_id:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tool để sửa!")
            return
        
        editor = ToolEditorWindow(tool_id=tool_id, parent=self, target_window_hwnd=None, main_window=self)
        editor.tool_saved.connect(self.refresh_tools)
        editor.show()
    
    def delete_tool(self):
        """Xóa tool"""
        current_index = self.tool_combo.currentIndex()
        tool_id = self.tool_combo.itemData(current_index)
        current_text = self.tool_combo.currentText()
        
        if not tool_id or current_text == "Chưa có tool nào":
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tool để xóa!")
            return
        
        reply = QMessageBox.question(self, "Xác nhận", f"Bạn có chắc muốn xóa tool '{current_text}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.tool_manager.delete_tool(tool_id)  # Delete by ID
            self.refresh_tools()
            QMessageBox.information(self, "Thành công", f"Đã xóa tool: {current_text}")
    
    def copy_tool(self):
        """Sao chép tool với tên mới"""
        current_index = self.tool_combo.currentIndex()
        tool_id = self.tool_combo.itemData(current_index)
        current_text = self.tool_combo.currentText()
        
        if not tool_id or current_text == "Chưa có tool nào":
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn tool để sao chép!")
            return
        
        # Import dialog here to avoid circular imports
        from src.ui.tool_copy_dialog import ToolCopyDialog
        
        dialog = ToolCopyDialog(self.tool_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.get_new_name()
            if new_name:
                try:
                    copied_tool = self.tool_manager.copy_tool(tool_id, new_name)
                    self.refresh_tools()
                    
                    # Select the newly copied tool
                    for i in range(self.tool_combo.count()):
                        if self.tool_combo.itemData(i) == copied_tool.id:
                            self.tool_combo.setCurrentIndex(i)
                            break
                    
                    QMessageBox.information(self, "Thành công", f"Đã sao chép tool thành công: {new_name}")
                except Exception as e:
                    QMessageBox.critical(self, "Lỗi", f"Không thể sao chép tool: {str(e)}")
    
    def start_tool(self):
        """Multi-tool: Run/Pause tool theo row đang chọn."""
        name = self._selected_runner_name()
        if not name:
            QMessageBox.information(self, "Thông báo", "Chọn 1 tool trong danh sách đang chạy để Run/Pause.")
            return
        self._toggle_run_pause(name)
    
    def stop_tool(self):
        """Multi-tool: Pause tool theo row đang chọn."""
        self._trigger_pause_selected_runner()
    
    def stop_tool_completely(self):
        """Multi-tool: Stop tool theo row đang chọn."""
        self._trigger_stop_selected_runner()
    
    def _trigger_start(self):
        """Hotkey handler (F5): toggle Run/Pause for selected runner row."""
        self.start_tool()

    def _toggle_status_panel(self):
        """Deprecated - Status Panel is now inline with each tool row."""
        pass

    def _toggle_process_expand(self, tool_name: str):
        """Toggle expand/collapse action list for a tool."""
        is_expanded = self._expanded_tools.get(tool_name, False)
        
        if is_expanded:
            # Collapse: remove action rows
            self._collapse_tool_actions(tool_name)
        else:
            # Expand: insert action rows
            self._expand_tool_actions(tool_name)
        
        # Update button text
        row = self._find_runner_row(tool_name)
        if row >= 0:
            btn = self.running_table.cellWidget(row, 6)
            if btn:
                btn.setText("▼" if not is_expanded else "▶")

    def _expand_tool_actions(self, tool_name: str):
        """Insert action rows below the tool row."""
        runner = self.runners.get(tool_name)
        if not runner or not runner.tool:
            return
        
        tool_row = self._find_runner_row(tool_name)
        if tool_row < 0:
            return
        
        # Insert action rows after tool row
        action_rows = []
        small_font = self.running_table.font()
        small_font.setPointSize(small_font.pointSize() - 1)
        
        for i, action in enumerate(runner.tool.actions):
            insert_row = tool_row + 1 + i
            self.running_table.insertRow(insert_row)
            # Set smaller row height for action rows
            self.running_table.setRowHeight(insert_row, 22)
            
            # Column 0: Action name with indent (smaller font)
            action_text = f"  ↳ {i+1}. {action.name}"
            name_item = QTableWidgetItem(action_text)
            name_item.setForeground(QBrush(QColor("#888888")))
            name_item.setFont(small_font)
            self.running_table.setItem(insert_row, 0, name_item)
            
            # Column 1: Action type (smaller font)
            type_text = f"{action.action_type.value}"
            type_item = QTableWidgetItem(type_text)
            type_item.setForeground(QBrush(QColor("#888888")))
            type_item.setFont(small_font)
            self.running_table.setItem(insert_row, 1, type_item)
            
            # Column 2: Elapsed time (will be updated by timer)
            time_item = QTableWidgetItem("--")
            time_item.setForeground(QBrush(QColor("#888888")))
            time_item.setFont(small_font)
            self.running_table.setItem(insert_row, 2, time_item)
            
            # Empty cells for other columns (3-7)
            for col in range(3, 8):
                empty_item = QTableWidgetItem("")
                self.running_table.setItem(insert_row, col, empty_item)
            
            action_rows.append(insert_row)
        
        self._expanded_tools[tool_name] = True
        self._tool_action_rows[tool_name] = list(range(tool_row + 1, tool_row + 1 + len(runner.tool.actions)))
        
        # Start timer for updating elapsed time
        if not self.status_timer.isActive():
            self.status_timer.start(100)
        
        # Highlight current action if tool is running
        if tool_name in self._current_tool_action_times:
            current_idx, _ = self._current_tool_action_times[tool_name]
            self._on_action_started(tool_name, current_idx, "")

    def _collapse_tool_actions(self, tool_name: str):
        """Remove action rows for a tool."""
        if tool_name not in self._tool_action_rows:
            return
        
        # Remove rows from bottom to top to avoid index shifting
        action_rows = sorted(self._tool_action_rows.get(tool_name, []), reverse=True)
        for row in action_rows:
            if row < self.running_table.rowCount():
                self.running_table.removeRow(row)
        
        self._expanded_tools[tool_name] = False
        self._tool_action_rows[tool_name] = []
        
        # Recalculate action rows for other expanded tools
        self._recalculate_action_rows()

    def _recalculate_action_rows(self):
        """Recalculate action row indices after collapse."""
        for tn in list(self._expanded_tools.keys()):
            if self._expanded_tools.get(tn, False):
                tool_row = self._find_runner_row(tn)
                runner = self.runners.get(tn)
                if tool_row >= 0 and runner and runner.tool:
                    num_actions = len(runner.tool.actions)
                    self._tool_action_rows[tn] = list(range(tool_row + 1, tool_row + 1 + num_actions))

    def _refresh_status_list(self):
        """Deprecated - Status Panel is now inline."""
        pass

    def _update_status_time(self):
        """Update elapsed time for current actions in expanded tools."""
        for tool_name, (action_idx, start_time) in list(self._current_tool_action_times.items()):
            if not self._expanded_tools.get(tool_name, False):
                continue
            
            action_rows = self._tool_action_rows.get(tool_name, [])
            if action_idx < 0 or action_idx >= len(action_rows):
                continue
            
            row = action_rows[action_idx]
            if row >= self.running_table.rowCount():
                continue
            
            # Update elapsed time in column 2
            elapsed = (time.perf_counter() - start_time) * 1000
            time_item = self.running_table.item(row, 2)
            if time_item:
                time_item.setText(f"{elapsed:.0f}ms")

    def _on_action_started(self, tool_name: str, action_index: int, action_name: str):
        """Handle action started signal."""
        self._current_tool_action_times[tool_name] = (action_index, time.perf_counter())
        
        # Highlight current action row if expanded
        if not self._expanded_tools.get(tool_name, False):
            return
        
        action_rows = self._tool_action_rows.get(tool_name, [])
        for i, row in enumerate(action_rows):
            if row >= self.running_table.rowCount():
                continue
            name_item = self.running_table.item(row, 0)
            type_item = self.running_table.item(row, 1)
            time_item = self.running_table.item(row, 2)
            if i == action_index:
                # Highlight current action with green background and white text
                if name_item:
                    name_item.setBackground(QBrush(QColor("#2d5a2d")))
                    name_item.setForeground(QBrush(QColor("#ffffff")))
                if type_item:
                    type_item.setBackground(QBrush(QColor("#2d5a2d")))
                    type_item.setForeground(QBrush(QColor("#ffffff")))
                if time_item:
                    time_item.setBackground(QBrush(QColor("#2d5a2d")))
                    time_item.setForeground(QBrush(QColor("#ffffff")))
            else:
                # Reset other rows
                if name_item:
                    name_item.setBackground(QBrush(QColor("transparent")))
                    name_item.setForeground(QBrush(QColor("#888888")))
                if type_item:
                    type_item.setBackground(QBrush(QColor("transparent")))
                    type_item.setForeground(QBrush(QColor("#888888")))
                if time_item:
                    time_item.setBackground(QBrush(QColor("transparent")))
                    time_item.setForeground(QBrush(QColor("#888888")))

    def _on_action_finished(self, tool_name: str, action_index: int, action_name: str, elapsed_ms: float):
        """Handle action finished signal."""
        # Update elapsed time in table
        if self._expanded_tools.get(tool_name, False):
            action_rows = self._tool_action_rows.get(tool_name, [])
            if action_index < len(action_rows):
                row = action_rows[action_index]
                if row < self.running_table.rowCount():
                    # Update elapsed time in column 2
                    time_item = self.running_table.item(row, 2)
                    if time_item:
                        time_item.setText(f"{elapsed_ms:.0f}ms")
                    
                    # Clear highlight - reset to gray
                    name_item = self.running_table.item(row, 0)
                    type_item = self.running_table.item(row, 1)
                    time_item = self.running_table.item(row, 2)
                    if name_item:
                        name_item.setBackground(QBrush(QColor("transparent")))
                        name_item.setForeground(QBrush(QColor("#888888")))
                    if type_item:
                        type_item.setBackground(QBrush(QColor("transparent")))
                        type_item.setForeground(QBrush(QColor("#888888")))
                    if time_item:
                        time_item.setBackground(QBrush(QColor("transparent")))
                        time_item.setForeground(QBrush(QColor("#888888")))
        
        # Clear from tracking
        if tool_name in self._current_tool_action_times:
            del self._current_tool_action_times[tool_name]

    def _on_cycle_started(self, tool_name: str, cycle_number: int):
        """Handle cycle started signal - reset action times in table."""
        if not self._expanded_tools.get(tool_name, False):
            return
        
        # Reset all action rows
        action_rows = self._tool_action_rows.get(tool_name, [])
        runner = self.runners.get(tool_name)
        if not runner or not runner.tool:
            return
        
        for i, row in enumerate(action_rows):
            if row >= self.running_table.rowCount():
                continue
            if i < len(runner.tool.actions):
                # Reset elapsed time to "--"
                time_item = self.running_table.item(row, 2)
                if time_item:
                    time_item.setText("--")
                    time_item.setBackground(QBrush(QColor("transparent")))
                    time_item.setForeground(QBrush(QColor("#888888")))
                # Reset name column
                name_item = self.running_table.item(row, 0)
                if name_item:
                    name_item.setBackground(QBrush(QColor("transparent")))
                    name_item.setForeground(QBrush(QColor("#888888")))
                # Reset type column
                type_item = self.running_table.item(row, 1)
                if type_item:
                    type_item.setBackground(QBrush(QColor("transparent")))
                    type_item.setForeground(QBrush(QColor("#888888")))

if __name__ == "__main__":
    if "--mcp-notifications-server" in sys.argv:
        from src.ai_control.servers.notifications import run_notifications_mcp_server
        run_notifications_mcp_server()
        raise SystemExit(0)
    import traceback
    import logging
    from datetime import datetime
    
    # Setup logging to file
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"app_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("=" * 80)
    logger.info("Application started")
    logger.info("=" * 80)
    
    # Global exception handler for uncaught exceptions
    def exception_hook(exc_type, exc_value, exc_traceback):
        """Log uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Call default handler for KeyboardInterrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        logger.critical("=" * 80)
        logger.critical("EXCEPTION DETAILS:")
        logger.critical("=" * 80)
        logger.critical(f"Type: {exc_type.__name__}")
        logger.critical(f"Value: {exc_value}")
        logger.critical("Traceback:")
        for line in traceback.format_tb(exc_traceback):
            logger.critical(line.rstrip())
        logger.critical("=" * 80)
    
    # Set the exception hook
    sys.excepthook = exception_hook
    
    # Also catch exceptions in Qt slots
    def qt_exception_hook(exc_type, exc_value, exc_traceback):
        """Log exceptions in Qt slots."""
        logger.error("Exception in Qt slot:", exc_info=(exc_type, exc_value, exc_traceback))
        logger.error("=" * 80)
        logger.error("QT SLOT EXCEPTION:")
        logger.error("=" * 80)
        logger.error(f"Type: {exc_type.__name__}")
        logger.error(f"Value: {exc_value}")
        logger.error("Traceback:")
        for line in traceback.format_tb(exc_traceback):
            logger.error(line.rstrip())
        logger.error("=" * 80)
    
    # Make process DPI-aware so ClientToScreen / SetCursorPos coordinates match captured pixels
    try:
        # Windows 10+: Per-monitor v2 awareness
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        logger.info("DPI awareness set: Per-monitor v2")
    except Exception as e:
        logger.warning(f"Failed to set DPI awareness v2: {e}")
        try:
            # Older fallback
            ctypes.windll.user32.SetProcessDPIAware()
            logger.info("DPI awareness set: Basic")
        except Exception as e2:
            logger.warning(f"Failed to set DPI awareness: {e2}")

    try:
        app = QApplication(sys.argv)
        _release_modifier_keys_fast()

        def _release_modifiers_on_quit():
            _release_modifier_keys_fast()

        app.aboutToQuit.connect(_release_modifiers_on_quit)
        
        # Install Qt message handler to catch Qt warnings/errors
        def qt_message_handler(mode, context, message):
            if mode == 0:  # QtDebugMsg
                logger.debug(f"Qt Debug: {message}")
            elif mode == 1:  # QtWarningMsg
                logger.warning(f"Qt Warning: {message}")
            elif mode == 2:  # QtCriticalMsg
                logger.error(f"Qt Critical: {message}")
            elif mode == 3:  # QtFatalMsg
                logger.critical(f"Qt Fatal: {message}")
        
        # Note: qInstallMessageHandler is not available in PyQt6
        # We'll rely on sys.excepthook instead
        
        logger.info("Creating main window...")
        window = MainWindow()
        logger.info("Showing main window...")
        window.show()
        logger.info("Entering event loop...")
        exit_code = app.exec()
        logger.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Fatal error in main: {e}", exc_info=True)
        sys.exit(1)
