from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
                             QLabel, QLineEdit, QPushButton, QListWidget,
                             QListWidgetItem, QMessageBox, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTextEdit, QAbstractItemView, QComboBox, QFileDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QMetaObject, Q_ARG
from ..logic.action_type import AutoAction, ActionType
from .action_config_dialog import ActionConfigDialog
from ..logic.tool_manager import Tool, ToolManager
import copy
import threading
import time

class _TestEngine:
    """Mock engine for test actions - provides stop flags for SystemExecutor."""
    def __init__(self):
        self.is_running = True
        self.should_stop_completely = False
        self.cancel_cycle_requested = False
    
    def stop(self):
        self.is_running = False
        self.should_stop_completely = True


class ToolEditorWindow(QMainWindow):
    tool_saved = pyqtSignal()  # Signal khi tool được lưu
    test_log = pyqtSignal(str)  # Signal để log kết quả test
    _test_finished = pyqtSignal(int)  # Signal khi test kết thúc (action_index)
    _highlight_action_signal = pyqtSignal(int, bool)  # Signal to highlight action (index, highlight)
    _update_action_time_signal = pyqtSignal(int, float)  # Signal to update action time (index, elapsed_ms)
    _test_log_signal = pyqtSignal(str)  # Signal for thread-safe logging
    
    def __init__(self, tool_id: str = None, parent=None, target_window_hwnd=None, main_window=None):
        super().__init__(parent)
        self.tool_manager = ToolManager()
        self.target_window_hwnd = target_window_hwnd
        self.target_window_title = ""
        self.window_capture_dir = ""
        self.main_window = main_window  # Reference to MainWindow for logging
        self.tool_id = tool_id  # UUID of the tool
        self.tool_name = None  # Will be loaded from tool
        self.actions = []
        self._test_running = False
        self._test_should_stop = False
        self._current_test_index = -1
        self._test_engine = None  # Mock engine for test actions
        self._test_lock = threading.Lock()  # Lock to prevent race conditions
        self._current_test_thread = None  # Track current test thread
        
        # Test all actions variables
        self._test_all_running = False
        self._test_all_should_stop = False
        self._action_times = {}  # {action_index: elapsed_ms}
        self._live_action_time_timer = QTimer(self)
        self._live_action_time_timer.setInterval(100)
        self._live_action_time_timer.timeout.connect(self._refresh_live_action_time)
        self._live_action_index = -1
        self._live_action_started_at = None
        
        # Set window title (will update after loading tool)
        self.setWindowTitle("Tạo Tool Mới")
        self.setFixedSize(750, 500)
        self.init_ui()
        
        # Connect signals for thread-safe UI updates
        self._test_finished.connect(self._on_test_finished)
        self._highlight_action_signal.connect(self._highlight_action)
        self._update_action_time_signal.connect(self._update_action_time)
        self._test_log_signal.connect(self._append_log, Qt.ConnectionType.QueuedConnection)
        
        if tool_id:
            self.load_tool()

    def _sleep_test_all_interruptible(self, seconds: float) -> bool:
        """Sleep in 100ms chunks so Test All can stop during action delay."""
        try:
            seconds = max(0.0, float(seconds or 0.0))
        except Exception:
            seconds = 0.0
        end_time = time.time() + seconds
        while time.time() < end_time:
            if self._test_all_should_stop:
                return False
            if self._test_engine and (
                not getattr(self._test_engine, "is_running", True)
                or getattr(self._test_engine, "should_stop_completely", False)
                or getattr(self._test_engine, "cancel_cycle_requested", False)
            ):
                return False
            remaining = end_time - time.time()
            time.sleep(min(0.1, max(0.0, remaining)))
        return True
    
    def init_ui(self):
        widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Tên tool
        main_layout.addWidget(QLabel("Tên tool:"))
        self.name_input = QLineEdit()
        main_layout.addWidget(self.name_input)
        
        # Use QSplitter for resizable panels
        from PyQt6.QtWidgets import QSplitter
        from PyQt6.QtCore import Qt
        
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top panel: Actions table
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        # Danh sách actions (dùng QTableWidget để có nút test trong mỗi row)
        top_layout.addWidget(QLabel("Danh sách actions:"))
        
        # Total time label
        self.total_time_label = QLabel("Tổng thời gian: --")
        self.total_time_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        top_layout.addWidget(self.total_time_label)
        
        self.actions_table = QTableWidget(0, 4)  # 4 columns: Action, Chạy test, Dừng test, Thời gian
        self.actions_table.setHorizontalHeaderLabels(["Action", "Chạy test", "Dừng test", "Thời gian"])
        self.actions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.actions_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.actions_table.verticalHeader().setVisible(False)
        self.actions_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.actions_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.actions_table.setColumnWidth(1, 80)
        self.actions_table.setColumnWidth(2, 80)
        self.actions_table.setColumnWidth(3, 100)  # Thời gian column
        self.actions_table.itemDoubleClicked.connect(self.edit_action)
        top_layout.addWidget(self.actions_table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        # Edit buttons
        self.add_btn = QPushButton("Thêm Item (Action)")
        self.add_btn.setToolTip("Thêm một action mới vào tool")
        self.add_btn.clicked.connect(self.add_action)
        self.edit_btn = QPushButton("Sửa")
        self.edit_btn.clicked.connect(self.edit_action)
        self.delete_btn = QPushButton("Xóa")
        self.delete_btn.clicked.connect(self.delete_action)
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self.duplicate_action)
        self.move_up_btn = QPushButton("↑ Lên")
        self.move_up_btn.clicked.connect(self.move_action_up)
        self.move_down_btn = QPushButton("↓ Xuống")
        self.move_down_btn.clicked.connect(self.move_action_down)
        
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.duplicate_btn)
        btn_layout.addWidget(self.move_up_btn)
        btn_layout.addWidget(self.move_down_btn)
        
        # Separator
        from PyQt6.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        btn_layout.addWidget(separator)
        
        # Test buttons
        self.test_all_btn = QPushButton("▶ Test Toàn Bộ")
        self.test_all_btn.setToolTip("Chạy test tất cả actions tuần tự")
        self.test_all_btn.clicked.connect(self._test_all_actions)
        self.stop_all_btn = QPushButton("■ Dừng Test")
        self.stop_all_btn.setToolTip("Dừng test toàn bộ")
        self.stop_all_btn.clicked.connect(self._stop_all_tests)
        self.stop_all_btn.setEnabled(False)
        
        btn_layout.addWidget(self.test_all_btn)
        btn_layout.addWidget(self.stop_all_btn)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        btn_layout.addWidget(separator2)
        
        # Save button
        self.save_btn = QPushButton("Lưu")
        self.save_btn.clicked.connect(self.save_tool)
        btn_layout.addWidget(self.save_btn)
        
        top_layout.addLayout(btn_layout)
        
        top_widget.setLayout(top_layout)
        splitter.addWidget(top_widget)
        
        # Bottom panel: Test log
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)

        window_layout = QHBoxLayout()
        window_layout.addWidget(QLabel("Window game:"))
        self.window_combo = QComboBox()
        self.window_combo.setMinimumWidth(320)
        self.refresh_window_btn = QPushButton("Làm mới")
        self.refresh_window_btn.clicked.connect(self.refresh_game_windows)
        self.window_combo.currentIndexChanged.connect(self._on_window_selected)
        window_layout.addWidget(self.window_combo, 1)
        window_layout.addWidget(self.refresh_window_btn)
        bottom_layout.addLayout(window_layout)
        self.refresh_game_windows()

        capture_layout = QHBoxLayout()
        self.capture_window_btn = QPushButton("Capture window game")
        self.capture_window_btn.clicked.connect(self._capture_selected_window)
        self.capture_path_input = QLineEdit()
        self.capture_path_input.setPlaceholderText("Thư mục lưu ảnh capture")
        self.capture_browse_btn = QPushButton("Chọn...")
        self.capture_browse_btn.clicked.connect(self._browse_capture_dir)
        capture_layout.addWidget(self.capture_window_btn)
        capture_layout.addWidget(QLabel("Lưu tại:"))
        capture_layout.addWidget(self.capture_path_input, 1)
        capture_layout.addWidget(self.capture_browse_btn)
        bottom_layout.addLayout(capture_layout)
        
        # Log header with buttons
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("Test Log:"))
        log_header.addStretch()
        
        # Toggle log button
        from PyQt6.QtWidgets import QToolButton
        self.toggle_log_btn = QToolButton()
        self.toggle_log_btn.setToolTip("Ẩn/Hiện log panel")
        self.toggle_log_btn.setText("▼")
        self.toggle_log_btn.clicked.connect(self._toggle_test_log)
        log_header.addWidget(self.toggle_log_btn)
        
        # Clear log button
        self.clear_test_log_btn = QToolButton()
        self.clear_test_log_btn.setToolTip("Xóa toàn bộ log")
        self.clear_test_log_btn.setText("🗑")
        self.clear_test_log_btn.clicked.connect(self._clear_test_log)
        log_header.addWidget(self.clear_test_log_btn)
        
        bottom_layout.addLayout(log_header)
        
        # Log area
        from PyQt6.QtGui import QTextOption
        self.test_log_area = QTextEdit()
        self.test_log_area.setReadOnly(True)
        self.test_log_area.setStyleSheet("background: #1e1e1e; color: #00ff00;")
        self.test_log_area.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.test_log_area.setWordWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        bottom_layout.addWidget(self.test_log_area)
        
        bottom_widget.setLayout(bottom_layout)
        splitter.addWidget(bottom_widget)
        
        # Set initial sizes (70% top, 30% bottom)
        splitter.setSizes([350, 150])
        self._test_log_visible = True
        self._test_log_splitter = splitter  # Save reference for toggle
        self._test_log_last_size = 150  # Save last size for restore
        
        main_layout.addWidget(splitter)
        
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)

    def refresh_game_windows(self):
        """Refresh game windows for this tool editor."""
        selected_title = self.target_window_title or ""
        try:
            current_title = self.window_combo.currentText()
            if current_title and self.window_combo.currentData():
                selected_title = current_title
        except Exception:
            pass

        self.window_combo.blockSignals(True)
        self.window_combo.clear()
        try:
            from ..logic.window_detector import WindowDetector
            windows = WindowDetector.find_game_windows()
        except Exception:
            windows = []

        if not windows:
            self.window_combo.addItem("Không tìm thấy window game", None)
        else:
            self.window_combo.addItem("Chọn window game", None)
            for hwnd, title in windows:
                self.window_combo.addItem(title, hwnd)

        idx = -1
        if selected_title:
            idx = self.window_combo.findText(selected_title)
        if idx < 0 and not selected_title and len(windows) == 1:
            idx = 1
        if idx < 0 and self.target_window_hwnd:
            for i in range(self.window_combo.count()):
                if self.window_combo.itemData(i) == self.target_window_hwnd:
                    idx = i
                    break
        if idx >= 0:
            self.window_combo.setCurrentIndex(idx)
        self.window_combo.blockSignals(False)
        self._on_window_selected(self.window_combo.currentIndex())

    def _on_window_selected(self, index: int):
        hwnd = self.window_combo.itemData(index) if index >= 0 else None
        self.target_window_hwnd = hwnd
        self.target_window_title = self.window_combo.currentText() if hwnd else ""

    def _selected_window_hwnd(self):
        self._on_window_selected(self.window_combo.currentIndex())
        return self.target_window_hwnd

    def _default_capture_dir(self):
        import os
        tool_folder = self.tool_id or "temp"
        return os.path.abspath(os.path.join("images", tool_folder, "window_captures"))

    def _selected_capture_dir(self):
        import os
        folder = self.capture_path_input.text().strip() if hasattr(self, "capture_path_input") else ""
        if not folder:
            folder = self.window_capture_dir or self._default_capture_dir()
            if hasattr(self, "capture_path_input"):
                self.capture_path_input.setText(folder)
        return os.path.abspath(folder)

    def _browse_capture_dir(self):
        current = self._selected_capture_dir()
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu capture", current)
        if folder:
            self.window_capture_dir = folder
            self.capture_path_input.setText(folder)

    def _capture_selected_window(self):
        hwnd = self._selected_window_hwnd()
        if not hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn window game trước khi capture!")
            return

        try:
            import os
            from datetime import datetime
            import cv2
            from ..logic.system_executor.window_capture import WindowCapture

            screenshot = WindowCapture(hwnd).capture()
            if screenshot is None:
                QMessageBox.warning(self, "Lỗi", "Không capture được window game.")
                return

            capture_dir = self._selected_capture_dir()
            os.makedirs(capture_dir, exist_ok=True)
            filename = f"window_capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.png"
            path = os.path.join(capture_dir, filename)

            ok, encoded = cv2.imencode(".png", screenshot)
            if not ok:
                QMessageBox.warning(self, "Lỗi", "Không encode được ảnh capture.")
                return
            encoded.tofile(path)

            self.window_capture_dir = capture_dir
            self._log(f"<b style='color:green;'>[Capture]</b> Đã lưu: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không capture được window game:\n{e}")
    
    def add_action(self):
        dialog = ActionConfigDialog(parent=self, target_window_hwnd=self._selected_window_hwnd(), tool_id=self.tool_id)
        if dialog.exec():
            action = dialog.get_action()
            if action:  # Kiểm tra action có hợp lệ không (có thể None nếu validation fail)
                self.actions.append(action)
                self.refresh_actions_list()
                # Auto-save tool after adding action
                self._auto_save_tool()

    def _update_goto_destination_indices_for_insert(self, inserted_index: int):
        """Shift goto destinations after inserting an action at the given 0-based index."""
        inserted_step = int(inserted_index) + 1
        for action in self.actions:
            if bool(getattr(action, "goto_step_enabled", False)):
                goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                if goto_idx >= inserted_step and goto_idx > 0:
                    action.goto_step_index = goto_idx + 1

            if bool(getattr(action, "timeout_goto_enabled", False)):
                timeout_goto_idx = int(getattr(action, "timeout_goto_step_index", 0) or 0)
                if timeout_goto_idx >= inserted_step and timeout_goto_idx > 0:
                    action.timeout_goto_step_index = timeout_goto_idx + 1

    def _update_goto_destination_indices_for_delete(self, deleted_index: int):
        """Shift or clamp goto destinations after deleting an action at the given 0-based index."""
        deleted_step = int(deleted_index) + 1
        max_step = len(self.actions)

        for action in self.actions:
            if bool(getattr(action, "goto_step_enabled", False)):
                goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                if goto_idx > deleted_step:
                    action.goto_step_index = goto_idx - 1
                elif goto_idx == deleted_step:
                    if max_step <= 0:
                        action.goto_step_enabled = False
                        action.goto_step_index = 0
                    else:
                        action.goto_step_index = min(deleted_step, max_step)

            if bool(getattr(action, "timeout_goto_enabled", False)):
                timeout_goto_idx = int(getattr(action, "timeout_goto_step_index", 0) or 0)
                if timeout_goto_idx > deleted_step:
                    action.timeout_goto_step_index = timeout_goto_idx - 1
                elif timeout_goto_idx == deleted_step:
                    if max_step <= 0:
                        action.timeout_goto_enabled = False
                        action.timeout_goto_step_index = 0
                    else:
                        action.timeout_goto_step_index = min(deleted_step, max_step)

    def _swap_goto_destination_indices(self, first_index: int, second_index: int):
        """Swap goto destinations when two actions swap positions."""
        first_step = int(first_index) + 1
        second_step = int(second_index) + 1

        for action in self.actions:
            if bool(getattr(action, "goto_step_enabled", False)):
                goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                if goto_idx == first_step:
                    action.goto_step_index = second_step
                elif goto_idx == second_step:
                    action.goto_step_index = first_step

            if bool(getattr(action, "timeout_goto_enabled", False)):
                timeout_goto_idx = int(getattr(action, "timeout_goto_step_index", 0) or 0)
                if timeout_goto_idx == first_step:
                    action.timeout_goto_step_index = second_step
                elif timeout_goto_idx == second_step:
                    action.timeout_goto_step_index = first_step
    
    def edit_action(self):
        current = self.actions_table.currentRow()
        if current < 0 or current >= len(self.actions):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn action để sửa!")
            return
        
        dialog = ActionConfigDialog(self.actions[current], parent=self, target_window_hwnd=self._selected_window_hwnd(), tool_id=self.tool_id)
        if dialog.exec():
            action = dialog.get_action()
            if action:  # Kiểm tra action có hợp lệ không (có thể None nếu validation fail)
                self.actions[current] = action
                self.refresh_actions_list()
                # Auto-save tool after editing action
                self._auto_save_tool()
    
    def delete_action(self):
        current = self.actions_table.currentRow()
        if current < 0 or current >= len(self.actions):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn action để xóa!")
            return
        
        reply = QMessageBox.question(self, "Xác nhận", "Bạn có chắc muốn xóa action này?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.actions[current]
            self._update_goto_destination_indices_for_delete(current)
            self.refresh_actions_list()
            self._auto_save_tool()
    
    def duplicate_action(self):
        current = self.actions_table.currentRow()
        if current < 0 or current >= len(self.actions):
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn action để duplicate!")
            return
        
        duplicated = copy.deepcopy(self.actions[current])
        self.actions.insert(current + 1, duplicated)
        self._update_goto_destination_indices_for_insert(current + 1)
        self.refresh_actions_list()
        self._auto_save_tool()
    
    def move_action_up(self):
        """Di chuyển action lên vị trí trước"""
        current = self.actions_table.currentRow()
        if current <= 0 or current >= len(self.actions):
            return
        
        # Hoán đổi vị trí
        self.actions[current], self.actions[current - 1] = self.actions[current - 1], self.actions[current]
        self._swap_goto_destination_indices(current - 1, current)
        self.refresh_actions_list()
        self.actions_table.selectRow(current - 1)
        self._auto_save_tool()
    
    def move_action_down(self):
        """Di chuyển action xuống vị trí sau"""
        current = self.actions_table.currentRow()
        if current < 0 or current >= len(self.actions) - 1:
            return
        
        # Hoán đổi vị trí
        self.actions[current], self.actions[current + 1] = self.actions[current + 1], self.actions[current]
        self._swap_goto_destination_indices(current, current + 1)
        self.refresh_actions_list()
        self.actions_table.selectRow(current + 1)
        self._auto_save_tool()
    
    def refresh_actions_list(self):
        self.actions_table.setRowCount(0)
        for i, action in enumerate(self.actions):
            row = self.actions_table.rowCount()
            self.actions_table.insertRow(row)
            
            # Build display text with mode suffix for MOUSE_CLICK
            display_text = f"{i+1}. {action.name} - {action.action_type.value}"
            
            # Add mode suffix for MOUSE_CLICK
            if action.action_type.value == "Click Chuột":
                if bool(getattr(action, "click_by_coordinate", False)):
                    display_text += " (tọa độ)"
                else:
                    display_text += " (hình ảnh)"
            
            self.actions_table.setItem(row, 0, QTableWidgetItem(display_text))
            
            # Nút "Chạy test"
            run_btn = QPushButton("▶ Chạy")
            run_btn.setToolTip("Chạy thử action này")
            run_btn.clicked.connect(lambda checked, idx=i: self._test_action(idx))
            self.actions_table.setCellWidget(row, 1, run_btn)
            
            # Nút "Dừng test"
            stop_btn = QPushButton("■ Dừng")
            stop_btn.setToolTip("Dừng test đang chạy")
            stop_btn.clicked.connect(lambda checked, idx=i: self._stop_test(idx))
            stop_btn.setEnabled(False)
            self.actions_table.setCellWidget(row, 2, stop_btn)
            
            # Cột "Thời gian"
            time_text = ""
            if i in self._action_times:
                time_text = f"{self._action_times[i]:.0f}ms"
            time_item = QTableWidgetItem(time_text)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.actions_table.setItem(row, 3, time_item)
    
    def load_tool(self):
        """Load tool by UUID."""
        tool = self.tool_manager.load_tool(self.tool_id)
        if tool:
            self.tool_name = tool.name
            self.actions = tool.actions
            self.name_input.setText(tool.name)
            self.target_window_title = str(getattr(tool, "target_window_title", "") or "")
            self.window_capture_dir = str(getattr(tool, "window_capture_dir", "") or "")
            self.capture_path_input.setText(self.window_capture_dir or self._default_capture_dir())
            self.refresh_game_windows()
            self.setWindowTitle(f"Chỉnh sửa Tool: {tool.name}")
            self.refresh_actions_list()
    
    def _auto_save_tool(self):
        """Auto-save tool without showing message or closing window."""
        name = self.name_input.text().strip()
        if not name or not self.actions:
            return  # Skip auto-save if no name or no actions
        
        # Preserve tool-level settings when editing an existing tool
        loop_enabled = False
        loop_mode = "forever"
        loop_count = 1
        loop_pre_delay_100ms = 0
        loop_post_delay_100ms = 0
        stop_on_timeout = True
        restart_on_timeout = False
        
        if self.tool_id:
            loaded = self.tool_manager.load_tool(self.tool_id)
            if loaded:
                loop_enabled = bool(getattr(loaded, "loop_enabled", False))
                loop_mode = getattr(loaded, "loop_mode", "forever")
                loop_count = int(getattr(loaded, "loop_count", 1) or 1)
                loop_pre_delay_100ms = int(getattr(loaded, "loop_pre_delay_100ms", 0) or 0)
                loop_post_delay_100ms = int(getattr(loaded, "loop_post_delay_100ms", 0) or 0)
                stop_on_timeout = bool(getattr(loaded, "stop_on_timeout", True))
                restart_on_timeout = bool(getattr(loaded, "restart_on_timeout", False))
                
                # Update existing tool
                tool = Tool(
                    id=self.tool_id,  # Keep same UUID
                    name=name,
                    actions=self.actions,
                    loop_enabled=loop_enabled,
                    loop_mode=loop_mode,
                    loop_count=loop_count,
                    loop_pre_delay_100ms=loop_pre_delay_100ms,
                    loop_post_delay_100ms=loop_post_delay_100ms,
                    stop_on_timeout=stop_on_timeout,
                    restart_on_timeout=restart_on_timeout,
                    target_window_title=self.target_window_title,
                    window_capture_dir=self.capture_path_input.text().strip(),
                )
            else:
                # Tool not found, create new
                tool = Tool(
                    name=name,
                    actions=self.actions,
                    target_window_title=self.target_window_title,
                    window_capture_dir=self.capture_path_input.text().strip(),
                )
                self.tool_id = tool.id
        else:
            # New tool
            tool = Tool(
                name=name,
                actions=self.actions,
                target_window_title=self.target_window_title,
                window_capture_dir=self.capture_path_input.text().strip(),
            )
            self.tool_id = tool.id
        
        if not getattr(tool, "window_capture_dir", ""):
            tool.window_capture_dir = self._default_capture_dir()
            self.capture_path_input.setText(tool.window_capture_dir)
        self.tool_manager.save_tool(tool)
        self.tool_saved.emit()
        print(f"[DEBUG] Auto-saved tool: {name} (ID: {self.tool_id})")
    
    def save_tool(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập tên tool!")
            return
        
        if not self.actions:
            QMessageBox.warning(self, "Cảnh báo", "Tool phải có ít nhất 1 action!")
            return
        
        # Validate unique name
        if not self.tool_manager.validate_unique_name(name, exclude_id=self.tool_id):
            QMessageBox.warning(self, "Cảnh báo", "Tên tool đã tồn tại. Vui lòng chọn tên khác.")
            return
        
        # Preserve tool-level settings when editing an existing tool
        loop_enabled = False
        loop_mode = "forever"
        loop_count = 1
        loop_pre_delay_100ms = 0
        loop_post_delay_100ms = 0
        stop_on_timeout = True
        restart_on_timeout = False
        
        if self.tool_id:
            # Editing existing tool
            loaded = self.tool_manager.load_tool(self.tool_id)
            if loaded:
                loop_enabled = bool(getattr(loaded, "loop_enabled", False))
                loop_mode = getattr(loaded, "loop_mode", "forever")
                loop_count = int(getattr(loaded, "loop_count", 1) or 1)
                loop_pre_delay_100ms = int(getattr(loaded, "loop_pre_delay_100ms", 0) or 0)
                loop_post_delay_100ms = int(getattr(loaded, "loop_post_delay_100ms", 0) or 0)
                stop_on_timeout = bool(getattr(loaded, "stop_on_timeout", True))
                restart_on_timeout = bool(getattr(loaded, "restart_on_timeout", False))
            
            tool = Tool(
                id=self.tool_id,  # Keep same UUID
                name=name,
                actions=self.actions,
                loop_enabled=loop_enabled,
                loop_mode=loop_mode,
                loop_count=loop_count,
                loop_pre_delay_100ms=loop_pre_delay_100ms,
                loop_post_delay_100ms=loop_post_delay_100ms,
                stop_on_timeout=stop_on_timeout,
                restart_on_timeout=restart_on_timeout,
                target_window_title=self.target_window_title,
                window_capture_dir=self.capture_path_input.text().strip(),
            )
        else:
            # Creating new tool
            tool = Tool(
                name=name,
                actions=self.actions,
                loop_enabled=loop_enabled,
                loop_mode=loop_mode,
                loop_count=loop_count,
                loop_pre_delay_100ms=loop_pre_delay_100ms,
                loop_post_delay_100ms=loop_post_delay_100ms,
                stop_on_timeout=stop_on_timeout,
                restart_on_timeout=restart_on_timeout,
                target_window_title=self.target_window_title,
                window_capture_dir=self.capture_path_input.text().strip(),
            )
            self.tool_id = tool.id  # Store new UUID
        
        # Debug log
        for i, action in enumerate(self.actions):
            print(f"[DEBUG] save_tool: action[{i}].image_path={getattr(action, 'image_path', None)}")
        
        if not getattr(tool, "window_capture_dir", ""):
            tool.window_capture_dir = self._default_capture_dir()
            self.capture_path_input.setText(tool.window_capture_dir)
        self.tool_manager.save_tool(tool)
        QMessageBox.information(self, "Thành công", f"Đã lưu tool: {name}")
        self.tool_saved.emit()
        self.close()

    def _append_log(self, msg: str):
        """Append log to test log area (ALWAYS called from UI thread via signal).
        
        This method is connected to _test_log_signal with QueuedConnection,
        ensuring it's always executed in the UI thread, making it thread-safe.
        """
        try:
            # Add timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"<span style='color:#888;'>[{timestamp}]</span> {msg}"
            
            # Append to test log area (safe because always called from UI thread)
            self.test_log_area.append(formatted_msg)
            
            # Auto-scroll to bottom
            cursor = self.test_log_area.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.test_log_area.setTextCursor(cursor)
        except Exception as e:
            print(f"[TEST LOG ERROR] {e}")

    def _log(self, msg: str):
        """Log message to test log area (thread-safe via signal).
        
        This method emits a signal instead of directly updating the UI,
        making it safe to call from any thread (UI thread or background thread).
        """
        self._test_log_signal.emit(msg)

    def _test_action(self, action_index: int):
        """Test the action at given index."""
        if action_index < 0 or action_index >= len(self.actions):
            QMessageBox.warning(self, "Cảnh báo", "Action không hợp lệ!")
            return
        
        action = self.actions[action_index]
        
        # Check if this is a passive action (no window required)
        is_passive = action.action_type in (ActionType.EVENT_NOTIFY, ActionType.READ_PASSIVE)
        
        # Check if this action needs window focus (only KEYBOARD and MOUSE_CLICK)
        needs_focus = action.action_type in (ActionType.KEYBOARD, ActionType.MOUSE_CLICK)
        target_hwnd = self._selected_window_hwnd()
        
        # Check if window is selected (only for non-passive actions)
        if not is_passive and not target_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn window game trước khi test!")
            return
        
        # Use lock to prevent race conditions
        with self._test_lock:
            # Prevent multiple tests running
            if self._test_running:
                QMessageBox.warning(self, "Cảnh báo", "Đang có test đang chạy!")
                return
            
            # Check conflict with test all
            if self._test_all_running:
                QMessageBox.warning(self, "Cảnh báo", "Test toàn bộ đang chạy!")
                return
            
            # Set running flag inside lock
            self._test_running = True
            self._test_should_stop = False
            self._current_test_index = action_index
        
        # Stop any running tool in main window
        if self.main_window:
            try:
                for runner in self.main_window.runners.values():
                    if runner.is_running:
                        runner.stop()
                        self._log("<b style='color:orange;'>Đã dừng tool đang chạy để test action</b>")
            except Exception:
                pass
        
        # Focus game window (only for KEYBOARD and MOUSE_CLICK actions)
        if needs_focus and target_hwnd:
            try:
                from ..logic.window_detector import WindowDetector
                detector = WindowDetector()
                detector.set_foreground_window(target_hwnd)
                time.sleep(0.2)
            except Exception as e:
                self._log(f"<b style='color:red;'>Lỗi focus window:</b> {e}")
        
        # Update buttons
        self._update_test_buttons(action_index, running=True)
        
        # Create engine before starting thread (thread-safe)
        test_engine = _TestEngine()
        self._test_engine = test_engine
        
        def run_test():
            executor = None
            try:
                from ..logic.system_executor import SystemExecutor
                from ..logic.action_type import ActionType
                executor = SystemExecutor(
                    target_window_hwnd=target_hwnd,
                    ui_log_func=self._log  # Direct call, _log emits signal safely
                )
                
                # Use local reference to engine (avoid race condition)
                executor.engine = test_engine
                
                action_display = f"{action.name} - {action.action_type.value}"
                self._log(f"<b style='color:cyan;'>▶ Testing:</b> {action_display}")
                
                start_time = time.perf_counter()
                
                # Check if should stop before executing
                if self._test_should_stop or not test_engine.is_running:
                    self._log(f"<b style='color:orange;'>Test đã bị dừng</b>")
                    return
                
                # Execute based on action type
                # READ_PASSIVE, EVENT_NOTIFY have their own logic, so just call execute once
                if action.action_type == ActionType.READ_PASSIVE:
                    success = executor.execute(action)
                elif action.action_type == ActionType.EVENT_NOTIFY:
                    success = executor.execute(action)
                elif action.action_type == ActionType.KEYBOARD or action.action_type == ActionType.WAIT:
                    success = executor.execute(action)
                else:
                    # MOUSE_CLICK, IMAGE_DETECT: wait for image with timeout
                    timeout = float(getattr(action, "timeout", 30.0) or 30.0)
                    check_interval = float(getattr(action, "check_interval", 0.5) or 0.5)
                    end_time = time.perf_counter() + timeout
                    success = False
                    while time.perf_counter() < end_time:
                        if self._test_should_stop or not test_engine.is_running:
                            self._log(f"<b style='color:orange;'>Test đã bị dừng</b>")
                            return
                        result = executor.execute(action)
                        if result:
                            success = True
                            break
                        time.sleep(check_interval)
                
                elapsed = (time.perf_counter() - start_time) * 1000
                
                if self._test_should_stop or not test_engine.is_running:
                    self._log(f"<b style='color:orange;'>Test đã bị dừng</b>")
                    return
                
                if success:
                    self._log(f"<b style='color:green;'>✓ Test thành công</b> ({elapsed:.0f}ms)")
                else:
                    self._log(f"<b style='color:red;'>✗ Test thất bại</b> ({elapsed:.0f}ms)")
                    
            except Exception as e:
                self._log(f"<b style='color:red;'>Lỗi test:</b> {e}")
            finally:
                # Cleanup executor resources
                if executor:
                    try:
                        executor.engine = None
                        executor.window_capture = None
                        executor.mouse_controller = None
                        executor.ocr_engine = None
                        executor.gemini_processor = None
                        executor.telegram_notifier = None
                    except Exception:
                        pass
                
                # Reset state with lock
                with self._test_lock:
                    self._test_running = False
                    self._test_should_stop = False
                    self._current_test_index = -1
                    self._test_engine = None
                    self._current_test_thread = None
                
                # Emit signal to update UI in main thread
                try:
                    self._test_finished.emit(action_index)
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_test, daemon=True)
        self._current_test_thread = thread
        thread.start()

    def _stop_test(self, action_index: int):
        """Stop the running test."""
        print(f"[DEBUG] _stop_test called: action_index={action_index}, _test_running={self._test_running}, _current_test_index={self._current_test_index}")
        
        # Set stop flag
        self._test_should_stop = True
        
        # Stop mock engine to signal executor to stop
        if self._test_engine:
            self._test_engine.stop()
            print(f"[DEBUG] _stop_test: mock engine stopped")
        
        # Update UI immediately
        with self._test_lock:
            idx = self._current_test_index if self._current_test_index >= 0 else action_index
        
        if idx >= 0 and idx < self.actions_table.rowCount():
            stop_btn = self.actions_table.cellWidget(idx, 2)
            run_btn = self.actions_table.cellWidget(idx, 1)
            if stop_btn:
                stop_btn.setEnabled(False)
            if run_btn:
                run_btn.setEnabled(True)
                run_btn.setText("▶ Chạy")
        
        if self._test_running:
            self._log(f"<b style='color:orange;'>Đang dừng test...</b>")
        
        # Reset state with lock
        with self._test_lock:
            self._test_running = False
            self._current_test_index = -1

    def _update_test_buttons(self, action_index: int, running: bool):
        """Update test buttons state for given action row."""
        if action_index < 0 or action_index >= self.actions_table.rowCount():
            return
        
        run_btn = self.actions_table.cellWidget(action_index, 1)
        stop_btn = self.actions_table.cellWidget(action_index, 2)
        
        if run_btn:
            run_btn.setEnabled(not running)
            run_btn.setText("Testing..." if running else "▶ Chạy")
        if stop_btn:
            stop_btn.setEnabled(running)
            stop_btn.setText("■ Dừng")  # Reset text in case it was "Đang dừng..."

    def _on_test_finished(self, action_index: int):
        """Handle test finished signal - update UI."""
        self._update_test_buttons(action_index, running=False)
    
    def _toggle_test_log(self):
        """Toggle test log panel expand/collapse."""
        if not self._test_log_visible:
            # Expand: restore last size
            sizes = self._test_log_splitter.sizes()
            sizes[1] = self._test_log_last_size
            self._test_log_splitter.setSizes(sizes)
            self.toggle_log_btn.setText("▼")
            self.toggle_log_btn.setToolTip("Ẩn log panel")
            self._test_log_visible = True
        else:
            # Collapse: save current size and minimize
            sizes = self._test_log_splitter.sizes()
            self._test_log_last_size = sizes[1]
            sizes[1] = 0
            self._test_log_splitter.setSizes(sizes)
            self.toggle_log_btn.setText("▶")
            self.toggle_log_btn.setToolTip("Hiện log panel")
            self._test_log_visible = False
    
    def _clear_test_log(self):
        """Clear test log content."""
        try:
            self.test_log_area.clear()
        except Exception:
            pass

    def _reset_test_all_progress(self):
        """Reset total/action timing and row highlight before a new full test run."""
        self._action_times = {}
        self._live_action_time_timer.stop()
        self._live_action_index = -1
        self._live_action_started_at = None
        self.total_time_label.setText("Tổng thời gian: --")

        self.actions_table.clearSelection()
        for row in range(self.actions_table.rowCount()):
            time_item = self.actions_table.item(row, 3)
            if time_item:
                time_item.setText("")

            for col in range(self.actions_table.columnCount()):
                item = self.actions_table.item(row, col)
                if item:
                    item.setBackground(Qt.GlobalColor.white)
                    item.setForeground(Qt.GlobalColor.black)
                    font = item.font()
                    font.setBold(False)
                    item.setFont(font)

    def _scroll_action_to_top(self, action_index: int):
        """Keep the active action visible near the top of the table."""
        if action_index < 0 or action_index >= self.actions_table.rowCount():
            return

        item = self.actions_table.item(action_index, 0)
        if not item:
            return

        self.actions_table.selectRow(action_index)
        self.actions_table.scrollToItem(
            item,
            QAbstractItemView.ScrollHint.PositionAtTop,
        )

    def _start_live_action_time(self, action_index: int):
        """Start realtime elapsed updates for the current action."""
        self._live_action_index = action_index
        self._live_action_started_at = time.perf_counter()
        self._refresh_live_action_time()
        self._live_action_time_timer.start()

    def _stop_live_action_time(self):
        """Stop realtime elapsed updates for the current action."""
        self._live_action_time_timer.stop()
        self._live_action_index = -1
        self._live_action_started_at = None

    def _refresh_live_action_time(self):
        """Update the current action row elapsed time while full test is running."""
        if (
            not self._test_all_running
            or self._live_action_index < 0
            or self._live_action_started_at is None
        ):
            return

        elapsed_ms = (time.perf_counter() - self._live_action_started_at) * 1000
        self._update_action_time(self._live_action_index, elapsed_ms)


    def _highlight_action(self, action_index: int, highlight: bool):
        """Highlight or unhighlight action row."""
        if action_index < 0 or action_index >= self.actions_table.rowCount():
            return
        
        from PyQt6.QtGui import QColor, QBrush
        
        if highlight:
            color = QColor(255, 245, 157)
            text_color = QColor(80, 60, 0)
            self._start_live_action_time(action_index)
            self._scroll_action_to_top(action_index)
        else:
            color = QColor(255, 255, 255)
            text_color = QColor(0, 0, 0)
            if self._live_action_index == action_index:
                self._stop_live_action_time()
        
        brush = QBrush(color)
        text_brush = QBrush(text_color)
        
        # Set background for all items in row
        for col in range(self.actions_table.columnCount()):
            item = self.actions_table.item(action_index, col)
            if item:
                item.setBackground(brush)
                item.setForeground(text_brush)
                font = item.font()
                font.setBold(bool(highlight))
                item.setFont(font)
    
    def _update_action_time(self, action_index: int, elapsed_ms: float):
        """Update action time in table."""
        if action_index < 0 or action_index >= self.actions_table.rowCount():
            return
        
        self._action_times[action_index] = elapsed_ms
        
        time_item = self.actions_table.item(action_index, 3)
        if time_item:
            time_item.setText(f"{elapsed_ms:.0f}ms")
    
    def _update_test_all_buttons(self, running: bool):
        """Update test all buttons state."""
        self.test_all_btn.setEnabled(not running)
        self.stop_all_btn.setEnabled(running)
        
        # Disable/enable individual test buttons
        for i in range(self.actions_table.rowCount()):
            run_btn = self.actions_table.cellWidget(i, 1)
            stop_btn = self.actions_table.cellWidget(i, 2)
            if run_btn:
                run_btn.setEnabled(not running)
            if stop_btn:
                stop_btn.setEnabled(False)
    
    def _test_all_actions(self):
        """Test all actions sequentially (like running tool for 1 cycle)."""
        if not self.actions:
            QMessageBox.warning(self, "Cảnh báo", "Không có action nào để test!")
            return
        
        target_hwnd = self._selected_window_hwnd()
        if not target_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn window game trước khi test!")
            return
        
        if self._test_all_running:
            QMessageBox.warning(self, "Cảnh báo", "Test toàn bộ đang chạy!")
            return
        
        if self._test_running:
            QMessageBox.warning(self, "Cảnh báo", "Test riêng lẻ đang chạy!")
            return
        
        # Load tool settings
        tool = None
        if self.tool_name:
            tool = self.tool_manager.load_tool(self.tool_name)
        
        if not tool:
            # Create temporary tool with default settings
            tool = Tool(
                self.name_input.text().strip() or "temp",
                self.actions,
                stop_on_timeout=True,
                restart_on_timeout=False
            )
        
        self._reset_test_all_progress()
        
        # Stop any running tool in main window
        if self.main_window:
            try:
                for runner in self.main_window.runners.values():
                    if runner.is_running:
                        runner.stop()
                        self._log("<b style='color:orange;'>Đã dừng tool đang chạy để test toàn bộ</b>")
            except Exception:
                pass
        
        # Focus game window
        try:
            from ..logic.window_detector import WindowDetector
            detector = WindowDetector()
            detector.set_foreground_window(target_hwnd)
            time.sleep(0.2)
        except Exception as e:
            self._log(f"<b style='color:red;'>Lỗi focus window:</b> {e}")
        
        # Run test in thread
        self._test_all_running = True
        self._test_all_should_stop = False
        self._update_test_all_buttons(running=True)
        
        def run_test_all():
            try:
                from ..logic.system_executor import SystemExecutor
                from ..logic.action_type import ActionType
                
                executor = SystemExecutor(target_window_hwnd=target_hwnd)
                
                # Create mock engine for stop flags
                self._test_engine = _TestEngine()
                executor.engine = self._test_engine
                
                self._log("<b style='color:cyan;'>═══════ BẮT ĐẦU TEST TOÀN BỘ ═══════</b>")
                
                total_start = time.perf_counter()
                
                # Run actions sequentially (like 1 cycle of tool)
                action_index = 0
                while action_index < len(self.actions):
                    if self._test_all_should_stop:
                        self._log("<b style='color:orange;'>Test toàn bộ đã bị dừng</b>")
                        break
                    
                    action = self.actions[action_index]
                    
                    # Build display text
                    action_display = f"{action.name} - {action.action_type.value}"
                    if action.action_type == ActionType.MOUSE_CLICK:
                        if bool(getattr(action, "click_by_coordinate", False)):
                            action_display += " (tọa độ)"
                        else:
                            action_display += " (hình ảnh)"
                    
                    self._log(f"<b style='color:cyan;'>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b>")
                    self._log(f"<b>Step {action_index+1}/{len(self.actions)}:</b> {action_display}")
                    print(f"[TEST ALL] Step {action_index+1}/{len(self.actions)}: {action_display}")
                    
                    # Highlight current action (emit signal for thread-safe UI update)
                    self._highlight_action_signal.emit(action_index, True)
                    
                    action_start = time.perf_counter()
                    success = False
                    error_msg = None
                    
                    # Get input blocking settings from tool
                    block_input_enabled = bool(getattr(tool, "block_input_enabled", False))
                    block_input_duration = float(getattr(tool, "block_input_duration", 3.0) or 3.0)
                    
                    # Execute based on action type (same logic as main.py)
                    if action.action_type == ActionType.KEYBOARD:
                        unlock_timer = None
                        did_block = False
                        try:
                            # Block USER input (tool vẫn gửi được qua SendInput)
                            if block_input_enabled and hasattr(executor, 'mouse_controller'):
                                success_block = executor.mouse_controller.block_input(True)
                                if success_block:
                                    did_block = True
                                    block_start_time = time.perf_counter()
                                    self._log(f"<b style='color:orange;'>🔒 Đã khóa user input (tool vẫn gửi được)</b>")
                                    
                                    # Start timer to unlock after duration (backup)
                                    def unlock_after_timeout():
                                        try:
                                            executor.mouse_controller.block_input(False)
                                            elapsed = time.perf_counter() - block_start_time
                                            self._log(f"<b style='color:green;'>🔓 Đã mở khóa input (timeout {elapsed:.2f}s)</b>")
                                        except Exception:
                                            pass
                                    unlock_timer = threading.Timer(block_input_duration, unlock_after_timeout)
                                    unlock_timer.daemon = True
                                    unlock_timer.start()
                                else:
                                    self._log("<b style='color:orange;'>⚠️ Không thể khóa input (cần quyền admin?)</b>")
                            
                            # Delay (để chắc chắn đã focus)
                            time.sleep(0.1)
                            
                            # Execute action (focus + press key bằng SendInput, không bị block)
                            success = executor.execute(action)
                            
                        finally:
                            # CRITICAL: LUÔN unlock khi action xong (cancel timer nếu còn)
                            if unlock_timer:
                                unlock_timer.cancel()
                            if did_block and hasattr(executor, 'mouse_controller'):
                                try:
                                    executor.mouse_controller.block_input(False)
                                    elapsed = time.perf_counter() - block_start_time
                                    self._log(f"<b style='color:green;'>🔓 Đã mở khóa input (sau delay {elapsed:.2f}s)</b>")
                                except Exception:
                                    pass
                        
                    elif action.action_type == ActionType.WAIT:
                        wait_time = float(getattr(action, "timeout", 1.0) or 1.0)
                        if self._sleep_test_all_interruptible(wait_time):
                            success = True
                        else:
                            self._log("<b style='color:orange;'>Action chờ bị dừng, ngắt test toàn bộ.</b>")
                            break
                    elif action.action_type == ActionType.EVENT_NOTIFY:
                        # EVENT_NOTIFY: check time window, return immediately
                        try:
                            success = executor.execute(action)
                        except Exception as e:
                            error_msg = str(e)
                            self._log(f"<b style='color:red;'>[Event]</b> Lỗi: {e}")
                            print(f"[TEST ALL] Step {action_index+1} ERROR: {e}")
                            success = False
                    else:
                        # MOUSE_CLICK, IMAGE_DETECT, READ_PASSIVE: wait for image with timeout
                        unlock_timer = None
                        did_block = False
                        try:
                            # Block input NGAY TRƯỚC execute (only for MOUSE_CLICK and IMAGE_DETECT, NOT for READ_PASSIVE)
                            should_block = (
                                block_input_enabled 
                                and action.action_type in (ActionType.MOUSE_CLICK, ActionType.IMAGE_DETECT)
                                and hasattr(executor, 'mouse_controller')
                            )
                            
                            if should_block:
                                success_block = executor.mouse_controller.block_input(True)
                                if success_block:
                                    did_block = True
                                    block_start_time = time.perf_counter()
                                    self._log(f"<b style='color:orange;'>🔒 Đã khóa input (tối đa {block_input_duration:.1f}s)</b>")
                                    
                                    # Wait 100ms after blocking for system to stabilize
                                    time.sleep(0.1)
                                    
                                    # Start timer to unlock after duration (backup)
                                    def unlock_after_timeout():
                                        try:
                                            executor.mouse_controller.block_input(False)
                                            elapsed = time.perf_counter() - block_start_time
                                            self._log(f"<b style='color:green;'>🔓 Đã mở khóa input (timeout {elapsed:.2f}s)</b>")
                                        except Exception:
                                            pass
                                    unlock_timer = threading.Timer(block_input_duration, unlock_after_timeout)
                                    unlock_timer.daemon = True
                                    unlock_timer.start()
                                else:
                                    self._log("<b style='color:orange;'>⚠️ Không thể khóa input (cần quyền admin?)</b>")
                            
                            # Execute action
                            timeout = float(getattr(action, "timeout", 30.0) or 30.0)
                            try:
                                success = executor.execute_with_timeout(action, timeout=timeout)
                            except Exception as e:
                                error_msg = str(e)
                                self._log(f"<b style='color:red;'>[Action]</b> Lỗi: {e}")
                                print(f"[TEST ALL] Step {action_index+1} ERROR: {e}")
                                success = False
                            
                        finally:
                            # CRITICAL: LUÔN unlock khi action xong (cancel timer nếu còn)
                            if unlock_timer:
                                unlock_timer.cancel()
                            if did_block and hasattr(executor, 'mouse_controller'):
                                try:
                                    executor.mouse_controller.block_input(False)
                                    elapsed = time.perf_counter() - block_start_time
                                    self._log(f"<b style='color:green;'>🔓 Đã mở khóa input (action xong {elapsed:.2f}s)</b>")
                                except Exception:
                                    pass
                        
                    
                    action_elapsed = (time.perf_counter() - action_start) * 1000
                    
                    # Update action time (emit signal for thread-safe UI update)
                    self._update_action_time_signal.emit(action_index, action_elapsed)
                    
                    # Unhighlight action (emit signal for thread-safe UI update)
                    self._highlight_action_signal.emit(action_index, False)
                    
                    if self._test_all_should_stop:
                        self._log("<b style='color:orange;'>Test toàn bộ đã bị dừng</b>")
                        break
                    
                    if success:
                        self._log(f"<b style='color:green;'>✓ Thành công</b> ({action_elapsed:.0f}ms)")
                        print(f"[TEST ALL] Step {action_index+1} SUCCESS ({action_elapsed:.0f}ms)")
                        
                        # Check goto_step
                        if bool(getattr(action, "goto_step_enabled", False)):
                            goto_idx = int(getattr(action, "goto_step_index", 0) or 0)
                            if goto_idx == 0:
                                # Restart from beginning (test mode doesn't have cycle concept, just restart)
                                self._log(f"<b style='color:cyan;'>🔄 Restart từ đầu</b>")
                                print(f"[TEST ALL] Step {action_index+1} → RESTART from beginning")
                                action_index = 0
                                continue
                            elif 1 <= goto_idx <= len(self.actions):
                                # goto_idx is 1-based step number, convert to 0-based array index
                                target_index = goto_idx - 1
                                self._log(f"<b style='color:cyan;'>🔄 Nhảy về Step {goto_idx}</b>")
                                print(f"[TEST ALL] Step {action_index+1} → GOTO Step {goto_idx}")
                                action_index = target_index
                                continue
                            else:
                                # Invalid goto_idx: out of range
                                self._log(f"<b style='color:orange;'>⚠️ Goto step không hợp lệ: {goto_idx} (phải từ 0-{len(self.actions)})</b>")
                                print(f"[TEST ALL] Step {action_index+1} → INVALID GOTO: {goto_idx}")
                        
                        # Execute delay after goto_step check (same as main.py)
                        if action.delay and action.delay > 0:
                            self._highlight_action_signal.emit(action_index, True)
                            if not self._sleep_test_all_interruptible(action.delay):
                                self._highlight_action_signal.emit(action_index, False)
                                self._log("<b style='color:orange;'>Delay bị dừng, ngắt test toàn bộ.</b>")
                                break
                            action_elapsed = (time.perf_counter() - action_start) * 1000
                            self._update_action_time_signal.emit(action_index, action_elapsed)
                            self._highlight_action_signal.emit(action_index, False)
                        
                        action_index += 1
                    else:
                        fail_reason = error_msg if error_msg else "Timeout/Thất bại"
                        self._log(f"<b style='color:red;'>✗ {fail_reason}</b> ({action_elapsed:.0f}ms)")
                        print(f"[TEST ALL] Step {action_index+1} FAILED: {fail_reason} ({action_elapsed:.0f}ms)")
                        
                        if bool(getattr(action, "continue_on_timeout", False)):
                            self._log("<b style='color:orange;'>Timeout → bỏ qua step này và làm tiếp step sau</b>")
                            action_index += 1
                            continue

                        # Check action-level timeout goto (per-action setting)
                        if bool(getattr(action, "timeout_goto_enabled", False)):
                            timeout_goto_idx = int(getattr(action, "timeout_goto_step_index", 0) or 0)
                            if timeout_goto_idx == 0:
                                # Restart from beginning (test mode doesn't have cycle concept, just restart)
                                self._log(f"<b style='color:orange;'>Timeout → Restart từ đầu</b>")
                                action_index = 0
                                continue
                            elif 1 <= timeout_goto_idx <= len(self.actions):
                                # timeout_goto_idx is 1-based step number, convert to 0-based array index
                                target_index = timeout_goto_idx - 1
                                self._log(f"<b style='color:orange;'>Timeout → nhảy về Step {timeout_goto_idx}</b>")
                                action_index = target_index
                                continue
                            else:
                                # Invalid timeout_goto_idx: out of range
                                self._log(f"<b style='color:orange;'>⚠️ Timeout goto step không hợp lệ: {timeout_goto_idx} (phải từ 0-{len(self.actions)})</b>")
                        
                        # Check tool settings
                        stop_on_timeout = bool(getattr(tool, "stop_on_timeout", True))
                        restart_on_timeout = bool(getattr(tool, "restart_on_timeout", False))
                        
                        if stop_on_timeout:
                            self._log("<b style='color:red;'>⚠️ Dừng tool do timeout (stop_on_timeout=True)</b>")
                            break
                        elif restart_on_timeout:
                            self._log("<b style='color:orange;'>🔄 Restart tool do timeout (restart_on_timeout=True)</b>")
                            action_index = 0
                            continue
                        else:
                            # Continue to next action
                            action_index += 1
                
                total_elapsed = (time.perf_counter() - total_start) * 1000
                
                # Final summary
                self._log("<b style='color:cyan;'>═══════ KẾT THÚC TEST TOÀN BỘ ═══════</b>")
                self._log(f"<b>Tổng thời gian: {total_elapsed:.0f}ms ({total_elapsed/1000:.2f}s)</b>")
                print(f"[TEST ALL] COMPLETED: Total time {total_elapsed:.0f}ms ({total_elapsed/1000:.2f}s)")
                
                # Update total time label
                try:
                    self.total_time_label.setText(f"Tổng thời gian: {total_elapsed:.0f}ms")
                except Exception:
                    pass
                
                if not self._test_all_should_stop:
                    self._log(f"<b style='color:cyan;'>═══════ KẾT THÚC TEST TOÀN BỘ ═══════</b>")
                    self._log(f"<b style='color:yellow;'>⏱️ Tổng thời gian: {total_elapsed:.0f}ms</b>")
                
            except Exception as e:
                self._log(f"<b style='color:red;'>Lỗi test toàn bộ:</b> {e}")
            finally:
                self._test_all_running = False
                self._test_all_should_stop = False
                self._test_engine = None
                self._live_action_time_timer.stop()
                self._live_action_index = -1
                self._live_action_started_at = None
                
                # Update UI in main thread
                try:
                    self._update_test_all_buttons(running=False)
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_test_all, daemon=True)
        thread.start()
    
    def _stop_all_tests(self):
        """Stop test all actions."""
        self._test_all_should_stop = True
        
        # Stop mock engine
        if self._test_engine:
            self._test_engine.stop()
        
        self._log("<b style='color:orange;'>Đang dừng test toàn bộ...</b>")
    
    def closeEvent(self, event):
        """Cleanup when dialog is closed - stop any running tests."""
        # Stop single test
        if self._test_running:
            self._test_should_stop = True
            if self._test_engine:
                self._test_engine.stop()
        
        # Stop test all
        if self._test_all_running:
            self._test_all_should_stop = True
            if self._test_engine:
                self._test_engine.stop()
        
        # Release all modifier keys to prevent stuck keys
        if hasattr(self, '_test_executor') and self._test_executor:
            try:
                self._test_executor.release_all_modifier_keys()
            except:
                pass
        
        # Accept close event
        event.accept()
