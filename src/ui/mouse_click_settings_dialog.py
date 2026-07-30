"""Mouse Click Action Settings Dialog."""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSpinBox, QCheckBox, QDoubleSpinBox, QGroupBox,
                             QWidget, QMessageBox, QFileDialog, QComboBox, QScrollArea,
                             QListWidget, QAbstractItemView)
from PyQt6.QtCore import Qt, QPointF
from ..logic.action_type import AutoAction
import os
import shutil


class MouseClickSettingsDialog(QDialog):
    """Dialog for configuring MOUSE_CLICK action settings."""
    
    def __init__(self, action: AutoAction, parent=None, target_window_hwnd=None, tool_id: str = None):
        super().__init__(parent)
        self.action = action
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id
        self.teaching_corners = None  # Initialize teaching_corners attribute
        self.post_click_teaching_corners = None
        self.setWindowTitle("Cài đặt Mouse Click Action")
        self.setFixedSize(520, 650)
        self._init_ui()
        self._load_settings()
    
    def _init_ui(self):
        """Initialize UI components."""
        # Main layout for dialog
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Content widget inside scroll area
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        # Click mode selection (at top)
        mode_group = QGroupBox("Chế độ Click")
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Chế độ:"))
        self.click_mode_combo = QComboBox()
        self.click_mode_combo.addItem("Click theo hình ảnh", False)  # click_by_coordinate = False
        self.click_mode_combo.addItem("Click theo tọa độ", True)     # click_by_coordinate = True
        self.click_mode_combo.currentIndexChanged.connect(self._on_click_mode_changed)
        mode_layout.addWidget(self.click_mode_combo)
        mode_layout.addStretch()
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # ===== COMMON LAYOUTS (always visible, at top) =====
        
        # Timeout settings
        timeout_group = QGroupBox("Thời gian chờ")
        timeout_layout = QVBoxLayout()
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Thời gian tối đa chờ:"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setMinimum(1)
        self.timeout_spin.setMaximum(36000)
        self.timeout_spin.setValue(50)
        self.timeout_spin.setSuffix(" x 100ms")
        timeout_row.addWidget(self.timeout_spin)
        timeout_row.addStretch()
        timeout_layout.addLayout(timeout_row)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Chu kỳ kiểm tra:"))
        self.check_interval_spin = QSpinBox()
        self.check_interval_spin.setMinimum(1)
        self.check_interval_spin.setMaximum(600)
        self.check_interval_spin.setValue(10)
        self.check_interval_spin.setSuffix(" x 100ms")
        interval_row.addWidget(self.check_interval_spin)
        interval_row.addStretch()
        timeout_layout.addLayout(interval_row)
        
        self.continue_on_timeout_checkbox = QCheckBox("Timeout → làm tiếp bước sau")
        timeout_layout.addWidget(self.continue_on_timeout_checkbox)
        
        # Timeout goto step
        timeout_goto_row = QHBoxLayout()
        self.timeout_goto_checkbox = QCheckBox("Timeout → nhảy về step:")
        self.timeout_goto_checkbox.stateChanged.connect(self._on_timeout_goto_changed)
        timeout_goto_row.addWidget(self.timeout_goto_checkbox)
        self.timeout_goto_spin = QSpinBox()
        self.timeout_goto_spin.setMinimum(0)
        self.timeout_goto_spin.setMaximum(100)
        self.timeout_goto_spin.setValue(1)
        self.timeout_goto_spin.setToolTip("0 = Restart cycle từ đầu (có delay)\n1-N = Nhảy về step cụ thể")
        self.timeout_goto_spin.setEnabled(False)
        self.timeout_goto_spin.setToolTip("Số thứ tự step (bắt đầu từ 1)")
        timeout_goto_row.addWidget(self.timeout_goto_spin)
        timeout_goto_row.addStretch()
        timeout_layout.addLayout(timeout_goto_row)
        
        timeout_group.setLayout(timeout_layout)
        layout.addWidget(timeout_group)
        
        # Click options
        click_group = QGroupBox("Tùy chọn Click")
        click_layout = QVBoxLayout()
        
        self.alt_click_checkbox = QCheckBox("Giữ ALT khi click (ALT + Click)")
        click_layout.addWidget(self.alt_click_checkbox)
        
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Delay sau khi click:"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(0)
        self.delay_spin.setMaximum(10000)
        self.delay_spin.setValue(10)
        self.delay_spin.setSuffix(" x 100ms")
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        click_layout.addLayout(delay_row)
        
        click_group.setLayout(click_layout)
        layout.addWidget(click_group)
        
        # Goto step
        goto_group = QGroupBox("Nhảy về step")
        goto_layout = QHBoxLayout()
        self.goto_step_checkbox = QCheckBox("🔄 Khi thành công, nhảy về step:")
        self.goto_step_checkbox.stateChanged.connect(self._on_goto_step_changed)
        goto_layout.addWidget(self.goto_step_checkbox)
        self.goto_step_spin = QSpinBox()
        self.goto_step_spin.setMinimum(0)
        self.goto_step_spin.setMaximum(100)
        self.goto_step_spin.setValue(1)
        self.goto_step_spin.setEnabled(False)
        self.goto_step_spin.setToolTip("0 = Restart cycle từ đầu (có delay)\n1-N = Nhảy về step cụ thể")
        goto_layout.addWidget(self.goto_step_spin)
        goto_layout.addStretch()
        goto_group.setLayout(goto_layout)
        layout.addWidget(goto_group)
        
        # ===== IMAGE MODE LAYOUTS (hide in coordinate mode) =====
        
        # Threshold (image mode only)
        self.threshold_group = QGroupBox("Nhận diện ảnh")
        threshold_layout = QVBoxLayout()
        
        thr_row = QHBoxLayout()
        thr_row.addWidget(QLabel("Ngưỡng nhận diện:"))
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setMinimum(0.10)
        self.threshold_spin.setMaximum(0.99)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setDecimals(2)
        self.threshold_spin.setValue(0.40)
        self.threshold_spin.setToolTip("Ngưỡng thấp = dễ nhận nhưng dễ nhầm\nNgưỡng cao = chính xác nhưng dễ fail")
        thr_row.addWidget(self.threshold_spin)
        thr_row.addStretch()
        threshold_layout.addLayout(thr_row)
        
        self.multiscale_checkbox = QCheckBox("Cho phép thay đổi kích thước (Multi-scale)")
        self.multiscale_checkbox.setChecked(True)
        self.multiscale_checkbox.stateChanged.connect(self._on_multiscale_changed)
        threshold_layout.addWidget(self.multiscale_checkbox)
        
        # Multiscale range settings
        multiscale_range_layout = QHBoxLayout()
        multiscale_range_layout.addWidget(QLabel("Khoảng scale:"))
        multiscale_range_layout.addWidget(QLabel("Min:"))
        self.multiscale_min_spin = QDoubleSpinBox()
        self.multiscale_min_spin.setMinimum(0.10)
        self.multiscale_min_spin.setMaximum(2.00)
        self.multiscale_min_spin.setSingleStep(0.05)
        self.multiscale_min_spin.setDecimals(2)
        self.multiscale_min_spin.setValue(0.70)
        multiscale_range_layout.addWidget(self.multiscale_min_spin)
        
        multiscale_range_layout.addWidget(QLabel("Max:"))
        self.multiscale_max_spin = QDoubleSpinBox()
        self.multiscale_max_spin.setMinimum(0.10)
        self.multiscale_max_spin.setMaximum(3.00)
        self.multiscale_max_spin.setSingleStep(0.05)
        self.multiscale_max_spin.setDecimals(2)
        self.multiscale_max_spin.setValue(1.30)
        multiscale_range_layout.addWidget(self.multiscale_max_spin)
        
        multiscale_range_layout.addWidget(QLabel("Step:"))
        self.multiscale_step_spin = QDoubleSpinBox()
        self.multiscale_step_spin.setMinimum(0.01)
        self.multiscale_step_spin.setMaximum(0.50)
        self.multiscale_step_spin.setSingleStep(0.01)
        self.multiscale_step_spin.setDecimals(2)
        self.multiscale_step_spin.setValue(0.05)
        multiscale_range_layout.addWidget(self.multiscale_step_spin)
        multiscale_range_layout.addStretch()
        
        self.multiscale_range_widget = QWidget()
        self.multiscale_range_widget.setLayout(multiscale_range_layout)
        self.multiscale_range_widget.setVisible(True)
        threshold_layout.addWidget(self.multiscale_range_widget)
        
        self.threshold_group.setLayout(threshold_layout)
        layout.addWidget(self.threshold_group)
        
        # Teaching image (image mode only)
        self.teaching_group = QGroupBox("Ảnh Teaching & Tọa độ Click")
        teaching_layout = QVBoxLayout()
        
        # Image path label
        self.image_path_label = QLabel("Chưa chọn ảnh")
        self.image_path_label.setWordWrap(True)
        teaching_layout.addWidget(self.image_path_label)
        
        # Buttons for image selection
        btn_row = QHBoxLayout()
        self.image_btn = QPushButton("Tạo ảnh Teaching")
        self.image_btn.clicked.connect(self._capture_teaching_image)
        btn_row.addWidget(self.image_btn)
        
        self.image_file_btn = QPushButton("Chọn file ảnh...")
        self.image_file_btn.clicked.connect(self._select_image_file)
        btn_row.addWidget(self.image_file_btn)
        
        btn_row.addStretch()
        teaching_layout.addLayout(btn_row)
        
        # Click coordinates
        coord_layout = QHBoxLayout()
        coord_layout.addWidget(QLabel("Tọa độ click:"))
        coord_layout.addWidget(QLabel("X:"))
        self.click_x_spin = QSpinBox()
        self.click_x_spin.setMinimum(0)
        self.click_x_spin.setMaximum(10000)
        coord_layout.addWidget(self.click_x_spin)
        coord_layout.addWidget(QLabel("Y:"))
        self.click_y_spin = QSpinBox()
        self.click_y_spin.setMinimum(0)
        self.click_y_spin.setMaximum(10000)
        coord_layout.addWidget(self.click_y_spin)
        coord_layout.addStretch()
        teaching_layout.addLayout(coord_layout)
        
        self.teaching_group.setLayout(teaching_layout)
        layout.addWidget(self.teaching_group)
        
        # Template Matching Preprocessing section (image mode only)
        self._add_template_matching_preprocessing_section(layout)
        
        # ===== COORDINATE MODE LAYOUT (hide in image mode) =====
        
        self.coordinate_group = QGroupBox("Teaching điểm click")
        coordinate_layout = QVBoxLayout()
        
        # Coordinate click position label
        self.coord_pos_label = QLabel("Chưa chọn điểm click")
        coordinate_layout.addWidget(self.coord_pos_label)
        
        # Button to capture coordinate
        coord_btn_row = QHBoxLayout()
        self.coord_teaching_btn = QPushButton("Chọn điểm click")
        self.coord_teaching_btn.clicked.connect(self._capture_coordinate_click)
        coord_btn_row.addWidget(self.coord_teaching_btn)
        coord_btn_row.addStretch()
        coordinate_layout.addLayout(coord_btn_row)
        
        # Coordinate display
        coord_display_layout = QHBoxLayout()
        coord_display_layout.addWidget(QLabel("Tọa độ click (client):"))
        coord_display_layout.addWidget(QLabel("X:"))
        self.coord_x_spin = QSpinBox()
        self.coord_x_spin.setMinimum(0)
        self.coord_x_spin.setMaximum(10000)
        coord_display_layout.addWidget(self.coord_x_spin)
        coord_display_layout.addWidget(QLabel("Y:"))
        self.coord_y_spin = QSpinBox()
        self.coord_y_spin.setMinimum(0)
        self.coord_y_spin.setMaximum(10000)
        coord_display_layout.addWidget(self.coord_y_spin)
        coord_display_layout.addStretch()
        coordinate_layout.addLayout(coord_display_layout)
        
        self.coordinate_group.setLayout(coordinate_layout)
        layout.addWidget(self.coordinate_group)
        
        # Initially hide coordinate group (default is image mode)
        self.coordinate_group.setVisible(False)

        self.post_click_group = QGroupBox("Kiểm tra kết quả sau khi click")
        post_click_layout = QVBoxLayout()

        self.enable_post_click_check_checkbox = QCheckBox("Bật chế độ click rồi chờ teaching image xuất hiện")
        self.enable_post_click_check_checkbox.stateChanged.connect(self._on_post_click_check_changed)
        post_click_layout.addWidget(self.enable_post_click_check_checkbox)

        self.post_click_settings_widget = QWidget()
        post_click_settings_layout = QVBoxLayout(self.post_click_settings_widget)
        post_click_settings_layout.setContentsMargins(0, 0, 0, 0)

        self.post_click_image_path_label = QLabel("Chưa chọn ảnh kết quả")
        self.post_click_image_path_label.setWordWrap(True)
        post_click_settings_layout.addWidget(self.post_click_image_path_label)

        post_click_btn_row = QHBoxLayout()
        self.post_click_image_btn = QPushButton("Tạo ảnh kết quả")
        self.post_click_image_btn.clicked.connect(self._capture_post_click_teaching_image)
        post_click_btn_row.addWidget(self.post_click_image_btn)

        self.post_click_image_file_btn = QPushButton("Chọn file ảnh...")
        self.post_click_image_file_btn.clicked.connect(self._select_post_click_image_file)
        post_click_btn_row.addWidget(self.post_click_image_file_btn)
        post_click_btn_row.addStretch()
        post_click_settings_layout.addLayout(post_click_btn_row)

        post_click_threshold_row = QHBoxLayout()
        post_click_threshold_row.addWidget(QLabel("Ngưỡng nhận diện kết quả:"))
        self.post_click_threshold_spin = QDoubleSpinBox()
        self.post_click_threshold_spin.setMinimum(0.10)
        self.post_click_threshold_spin.setMaximum(0.99)
        self.post_click_threshold_spin.setSingleStep(0.01)
        self.post_click_threshold_spin.setDecimals(2)
        self.post_click_threshold_spin.setValue(0.40)
        post_click_threshold_row.addWidget(self.post_click_threshold_spin)
        post_click_threshold_row.addStretch()
        post_click_settings_layout.addLayout(post_click_threshold_row)

        post_click_delay_row = QHBoxLayout()
        post_click_delay_row.addWidget(QLabel("Delay trước khi check ảnh:"))
        self.post_click_delay_spin = QSpinBox()
        self.post_click_delay_spin.setMinimum(0)
        self.post_click_delay_spin.setMaximum(10000)
        self.post_click_delay_spin.setValue(10)
        self.post_click_delay_spin.setSuffix(" x 100ms")
        post_click_delay_row.addWidget(self.post_click_delay_spin)
        post_click_delay_row.addStretch()
        post_click_settings_layout.addLayout(post_click_delay_row)

        post_click_retry_row = QHBoxLayout()
        post_click_retry_row.addWidget(QLabel("Số lần retry click lại:"))
        self.post_click_retry_spin = QSpinBox()
        self.post_click_retry_spin.setMinimum(0)
        self.post_click_retry_spin.setMaximum(100)
        self.post_click_retry_spin.setValue(0)
        post_click_retry_row.addWidget(self.post_click_retry_spin)
        post_click_retry_row.addStretch()
        post_click_settings_layout.addLayout(post_click_retry_row)

        post_click_layout.addWidget(self.post_click_settings_widget)
        self.post_click_group.setLayout(post_click_layout)
        layout.addWidget(self.post_click_group)
        
        # Add stretch to prevent layout expansion when groups are hidden
        layout.addStretch()
        
        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Buttons (outside scroll area)
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(10, 5, 10, 10)
        btn_layout.addStretch()
        ok_btn = QPushButton("Lưu")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        main_layout.addLayout(btn_layout)
        
        self.setLayout(main_layout)
    
    def _on_click_mode_changed(self, index):
        """Handle click mode change."""
        is_coordinate_mode = self.click_mode_combo.currentData()
        
        # Show/hide layouts based on mode
        # Image mode layouts
        self.threshold_group.setVisible(not is_coordinate_mode)
        self.teaching_group.setVisible(not is_coordinate_mode)
        self.preprocessing_group.setVisible(not is_coordinate_mode)
        
        # Coordinate mode layout
        self.coordinate_group.setVisible(is_coordinate_mode)
    
    def _on_multiscale_changed(self, state):
        """Show/hide multiscale range settings."""
        self.multiscale_range_widget.setVisible(bool(state))
    
    def _on_goto_step_changed(self, state):
        """Enable/disable goto step spin box."""
        self.goto_step_spin.setEnabled(bool(state))
    
    def _on_timeout_goto_changed(self, state):
        """Enable/disable timeout goto step spin box."""
        self.timeout_goto_spin.setEnabled(bool(state))
        # Disable continue_on_timeout if timeout_goto is enabled
        if state:
            self.continue_on_timeout_checkbox.setChecked(False)
            self.continue_on_timeout_checkbox.setEnabled(False)
        else:
            self.continue_on_timeout_checkbox.setEnabled(True)

    def _on_post_click_check_changed(self, state):
        """Enable/disable post-click result check settings."""
        self.post_click_settings_widget.setEnabled(bool(state))
    
    def _capture_teaching_image(self):
        """Open image capture dialog for image mode."""
        # Get parent's target_window_hwnd
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, 'target_window_hwnd') or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        
        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            parent_dialog.target_window_hwnd,
            parent=self,
            tool_id=getattr(parent_dialog, "tool_id", None),
            hide_click_selection=False,  # MOUSE_CLICK cần chọn điểm click
            hide_region_selection=False,  # Image mode cần chọn vùng
            initial_image_path=getattr(self.action, "image_path", None),
            initial_click_x=getattr(self.action, "click_x", None),
            initial_click_y=getattr(self.action, "click_y", None),
            initial_mask_regions=getattr(self.action, "mask_regions", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()
            
            if len(result) == 9:
                image_path, click_x, click_y, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height = result
            elif len(result) == 7:
                # Backward compatibility
                image_path, click_x, click_y, corner_x1, corner_y1, corner_x2, corner_y2 = result
                window_width, window_height = None, None
            else:
                image_path, click_x, click_y = result[:3]
                corner_x1, corner_y1, corner_x2, corner_y2 = None, None, None, None
                window_width, window_height = None, None
            
            if image_path:
                self.action.image_path = image_path
                # Save mask regions
                self.action.mask_regions = dialog.get_mask_regions()
                filename = os.path.basename(image_path)
                self.image_path_label.setText(f"Đã chọn: {filename}")
                
                # Save teaching corners to self.teaching_corners (not self.action)
                if corner_x1 is not None:
                    self.teaching_corners = (corner_x1, corner_y1, corner_x2, corner_y2)
                    # Also save to action for backward compatibility
                    self.action.teaching_corner_x1 = corner_x1
                    self.action.teaching_corner_y1 = corner_y1
                    self.action.teaching_corner_x2 = corner_x2
                    self.action.teaching_corner_y2 = corner_y2
                
                # Save teaching window size
                if window_width is not None and window_height is not None:
                    self.action.teaching_window_width = window_width
                    self.action.teaching_window_height = window_height
                
                # Update button text AFTER setting teaching_corners
                self._update_image_button_text()
                
                # Save click coordinates
                if click_x is not None and click_y is not None:
                    self.action.click_x = int(click_x)
                    self.action.click_y = int(click_y)
                    self.click_x_spin.setValue(self.action.click_x)
                    self.click_y_spin.setValue(self.action.click_y)
    
    def _capture_coordinate_click(self):
        """Open image capture dialog for coordinate mode (only select click point)."""
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, 'target_window_hwnd') or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return
        
        from .image_capture_dialog import ImageCaptureDialog
        
        # Get current coordinate_click_pos for initial display
        coord_pos = getattr(self.action, "coordinate_click_pos", None)
        initial_x = coord_pos[0] if coord_pos else None
        initial_y = coord_pos[1] if coord_pos else None
        
        dialog = ImageCaptureDialog(
            parent_dialog.target_window_hwnd,
            parent=self,
            tool_id=getattr(parent_dialog, "tool_id", None),
            hide_click_selection=False,  # Need to select click point
            hide_region_selection=True,  # Disable region selection for coordinate mode
            initial_image_path=None,  # No image for coordinate mode
            initial_click_x=initial_x,
            initial_click_y=initial_y,
        )
        if dialog.exec():
            # Get click point from dialog
            click_point = dialog.graphics_view.click_point
            if click_point:
                coord_x = int(click_point.x())
                coord_y = int(click_point.y())
                
                # Save to action
                self.action.coordinate_click_pos = (coord_x, coord_y)
                
                # Update UI
                self.coord_x_spin.setValue(coord_x)
                self.coord_y_spin.setValue(coord_y)
                self.coord_pos_label.setText(f"Đã chọn: ({coord_x}, {coord_y})")
                self.coord_teaching_btn.setText("Xem/Sửa điểm click")
    
    def _select_image_file(self):
        """Select image from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if filepath:
            # Copy image to images folder
            parent_dialog = self.parent()
            base_dir = "images"
            try:
                from .image_capture_dialog import ImageCaptureDialog as _ICD
                sub = _ICD._sanitize_tool_folder_name(getattr(parent_dialog, "tool_name", None))
            except Exception:
                sub = ""
            images_dir = os.path.join(base_dir, sub) if sub else base_dir
            os.makedirs(images_dir, exist_ok=True)
            filename = os.path.basename(filepath)
            dest_path = os.path.join(images_dir, filename)
            shutil.copy2(filepath, dest_path)
            
            self.action.image_path = dest_path
            self.image_path_label.setText(f"Đã chọn: {filename}")
            self._update_image_button_text()
    

    
    def _capture_post_click_teaching_image(self):
        """Capture the expected result image shown after clicking."""
        parent_dialog = self.parent()
        if not hasattr(parent_dialog, 'target_window_hwnd') or not parent_dialog.target_window_hwnd:
            QMessageBox.warning(self, "Cảnh báo", "Chưa chọn window game ở màn hình chính!")
            return

        from .image_capture_dialog import ImageCaptureDialog
        dialog = ImageCaptureDialog(
            parent_dialog.target_window_hwnd,
            parent=self,
            tool_id=getattr(parent_dialog, "tool_id", None),
            hide_click_selection=True,
            hide_region_selection=False,
            initial_image_path=getattr(self.action, "post_click_image_path", None),
        )
        if dialog.exec():
            result = dialog.get_cropped_image_path()

            if len(result) == 9:
                image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height = result
            elif len(result) == 7:
                image_path, _, _, corner_x1, corner_y1, corner_x2, corner_y2 = result
                window_width, window_height = None, None
            else:
                image_path = result[0] if result else None
                corner_x1, corner_y1, corner_x2, corner_y2 = None, None, None, None
                window_width, window_height = None, None

            if image_path:
                self.action.post_click_image_path = image_path
                filename = os.path.basename(image_path)
                self.post_click_image_path_label.setText(f"Đã chọn: {filename}")

                if corner_x1 is not None:
                    self.post_click_teaching_corners = (corner_x1, corner_y1, corner_x2, corner_y2)
                    self.action.post_click_teaching_corner_x1 = corner_x1
                    self.action.post_click_teaching_corner_y1 = corner_y1
                    self.action.post_click_teaching_corner_x2 = corner_x2
                    self.action.post_click_teaching_corner_y2 = corner_y2

                if window_width is not None and window_height is not None:
                    self.action.post_click_teaching_window_width = window_width
                    self.action.post_click_teaching_window_height = window_height

                self._update_post_click_image_button_text()

    def _select_post_click_image_file(self):
        """Select expected result image from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh kết quả", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if filepath:
            parent_dialog = self.parent()
            base_dir = "images"
            try:
                from .image_capture_dialog import ImageCaptureDialog as _ICD
                sub = _ICD._sanitize_tool_folder_name(getattr(parent_dialog, "tool_name", None))
            except Exception:
                sub = ""
            images_dir = os.path.join(base_dir, sub) if sub else base_dir
            os.makedirs(images_dir, exist_ok=True)
            filename = os.path.basename(filepath)
            dest_path = os.path.join(images_dir, filename)
            shutil.copy2(filepath, dest_path)

            self.action.post_click_image_path = dest_path
            self.post_click_image_path_label.setText(f"Đã chọn: {filename}")
            self._update_post_click_image_button_text()

    def _add_template_matching_preprocessing_section(self, layout):
        """Add Template Matching Preprocessing section."""
        self.preprocessing_group = QGroupBox("⚙️ Template Matching Preprocessing")
        preprocessing_layout = QVBoxLayout()
        
        # Algorithm ListView (read-only)
        self.template_algorithms_list = QListWidget()
        self.template_algorithms_list.setMaximumHeight(120)
        self.template_algorithms_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        preprocessing_layout.addWidget(self.template_algorithms_list)
        
        # Configure button
        configure_btn = QPushButton("⚙️ Cấu hình Template Matching Algorithms")
        configure_btn.clicked.connect(self._open_template_matching_config)
        preprocessing_layout.addWidget(configure_btn)
        
        self.preprocessing_group.setLayout(preprocessing_layout)
        layout.addWidget(self.preprocessing_group)
    
    def _open_template_matching_config(self):
        """Open Multi-Image Testing Dialog for template matching."""
        from .multi_image_algorithm_testing_dialog import MultiImageAlgorithmTestingDialog
        
        # Pass current template_matching_algorithms to dialog
        dialog = MultiImageAlgorithmTestingDialog(
            action=self.action,
            parent=self,
            target_window_hwnd=self.target_window_hwnd,
            tool_id=self.tool_id
        )
        
        # Set current algorithms if any
        if hasattr(self.action, 'template_matching_algorithms') and self.action.template_matching_algorithms:
            # Load algorithms into dialog (this would need to be implemented in MultiImageAlgorithmTestingDialog)
            pass
        
        if dialog.exec():
            # Update display after dialog closes
            self._update_template_algorithms_display()
    
    def _update_template_algorithms_display(self):
        """Update template algorithms ListView display."""
        algorithms = getattr(self.action, 'template_matching_algorithms', [])
        from .algorithm_display_utils import update_algorithms_display
        update_algorithms_display(self.template_algorithms_list, algorithms)
    
    def _update_image_button_text(self):
        """Update button text based on whether image exists."""
        # Check both image_path (image mode) and teaching_corners (coordinate mode)
        has_teaching = False
        if self.action.image_path and os.path.exists(self.action.image_path):
            has_teaching = True
        elif hasattr(self, 'teaching_corners') and self.teaching_corners and len(self.teaching_corners) == 4:
            has_teaching = True
        
        if has_teaching:
            self.image_btn.setText("Xem/Sửa ảnh Teaching")
        else:
            self.image_btn.setText("Tạo ảnh Teaching")
    
    def _update_post_click_image_button_text(self):
        """Update button text for the expected result image."""
        has_post_click_teaching = False
        if self.action.post_click_image_path and os.path.exists(self.action.post_click_image_path):
            has_post_click_teaching = True
        elif self.post_click_teaching_corners and len(self.post_click_teaching_corners) == 4:
            has_post_click_teaching = True

        if has_post_click_teaching:
            self.post_click_image_btn.setText("Xem/Sửa ảnh kết quả")
        else:
            self.post_click_image_btn.setText("Tạo ảnh kết quả")

    def _load_settings(self):
        """Load settings from action."""
        # Click mode
        click_by_coordinate = bool(getattr(self.action, "click_by_coordinate", False))
        self.click_mode_combo.setCurrentIndex(1 if click_by_coordinate else 0)
        self._on_click_mode_changed(self.click_mode_combo.currentIndex())
        
        # Threshold
        try:
            thr = float(getattr(self.action, "match_threshold", 0.4))
            self.threshold_spin.setValue(max(0.10, min(0.99, thr)))
        except Exception:
            pass
        
        # Multiscale
        try:
            multiscale_enabled = bool(getattr(self.action, "multiscale_enabled", True))
            self.multiscale_checkbox.setChecked(multiscale_enabled)
            self.multiscale_range_widget.setVisible(multiscale_enabled)
        except Exception:
            pass
        
        # Multiscale range
        try:
            self.multiscale_min_spin.setValue(float(getattr(self.action, "multiscale_min", 0.70)))
            self.multiscale_max_spin.setValue(float(getattr(self.action, "multiscale_max", 1.30)))
            self.multiscale_step_spin.setValue(float(getattr(self.action, "multiscale_step", 0.05)))
        except Exception:
            pass
        
        # Timeout
        timeout_value = float(getattr(self.action, 'timeout', 5.0))
        self.timeout_spin.setValue(max(1, int(round(timeout_value * 10))))
        
        check_interval_value = float(getattr(self.action, 'check_interval', 1.0))
        self.check_interval_spin.setValue(max(1, int(round(check_interval_value * 10))))
        
        try:
            self.continue_on_timeout_checkbox.setChecked(bool(getattr(self.action, "continue_on_timeout", False)))
        except Exception:
            pass
        
        # Timeout goto step
        timeout_goto_enabled = bool(getattr(self.action, "timeout_goto_enabled", False))
        self.timeout_goto_checkbox.setChecked(timeout_goto_enabled)
        self.timeout_goto_spin.setEnabled(timeout_goto_enabled)
        idx = int(getattr(self.action, "timeout_goto_step_index", 0) or 0)
        self.timeout_goto_spin.setValue(idx)  # No conversion: 0=restart, 1=step1, 2=step2...
        # Disable continue_on_timeout if timeout_goto is enabled
        if timeout_goto_enabled:
            self.continue_on_timeout_checkbox.setEnabled(False)
        
        # Click options
        try:
            self.alt_click_checkbox.setChecked(bool(getattr(self.action, "alt_click", False)))
        except Exception:
            pass
        
        # Delay
        delay_in_100ms = int(self.action.delay * 10)
        self.delay_spin.setValue(delay_in_100ms)
        
        # Teaching image (image mode)
        if self.action.image_path:
            filename = os.path.basename(self.action.image_path)
            self.image_path_label.setText(f"Đã chọn: {filename}")
        
        # Load teaching image corners (for both modes) - MUST BE BEFORE _update_image_button_text()
        try:
            x1 = getattr(self.action, "teaching_corner_x1", None)
            y1 = getattr(self.action, "teaching_corner_y1", None)
            x2 = getattr(self.action, "teaching_corner_x2", None)
            y2 = getattr(self.action, "teaching_corner_y2", None)
            if all(v is not None for v in [x1, y1, x2, y2]):
                self.teaching_corners = (x1, y1, x2, y2)
        except Exception:
            pass
        
        # Update button text AFTER loading teaching_corners
        self._update_image_button_text()

        try:
            post_x1 = getattr(self.action, "post_click_teaching_corner_x1", None)
            post_y1 = getattr(self.action, "post_click_teaching_corner_y1", None)
            post_x2 = getattr(self.action, "post_click_teaching_corner_x2", None)
            post_y2 = getattr(self.action, "post_click_teaching_corner_y2", None)
            if all(v is not None for v in [post_x1, post_y1, post_x2, post_y2]):
                self.post_click_teaching_corners = (post_x1, post_y1, post_x2, post_y2)
        except Exception:
            pass

        post_click_image_path = getattr(self.action, "post_click_image_path", None)
        if post_click_image_path:
            filename = os.path.basename(post_click_image_path)
            self.post_click_image_path_label.setText(f"Đã chọn: {filename}")
        self._update_post_click_image_button_text()

        self.enable_post_click_check_checkbox.setChecked(
            bool(getattr(self.action, "enable_post_click_image_check", False))
        )
        self.post_click_threshold_spin.setValue(
            max(0.10, min(0.99, float(getattr(self.action, "post_click_match_threshold", 0.4) or 0.4)))
        )
        self.post_click_delay_spin.setValue(
            max(0, int(round(float(getattr(self.action, "post_click_check_delay", 1.0) or 0.0) * 10)))
        )
        self.post_click_retry_spin.setValue(
            max(0, int(getattr(self.action, "post_click_retry_count", 0) or 0))
        )
        self._on_post_click_check_changed(self.enable_post_click_check_checkbox.isChecked())

        # Click coordinates (image mode)
        if self.action.click_x is not None:
            self.click_x_spin.setValue(int(self.action.click_x))
        if self.action.click_y is not None:
            self.click_y_spin.setValue(int(self.action.click_y))
        
        # Coordinate click position (coordinate mode)
        coord_pos = getattr(self.action, "coordinate_click_pos", None)
        if coord_pos and len(coord_pos) >= 2:
            self.coord_x_spin.setValue(int(coord_pos[0]))
            self.coord_y_spin.setValue(int(coord_pos[1]))
            self.coord_pos_label.setText(f"Đã chọn: ({coord_pos[0]}, {coord_pos[1]})")
            self.coord_teaching_btn.setText("Xem/Sửa điểm click")
        
        # Goto step
        self.goto_step_checkbox.setChecked(bool(getattr(self.action, "goto_step_enabled", False)))
        idx = int(getattr(self.action, "goto_step_index", 0) or 0)
        self.goto_step_spin.setValue(idx)  # No conversion: 0=restart, 1=step1, 2=step2...
        self.goto_step_spin.setEnabled(bool(getattr(self.action, "goto_step_enabled", False)))
        
        # Template matching algorithms
        self._update_template_algorithms_display()
    
    def get_settings(self) -> dict:
        """Get settings from dialog.
        
        Returns:
            Dict with all mouse click settings
        """
        is_coordinate_mode = self.click_mode_combo.currentData()
        
        # Get coordinate_click_pos from spin boxes
        coord_pos = None
        if is_coordinate_mode:
            coord_x = self.coord_x_spin.value()
            coord_y = self.coord_y_spin.value()
            if coord_x > 0 or coord_y > 0:
                coord_pos = (coord_x, coord_y)
        
        # Get teaching corners from self.teaching_corners (not self.action)
        teaching_x1 = None
        teaching_y1 = None
        teaching_x2 = None
        teaching_y2 = None
        if hasattr(self, 'teaching_corners') and self.teaching_corners and len(self.teaching_corners) == 4:
            teaching_x1, teaching_y1, teaching_x2, teaching_y2 = self.teaching_corners

        post_click_teaching_x1 = None
        post_click_teaching_y1 = None
        post_click_teaching_x2 = None
        post_click_teaching_y2 = None
        if self.post_click_teaching_corners and len(self.post_click_teaching_corners) == 4:
            (
                post_click_teaching_x1,
                post_click_teaching_y1,
                post_click_teaching_x2,
                post_click_teaching_y2,
            ) = self.post_click_teaching_corners
        
        return {
            "click_by_coordinate": bool(is_coordinate_mode),
            "coordinate_click_pos": coord_pos,
            "match_threshold": float(self.threshold_spin.value()),
            "multiscale_enabled": bool(self.multiscale_checkbox.isChecked()),
            "multiscale_min": float(self.multiscale_min_spin.value()),
            "multiscale_max": float(self.multiscale_max_spin.value()),
            "multiscale_step": float(self.multiscale_step_spin.value()),
            "timeout": self.timeout_spin.value() / 10.0,
            "check_interval": self.check_interval_spin.value() / 10.0,
            "continue_on_timeout": bool(self.continue_on_timeout_checkbox.isChecked()),
            "alt_click": bool(self.alt_click_checkbox.isChecked()),
            "delay": self.delay_spin.value() / 10.0,
            "image_path": self.action.image_path,
            "click_x": int(self.click_x_spin.value()) if self.click_x_spin.value() > 0 else None,
            "click_y": int(self.click_y_spin.value()) if self.click_y_spin.value() > 0 else None,
            "teaching_corner_x1": teaching_x1,
            "teaching_corner_y1": teaching_y1,
            "teaching_corner_x2": teaching_x2,
            "teaching_corner_y2": teaching_y2,
            "teaching_window_width": getattr(self.action, "teaching_window_width", None),
            "teaching_window_height": getattr(self.action, "teaching_window_height", None),
            "enable_post_click_image_check": bool(self.enable_post_click_check_checkbox.isChecked()),
            "post_click_check_delay": self.post_click_delay_spin.value() / 10.0,
            "post_click_retry_count": int(self.post_click_retry_spin.value()),
            "post_click_image_path": getattr(self.action, "post_click_image_path", None),
            "post_click_match_threshold": float(self.post_click_threshold_spin.value()),
            "post_click_teaching_corner_x1": post_click_teaching_x1,
            "post_click_teaching_corner_y1": post_click_teaching_y1,
            "post_click_teaching_corner_x2": post_click_teaching_x2,
            "post_click_teaching_corner_y2": post_click_teaching_y2,
            "post_click_teaching_window_width": getattr(self.action, "post_click_teaching_window_width", None),
            "post_click_teaching_window_height": getattr(self.action, "post_click_teaching_window_height", None),
            "goto_step_enabled": bool(self.goto_step_checkbox.isChecked()),
            "goto_step_index": int(self.goto_step_spin.value()),  # No conversion: 0=restart, 1=step1, 2=step2...
            "timeout_goto_enabled": bool(self.timeout_goto_checkbox.isChecked()),
            "timeout_goto_step_index": int(self.timeout_goto_spin.value()),  # No conversion: 0=restart, 1=step1, 2=step2...
            "template_matching_algorithms": getattr(self.action, 'template_matching_algorithms', [])
        }
