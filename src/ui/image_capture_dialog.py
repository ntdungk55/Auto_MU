from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QLineEdit, QComboBox, QInputDialog,
                             QDialogButtonBox,
                             QGraphicsView, QGraphicsScene, QMessageBox,
                             QGraphicsRectItem, QGraphicsEllipseItem, QGraphicsLineItem)
from PyQt6.QtCore import QLineF
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, QPointF
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QMouseEvent, QCursor
import win32gui
import win32ui
import win32con
import ctypes
from ctypes import wintypes
import numpy as np
import cv2
import os
from ..logic.window_detector import WindowDetector
from ..logic.app_paths import get_runtime_root
from ..logic.teaching_matching import (
    expand_coordinate_bounds,
    normalize_coordinate_match_offset,
)
try:
    from PIL import Image
    import io
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not found, image saving might be limited.")

# Windows API constants
PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002
user32 = ctypes.windll.user32
user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, ctypes.c_uint]
user32.PrintWindow.restype = wintypes.BOOL

# DPI Awareness constants
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
PROCESS_PER_MONITOR_DPI_AWARE = 2

def _ensure_dpi_awareness():
    """Ensure DPI awareness is set for high-quality screenshots."""
    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Set DPI awareness at module load
_ensure_dpi_awareness()


class CropSaveDialog(QDialog):
    """Choose a managed learning folder and confirm a cropped PNG save."""

    def __init__(self, crop: QPixmap, learning_root: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lưu ảnh teaching")
        self.resize(620, 500)
        self.learning_root = os.path.abspath(learning_root)
        self.selected_path = ""
        os.makedirs(self.learning_root, exist_ok=True)

        layout = QVBoxLayout(self)
        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumSize(400, 300)
        preview.setPixmap(crop.scaled(
            560,
            340,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))
        layout.addWidget(preview, 1)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Loại learning:"))
        self.folder_combo = QComboBox()
        folder_row.addWidget(self.folder_combo, 1)
        new_btn = QPushButton("Thêm")
        new_btn.clicked.connect(self._create_folder)
        rename_btn = QPushButton("Đổi tên")
        rename_btn.clicked.connect(self._rename_folder)
        delete_btn = QPushButton("Xóa")
        delete_btn.clicked.connect(self._delete_folder)
        folder_row.addWidget(new_btn)
        folder_row.addWidget(rename_btn)
        folder_row.addWidget(delete_btn)
        layout.addLayout(folder_row)

        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("Tên file, không cần nhập .png")
        layout.addWidget(QLabel("Tên file:"))
        layout.addWidget(self.filename_edit)
        self._refresh_folders()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_path)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _refresh_folders(self, select_name: str | None = None) -> None:
        current = select_name or self.folder_combo.currentText()
        folders = sorted(
            name for name in os.listdir(self.learning_root)
            if os.path.isdir(os.path.join(self.learning_root, name))
        )
        self.folder_combo.blockSignals(True)
        self.folder_combo.clear()
        self.folder_combo.addItems(folders)
        if current in folders:
            self.folder_combo.setCurrentText(current)
        self.folder_combo.blockSignals(False)

    def _folder_name(self, title: str, label: str, initial: str = "") -> str:
        name, accepted = QInputDialog.getText(self, title, label, text=initial)
        return name.strip() if accepted else ""

    def _valid_folder_name(self, name: str) -> bool:
        return bool(name) and name not in {".", ".."} and os.path.basename(name) == name

    def _create_folder(self) -> None:
        name = self._folder_name("Thêm loại learning", "Tên thư mục:")
        if not self._valid_folder_name(name):
            return
        path = os.path.join(self.learning_root, name)
        if os.path.exists(path):
            QMessageBox.warning(self, "Trùng tên", "Thư mục này đã tồn tại.")
            return
        os.makedirs(path)
        self._refresh_folders(name)

    def _rename_folder(self) -> None:
        old_name = self.folder_combo.currentText().strip()
        if not old_name:
            return
        new_name = self._folder_name("Đổi tên loại learning", "Tên mới:", old_name)
        if not self._valid_folder_name(new_name) or new_name == old_name:
            return
        new_path = os.path.join(self.learning_root, new_name)
        if os.path.exists(new_path):
            QMessageBox.warning(self, "Trùng tên", "Thư mục này đã tồn tại.")
            return
        os.rename(os.path.join(self.learning_root, old_name), new_path)
        self._refresh_folders(new_name)

    def _delete_folder(self) -> None:
        name = self.folder_combo.currentText().strip()
        if not name:
            return
        folder = os.path.join(self.learning_root, name)
        answer = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Xóa thư mục learning '{name}' và toàn bộ ảnh bên trong?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        import shutil
        shutil.rmtree(folder)
        self._refresh_folders()

    def _accept_path(self) -> None:
        folder = self.folder_combo.currentText().strip()
        filename = self.filename_edit.text().strip()
        if not folder:
            QMessageBox.warning(self, "Thiếu loại learning", "Hãy tạo hoặc chọn một thư mục learning.")
            return
        if not filename:
            QMessageBox.warning(self, "Thiếu tên file", "Vui lòng nhập tên file.")
            return
        if os.path.basename(filename) != filename or filename in {".", ".."}:
            QMessageBox.warning(self, "Tên file không hợp lệ", "Chỉ được nhập tên file, không nhập đường dẫn.")
            return
        if not filename.lower().endswith(".png"):
            filename += ".png"
        self.selected_path = os.path.join(self.learning_root, folder, filename)
        self.accept()

class ImageGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_rect = None
        self.click_point = None
        self.drawing_selection = False
        self.selecting_click_point = False
        self.start_pos = None
        # Graphics items để vẽ selection và click point
        self.selection_item = None
        self.coordinate_offset_item = None
        self.click_item = None  # Có thể là list nếu có nhiều items
        self._parent_dialog = None  # Reference to parent dialog for updating title
        self._temp_mask_item = None  # Temporary mask visual during drawing
        
        # Cải thiện chất lượng hiển thị
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    
    def wheelEvent(self, event):
        """Zoom in/out với mouse wheel."""
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            self.scale(zoom_factor, zoom_factor)
        else:
            self.scale(1 / zoom_factor, 1 / zoom_factor)
        
        # Update zoom level in title
        self._update_zoom_title()
    
    def _update_zoom_title(self):
        """Update parent dialog title with current zoom level."""
        if self._parent_dialog and hasattr(self._parent_dialog, 'captured_image'):
            pixmap = self._parent_dialog.captured_image
            if pixmap:
                # Get current scale from transform matrix
                transform = self.transform()
                scale = transform.m11()  # Horizontal scale factor
                zoom_percent = int(scale * 100)
                img_width = pixmap.width()
                img_height = pixmap.height()
                self._parent_dialog.setWindowTitle(
                    f"Capture & Chọn Ảnh - {img_width}x{img_height} ({zoom_percent}%)"
                )
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if in mask drawing mode
            if self._parent_dialog and self._parent_dialog.drawing_mask:
                self.start_pos = event.pos()
                return
            
            if self.drawing_selection:
                self.start_pos = event.pos()
                # Bắt đầu vẽ selection rect ngay khi click
                self.selection_rect = None
                self.update_selection_rect()
            elif self.selecting_click_point:
                scene_pos = self.mapToScene(event.pos())
                self.click_point = scene_pos
                self.update_click_point()
                
                # Debug: In ra tọa độ để kiểm tra
                print(f"[DEBUG Click] View pos: {event.pos().x()}, {event.pos().y()}")
                print(f"[DEBUG Click] Scene pos: {scene_pos.x()}, {scene_pos.y()}")
                if self._parent_dialog and self._parent_dialog.captured_image:
                    img = self._parent_dialog.captured_image
                    print(f"[DEBUG Click] Image size: {img.width()}x{img.height()}")
            else:
                # Check if clicking on mask to select
                if self._parent_dialog:
                    scene_pos = self.mapToScene(event.pos())
                    self._parent_dialog.select_mask_at_pos(scene_pos)
        elif event.button() == Qt.MouseButton.RightButton:
            # Right click on mask to delete
            if self._parent_dialog and self._parent_dialog.selected_mask_index is not None:
                from PyQt6.QtWidgets import QMenu
                menu = QMenu()
                delete_action = menu.addAction("Xóa mask")
                action = menu.exec(event.globalPosition().toPoint())
                if action == delete_action:
                    self._parent_dialog.delete_selected_mask()
                return
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        # Handle mask drawing - DON'T use selection_rect for mask
        if self._parent_dialog and self._parent_dialog.drawing_mask and self.start_pos:
            # Draw temporary mask rect using a separate temp item
            end_pos = event.pos()
            scene_start = self.mapToScene(self.start_pos)
            scene_end = self.mapToScene(end_pos)
            temp_rect = QRectF(
                min(scene_start.x(), scene_end.x()),
                min(scene_start.y(), scene_end.y()),
                abs(scene_end.x() - scene_start.x()),
                abs(scene_end.y() - scene_start.y())
            )
            # Update visual feedback for mask (separate from selection)
            self._update_temp_mask_visual(temp_rect)
            return
        
        if self.drawing_selection and self.start_pos:
            end_pos = event.pos()
            scene_start = self.mapToScene(self.start_pos)
            scene_end = self.mapToScene(end_pos)
            self.selection_rect = QRectF(
                min(scene_start.x(), scene_end.x()),
                min(scene_start.y(), scene_end.y()),
                abs(scene_end.x() - scene_start.x()),
                abs(scene_end.y() - scene_start.y())
            )
            self.update_selection_rect()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # Handle mask drawing completion
            if self._parent_dialog and self._parent_dialog.drawing_mask and self.start_pos:
                end_pos = event.pos()
                scene_start = self.mapToScene(self.start_pos)
                scene_end = self.mapToScene(end_pos)
                mask_rect = QRectF(
                    min(scene_start.x(), scene_end.x()),
                    min(scene_start.y(), scene_end.y()),
                    abs(scene_end.x() - scene_start.x()),
                    abs(scene_end.y() - scene_start.y())
                )
                # Add mask rect to dialog
                self._parent_dialog.add_mask_rect(mask_rect)
                # Clear temporary mask visual
                self._clear_temp_mask_visual()
                self.start_pos = None
                return
            
            if self.drawing_selection:
                if self.start_pos:
                    # Hoàn thành vẽ selection
                    end_pos = event.pos()
                    scene_start = self.mapToScene(self.start_pos)
                    scene_end = self.mapToScene(end_pos)
                    self.selection_rect = QRectF(
                        min(scene_start.x(), scene_end.x()),
                        min(scene_start.y(), scene_end.y()),
                        abs(scene_end.x() - scene_start.x()),
                        abs(scene_end.y() - scene_start.y())
                    )
                    self.update_selection_rect()
                self.start_pos = None
                # Giữ chế độ drawing_selection để có thể vẽ lại nếu cần
                # Chỉ reset cursor khi người dùng tắt chế độ
        super().mouseReleaseEvent(event)
    
    def keyPressEvent(self, event):
        """Handle Delete key to remove selected mask."""
        if event.key() == Qt.Key.Key_Delete:
            if self._parent_dialog:
                self._parent_dialog.delete_selected_mask()
        super().keyPressEvent(event)
    
    def _update_temp_mask_visual(self, rect: QRectF):
        """Update temporary mask visual during drawing (separate from selection)."""
        scene = self.scene if hasattr(self, 'scene') else super().scene()
        if not scene:
            return
        
        # Remove old temp mask item
        if self._temp_mask_item:
            scene.removeItem(self._temp_mask_item)
            self._temp_mask_item = None
        
        # Create new temp mask item
        if rect and not rect.isEmpty() and rect.width() > 0 and rect.height() > 0:
            self._temp_mask_item = QGraphicsRectItem(rect)
            pen = QPen(QColor(255, 165, 0), 1)
            pen.setCosmetic(True)
            pen.setStyle(Qt.PenStyle.DashLine)
            self._temp_mask_item.setPen(pen)
            self._temp_mask_item.setBrush(QColor(255, 165, 0, 50))  # Orange semi-transparent
            self._temp_mask_item.setZValue(1002)  # Above everything
            scene.addItem(self._temp_mask_item)
    
    def _clear_temp_mask_visual(self):
        """Clear temporary mask visual."""
        scene = self.scene if hasattr(self, 'scene') else super().scene()
        if not scene:
            return
        
        if self._temp_mask_item:
            scene.removeItem(self._temp_mask_item)
            self._temp_mask_item = None
    
    def update_selection_rect(self):
        """Cập nhật graphics item cho selection rect"""
        # Lấy scene từ attribute hoặc method
        if hasattr(self, 'scene'):
            scene = self.scene  # Nếu đã lưu reference
        else:
            scene = super().scene()  # Dùng method từ QGraphicsView
        
        if not scene:
            return
        
        # Xóa item cũ nếu có
        if self.selection_item:
            scene.removeItem(self.selection_item)
            self.selection_item = None
        if self.coordinate_offset_item:
            scene.removeItem(self.coordinate_offset_item)
            self.coordinate_offset_item = None
        
        # Tạo item mới nếu có selection_rect và không rỗng
        if self.selection_rect and not self.selection_rect.isEmpty():
            # Đảm bảo rect có kích thước tối thiểu
            if self.selection_rect.width() > 0 and self.selection_rect.height() > 0:
                self.selection_item = QGraphicsRectItem(self.selection_rect)
                # Vẽ viền đỏ đậm và nền trong suốt
                pen = QPen(QColor(255, 0, 0), 1)
                pen.setCosmetic(True)
                pen.setStyle(Qt.PenStyle.DashLine)  # Đường nét đứt
                self.selection_item.setPen(pen)
                self.selection_item.setBrush(QColor(255, 0, 0, 50))  # Nền đỏ trong suốt
                self.selection_item.setZValue(1000)  # Đảm bảo vẽ trên cùng
                scene.addItem(self.selection_item)

                parent_dialog = self._parent_dialog
                offset = getattr(parent_dialog, "coordinate_match_offset", 0)
                captured_image = getattr(parent_dialog, "captured_image", None)
                if offset > 0 and captured_image is not None:
                    bounds = expand_coordinate_bounds(
                        self.selection_rect.left(),
                        self.selection_rect.top(),
                        self.selection_rect.right(),
                        self.selection_rect.bottom(),
                        offset,
                        captured_image.width(),
                        captured_image.height(),
                    )
                    if bounds:
                        left, top, right, bottom = bounds
                        offset_rect = QRectF(left, top, right - left, bottom - top)
                        self.coordinate_offset_item = QGraphicsRectItem(offset_rect)
                        offset_pen = QPen(QColor(255, 214, 10), 1)
                        offset_pen.setCosmetic(True)
                        offset_pen.setStyle(Qt.PenStyle.DashLine)
                        self.coordinate_offset_item.setPen(offset_pen)
                        self.coordinate_offset_item.setZValue(1001)
                        scene.addItem(self.coordinate_offset_item)
    
    def update_click_point(self):
        """Cập nhật graphics item cho click point"""
        # Lấy scene từ attribute hoặc method
        if hasattr(self, 'scene'):
            scene = self.scene  # Nếu đã lưu reference
        else:
            scene = super().scene()  # Dùng method từ QGraphicsView
        
        if not scene:
            return
        
        # Xóa item cũ nếu có (có thể là list hoặc single item)
        if self.click_item:
            if isinstance(self.click_item, list):
                for item in self.click_item:
                    scene.removeItem(item)
            else:
                scene.removeItem(self.click_item)
            self.click_item = None
        
        # Tạo item mới nếu có click_point
        if self.click_point:
            # Tạo dấu chéo (crosshair) tại điểm click để dễ nhìn hơn
            radius = 8
            
            # Tạo 2 đường chéo tạo thành dấu X
            line1 = QGraphicsLineItem(
                QLineF(
                    self.click_point.x() - radius,
                    self.click_point.y() - radius,
                    self.click_point.x() + radius,
                    self.click_point.y() + radius
                )
            )
            line2 = QGraphicsLineItem(
                QLineF(
                    self.click_point.x() - radius,
                    self.click_point.y() + radius,
                    self.click_point.x() + radius,
                    self.click_point.y() - radius
                )
            )
            
            # Tạo ellipse nhỏ ở giữa
            rect = QRectF(
                self.click_point.x() - radius,
                self.click_point.y() - radius,
                radius * 2,
                radius * 2
            )
            ellipse = QGraphicsEllipseItem(rect)
            
            # Style cho tất cả items
            pen = QPen(QColor(0, 255, 0), 1)
            pen.setCosmetic(True)
            brush = QColor(0, 255, 0, 100)  # Màu xanh trong suốt
            
            line1.setPen(pen)
            line2.setPen(pen)
            ellipse.setPen(pen)
            ellipse.setBrush(brush)
            
            # Thêm vào scene
            scene.addItem(line1)
            scene.addItem(line2)
            scene.addItem(ellipse)
            
            # Lưu tất cả items để có thể xóa sau
            self.click_item = [line1, line2, ellipse]
            
            # Set z-value để vẽ trên cùng
            for item in self.click_item:
                item.setZValue(1001)

class ImageCaptureDialog(QDialog):
    def __init__(
        self,
        target_window_hwnd: int = None,
        parent=None,
        tool_id: str = None,  # UUID of the tool
        hide_click_selection: bool = False,
        hide_region_selection: bool = False,
        initial_image_path: str = None,
        initial_click_x: int = None,
        initial_click_y: int = None,
        initial_mask_regions: list = None,
        coordinate_match_offset: int = 0,
        manual_save: bool = False,
    ):
        super().__init__(parent)
        self.target_window_hwnd = target_window_hwnd
        self.tool_id = tool_id  # UUID instead of name
        self.captured_image = None
        self._captured_bgr = None  # BGR array để save (giống runtime capture)
        self.selection_rect = None
        self.click_point = None
        self.drawing_selection = False
        self.selecting_click_point = False
        self.hide_click_selection = hide_click_selection  # Ẩn nút chọn điểm click nếu True
        self.hide_region_selection = hide_region_selection  # Ẩn nút chọn vùng nếu True
        self.coordinate_match_offset = (
            normalize_coordinate_match_offset(coordinate_match_offset)
            if coordinate_match_offset
            else 0
        )
        self.manual_save = manual_save
        self._loaded_from_existing = False  # Track if loaded from existing file
        self._existing_image_path = initial_image_path  # Store original path
        
        # Mask regions support
        self.drawing_mask = False
        self.mask_rect_items = []  # List of QGraphicsRectItem for mask regions
        self.selected_mask_index = None  # Index of selected mask
        self.mask_start_pos = None  # Start position when drawing mask
        
        self.setWindowTitle("Capture & Chọn Ảnh")
        self.setFixedSize(800, 600)
        self.init_ui()

        # Load existing teaching image if provided
        if initial_image_path:
            # Normalize path for Windows and make absolute
            normalized_path = os.path.normpath(initial_image_path)
            if not os.path.isabs(normalized_path):
                # Make absolute relative to current working directory
                normalized_path = os.path.abspath(normalized_path)
            print(f"[DEBUG] Checking teaching image: {normalized_path}")
            print(f"[DEBUG] File exists: {os.path.exists(normalized_path)}")
            if os.path.exists(normalized_path):
                print(f"[DEBUG] Loading teaching image: {normalized_path}")
                try:
                    pm = QPixmap(normalized_path)
                    print(f"[DEBUG] QPixmap loaded: isNull={pm.isNull()}, size={pm.width()}x{pm.height()}")
                    if not pm.isNull():
                        self.captured_image = pm
                        self._loaded_from_existing = True  # Mark as loaded from existing
                        
                        # Load BGR data from file for saving later
                        # Use imdecode for Unicode path support (cv2.imread corrupts Unicode paths on Windows)
                        with open(normalized_path, 'rb') as f:
                            file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
                        bgr = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                        if bgr is not None:
                            self._captured_bgr = bgr
                            print(f"[DEBUG] BGR data loaded: {bgr.shape}")
                        
                        # Display image (this will reset click_point)
                        self.display_image(pm)
                        print(f"[DEBUG] Image displayed")

                        # Restore click point AFTER display (tọa độ trong ảnh crop)
                        if (initial_click_x is not None) and (initial_click_y is not None) and (not self.hide_click_selection):
                            try:
                                self.graphics_view.click_point = QPointF(float(initial_click_x), float(initial_click_y))
                                self.graphics_view.update_click_point()
                                print(f"[DEBUG] Restored click point: ({initial_click_x}, {initial_click_y})")
                            except Exception as e:
                                print(f"[WARN] Cannot restore click point: {e}")

                        # Enable buttons as if we already captured
                        self.select_region_btn.setEnabled(True)
                        self.select_click_btn.setEnabled(True and (not self.hide_click_selection))
                        self.draw_mask_btn.setEnabled(True)
                        self.clear_masks_btn.setEnabled(True)
                        self.clear_btn.setEnabled(True)
                        self.ok_btn.setEnabled(True)
                        print(f"[DEBUG] Buttons enabled")
                        
                        # Load mask regions if provided
                        if initial_mask_regions:
                            print(f"[DEBUG] Loading {len(initial_mask_regions)} mask regions")
                            # Check if we have teaching corners (crop info)
                            # If we have corners, mask regions are relative to crop
                            # Need to convert back to absolute for display
                            has_crop = (hasattr(self, '_teaching_corners') and 
                                       self._teaching_corners and 
                                       all(c is not None for c in self._teaching_corners))
                            
                            for region in initial_mask_regions:
                                try:
                                    x = float(region.get("x", 0))
                                    y = float(region.get("y", 0))
                                    w = float(region.get("w", 0))
                                    h = float(region.get("h", 0))
                                    
                                    # Mask regions are stored relative to cropped image
                                    # But displayed image is the cropped version
                                    # So coordinates are already correct - no conversion needed!
                                    rect = QRectF(x, y, w, h)
                                    self.add_mask_rect(rect)
                                except Exception as e:
                                    print(f"[WARN] Cannot load mask region: {e}")
                
                except Exception as e:
                    print(f"[WARN] Không load được teaching image: {e}")
            else:
                print(f"[WARN] Teaching image not found: {normalized_path}")

    @staticmethod
    def _sanitize_tool_folder_name(name: str) -> str:
        """Windows-safe folder name for storing teaching images under images/<tool_name>/."""
        try:
            s = str(name or "").strip()
        except Exception:
            s = ""
        if not s:
            return ""
        # Remove invalid characters for Windows file/folder names: <>:"/\\|?*
        bad = '<>:"/\\\\|?*'
        for ch in bad:
            s = s.replace(ch, "_")
        # Avoid trailing dots/spaces (Windows doesn't like them)
        s = s.strip(" .")
        # Collapse consecutive spaces
        while "  " in s:
            s = s.replace("  ", " ")
        return s
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.capture_btn = QPushButton("Chụp ảnh")
        self.capture_btn.clicked.connect(self.capture_screenshot)
        self.select_region_btn = QPushButton("Chọn vùng")
        self.select_region_btn.clicked.connect(self.enable_region_selection)
        self.select_click_btn = QPushButton("Chọn điểm click")
        self.select_click_btn.clicked.connect(self.enable_click_selection)
        self.draw_mask_btn = QPushButton("Vẽ Mask")
        self.draw_mask_btn.clicked.connect(self.toggle_mask_drawing)
        self.clear_masks_btn = QPushButton("Xóa tất cả mask")
        self.clear_masks_btn.clicked.connect(self.clear_all_masks)
        self.clear_btn = QPushButton("Xóa")
        self.clear_btn.clicked.connect(self.clear_selection)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.capture_btn)
        btn_layout.addWidget(self.select_region_btn)
        btn_layout.addWidget(self.select_click_btn)
        btn_layout.addWidget(self.draw_mask_btn)
        btn_layout.addWidget(self.clear_masks_btn)
        btn_layout.addWidget(self.clear_btn)
        if self.manual_save:
            self.save_crop_btn = QPushButton("Lưu ảnh")
            self.save_crop_btn.clicked.connect(self._save_cropped_image_as)
            btn_layout.addWidget(self.save_crop_btn)
        
        # Zoom buttons
        self.zoom_100_btn = QPushButton("100%")
        self.zoom_100_btn.setToolTip("Hiển thị ảnh ở kích thước gốc (1:1)")
        self.zoom_100_btn.clicked.connect(self.zoom_100)
        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.setToolTip("Fit ảnh vào view")
        self.zoom_fit_btn.clicked.connect(self.zoom_fit)
        btn_layout.addWidget(self.zoom_100_btn)
        btn_layout.addWidget(self.zoom_fit_btn)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        # Ẩn nút chọn điểm click nếu hide_click_selection = True
        if self.hide_click_selection:
            self.select_click_btn.setVisible(False)
        
        # Ẩn nút chọn vùng nếu hide_region_selection = True
        if self.hide_region_selection:
            self.select_region_btn.setVisible(False)
        
        # Graphics view
        self.scene = QGraphicsScene()
        self.graphics_view = ImageGraphicsView()
        self.graphics_view.setScene(self.scene)
        self.graphics_view.setDragMode(QGraphicsView.DragMode.NoDrag)
        # Lưu reference scene vào graphics_view để dùng trong update methods
        self.graphics_view.scene = self.scene
        # Lưu reference dialog để update title khi zoom
        self.graphics_view._parent_dialog = self
        layout.addWidget(self.graphics_view)
        
        self.setLayout(layout)
        
        # Disable buttons until capture
        self.select_region_btn.setEnabled(False)
        self.select_click_btn.setEnabled(False)
        self.draw_mask_btn.setEnabled(False)
        self.clear_masks_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)

    def _current_crop_pixmap(self) -> QPixmap | None:
        if self.captured_image is None or self.captured_image.isNull():
            return None
        selection_rect = self.graphics_view.selection_rect
        if selection_rect is None or selection_rect.isEmpty():
            return self.captured_image
        image_rect = QRectF(0, 0, self.captured_image.width(), self.captured_image.height())
        crop_rect = selection_rect.intersected(image_rect).toRect()
        if crop_rect.isEmpty():
            return None
        return self.captured_image.copy(crop_rect)

    def _save_cropped_image_as(self) -> None:
        crop = self._current_crop_pixmap()
        if crop is None:
            QMessageBox.warning(self, "Chưa có ảnh", "Hãy chụp ảnh và chọn vùng crop trước.")
            return
        learning_root = os.path.join(get_runtime_root(), "images", "learning")
        dialog = CropSaveDialog(crop, learning_root, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        path = dialog.selected_path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not crop.save(path, "PNG"):
            QMessageBox.critical(self, "Lỗi lưu ảnh", f"Không thể lưu ảnh:\n{path}")
            return
        QMessageBox.information(self, "Đã lưu ảnh", f"Đã lưu ảnh teaching:\n{path}")
    
    def capture_screenshot(self):
        """Chụp screenshot của window"""
        if not self.target_window_hwnd:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn window!")
            return
        
        # Mark as new capture (not loaded from existing)
        self._loaded_from_existing = False
        self._existing_image_path = None
        
        try:
            rect = win32gui.GetClientRect(self.target_window_hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            
            # Save window size for teaching image metadata
            self._captured_window_width = width
            self._captured_window_height = height
            
            if width <= 0 or height <= 0:
                raise Exception("Window size invalid")
            
            hwndDC = win32gui.GetWindowDC(self.target_window_hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(bitmap)
            
            # Dùng PrintWindow - ưu tiên PW_CLIENTONLY để tọa độ match đúng với runtime
            result = user32.PrintWindow(self.target_window_hwnd, saveDC.GetSafeHdc(), PW_CLIENTONLY)
            
            if not result:
                # Fallback: thử PW_RENDERFULLCONTENT (một số game/DirectX cần)
                result = user32.PrintWindow(self.target_window_hwnd, saveDC.GetSafeHdc(), PW_RENDERFULLCONTENT)
            
            if not result:
                client_rect = win32gui.GetClientRect(self.target_window_hwnd)
                client_x, client_y, client_w, client_h = client_rect
                client_pos = win32gui.ClientToScreen(self.target_window_hwnd, (client_x, client_y))
                
                screen_dc = win32gui.GetWindowDC(0)
                screen_mfc = win32ui.CreateDCFromHandle(screen_dc)
                result = saveDC.BitBlt((0, 0), (width, height), screen_mfc, client_pos, win32con.SRCCOPY)
                screen_mfc.DeleteDC()
                win32gui.ReleaseDC(0, screen_dc)
            
            if result:
                bmp_data = bitmap.GetBitmapBits(True)
                if isinstance(bmp_data, bytes):
                    bmpstr = bmp_data
                elif isinstance(bmp_data, tuple):
                    bmpstr = bytes(bmp_data)
                else:
                    raise Exception(f"Unexpected bitmap data type: {type(bmp_data)}")
                
                # BGRA format từ Windows bitmap
                arr_bgra = np.frombuffer(bmpstr, dtype=np.uint8).reshape((height, width, 4))
                
                # Lưu BGR array để dùng khi save (giống runtime capture)
                self._captured_bgr = arr_bgra[:, :, :3].copy()  # BGR (3 channels đầu của BGRA)
                
                # Chuyển BGRA sang RGB cho QImage hiển thị
                arr_rgb = arr_bgra[:, :, [2, 1, 0]].copy()  # BGRA -> RGB (bỏ alpha)
                
                # Dùng Format_RGB888 cho QImage
                bytes_per_line = width * 3
                img = QImage(arr_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
                img._arr = arr_rgb  # Giữ reference để tránh garbage collection
                
                self.captured_image = QPixmap.fromImage(img)
            else:
                raise Exception("Không thể copy window content")
            
            win32gui.DeleteObject(bitmap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.target_window_hwnd, hwndDC)
            
            self.display_image(self.captured_image)
            
            self.select_region_btn.setEnabled(True)
            self.select_click_btn.setEnabled(True)
            self.draw_mask_btn.setEnabled(True)
            self.clear_masks_btn.setEnabled(True)
            self.clear_btn.setEnabled(True)
            self.ok_btn.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể chụp screenshot: {str(e)}")
    
    def display_image(self, pixmap):
        """Hiển thị ảnh trong graphics view với chất lượng cao.
        
        Ảnh được hiển thị ở tỷ lệ 1:1 (100%) để giữ nguyên chất lượng.
        User có thể zoom in/out bằng mouse wheel.
        """
        self.scene.clear()
        
        # Thêm pixmap vào scene
        pixmap_item = self.scene.addPixmap(pixmap)
        # Bật smooth transformation cho pixmap item
        pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        
        # Reset transform
        self.graphics_view.resetTransform()
        
        # Tính toán scale để hiển thị tốt nhất
        view_width = self.graphics_view.viewport().width()
        view_height = self.graphics_view.viewport().height()
        img_width = pixmap.width()
        img_height = pixmap.height()
        
        # Nếu ảnh lớn hơn view, fit vào view nhưng không scale quá nhỏ
        # Nếu ảnh nhỏ hơn view, hiển thị 1:1
        scale_x = view_width / img_width if img_width > 0 else 1
        scale_y = view_height / img_height if img_height > 0 else 1
        scale = min(scale_x, scale_y, 1.0)  # Không scale lớn hơn 1:1
        
        # Nếu scale quá nhỏ (< 0.5), hiển thị ở 50% để vẫn thấy chi tiết
        if scale < 0.5:
            scale = 0.5
        
        self.graphics_view.scale(scale, scale)
        
        # Center ảnh trong view
        self.graphics_view.centerOn(pixmap_item)
        
        # Hiển thị thông tin zoom level
        zoom_percent = int(scale * 100)
        self.setWindowTitle(f"Capture & Chọn Ảnh - {img_width}x{img_height} ({zoom_percent}%)")
        
        # Reset selection khi hiển thị ảnh mới
        self.graphics_view.selection_rect = None
        self.graphics_view.click_point = None
        self.graphics_view.start_pos = None
        self.graphics_view.selection_item = None
        self.graphics_view.coordinate_offset_item = None
        self.graphics_view.click_item = None
        self.selection_rect = None
        self.click_point = None
    
    def enable_region_selection(self):
        """Bật chế độ chọn vùng"""
        self.graphics_view.drawing_selection = True
        self.graphics_view.selecting_click_point = False
        self.graphics_view.start_pos = None
        # Thay đổi cursor thành crosshair khi chọn vùng (dấu +)
        self.graphics_view.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.select_region_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.select_click_btn.setStyleSheet("")
    
    def enable_click_selection(self):
        """Bật chế độ chọn điểm click"""
        self.graphics_view.drawing_selection = False
        self.graphics_view.selecting_click_point = True
        # Thay đổi cursor thành pointing hand để chỉ ra đang chọn điểm
        self.graphics_view.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.select_click_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.select_region_btn.setStyleSheet("")
    
    def clear_selection(self):
        """Xóa selection và click point"""
        self.selection_rect = None
        self.click_point = None
        self.graphics_view.selection_rect = None
        self.graphics_view.click_point = None
        self.graphics_view.start_pos = None
        self.graphics_view.drawing_selection = False
        self.graphics_view.selecting_click_point = False
        # Xóa graphics items
        self.graphics_view.update_selection_rect()
        self.graphics_view.update_click_point()
        # Reset cursor
        self.graphics_view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        self.select_region_btn.setStyleSheet("")
        self.select_click_btn.setStyleSheet("")
    
    def zoom_100(self):
        """Zoom về 100% (1:1 pixel)."""
        if not self.captured_image:
            return
        self.graphics_view.resetTransform()
        self._update_title()
    
    def zoom_fit(self):
        """Fit ảnh vào view."""
        if not self.captured_image:
            return
        self.graphics_view.resetTransform()
        self.graphics_view.fitInView(
            self.scene.itemsBoundingRect(), 
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self._update_title()
    
    def _update_title(self):
        """Update window title với zoom level hiện tại."""
        if self.captured_image:
            transform = self.graphics_view.transform()
            scale = transform.m11()
            zoom_percent = int(scale * 100)
            img_width = self.captured_image.width()
            img_height = self.captured_image.height()
            self.setWindowTitle(
                f"Capture & Chọn Ảnh - {img_width}x{img_height} ({zoom_percent}%)"
            )
    
    def get_cropped_image_path(self) -> tuple:
        """Trả về (image_path, click_x, click_y, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height) của ảnh đã crop.
        
        click_x, click_y là tọa độ relative to góc trên bên trái của ảnh đã crop.
        corner_x1, corner_y1, corner_x2, corner_y2 là tọa độ selection rect trên ảnh gốc.
        window_width, window_height là kích thước window khi chụp teaching image.
        """
        if not self.captured_image:
            return None, None, None, None, None, None, None, None, None
        
        # Lấy selection rect từ graphics_view (đảm bảo lấy giá trị mới nhất)
        selection_rect = self.graphics_view.selection_rect
        click_point = self.graphics_view.click_point
        
        # Sync với dialog
        self.selection_rect = selection_rect
        self.click_point = click_point
        
        # Lấy kích thước ảnh gốc
        original_image_width = self.captured_image.width()
        original_image_height = self.captured_image.height()
        
        # Chuyển QRect sang QRectF nếu cần
        if selection_rect:
            if isinstance(selection_rect, QRect):
                selection_rect = QRectF(selection_rect)
            # Đảm bảo rect nằm trong phạm vi ảnh gốc
            img_rect = QRectF(0, 0, original_image_width, original_image_height)
            selection_rect = selection_rect.intersected(img_rect)
        
        # Save teaching images under images/teaching/<tool_id>/ if tool_id is provided
        # If loaded from existing and no new capture, return existing path
        if self._loaded_from_existing and self._existing_image_path:
            print(f"[DEBUG] Reusing existing image path: {self._existing_image_path}")
            filepath = self._existing_image_path
            cropped_width = self.captured_image.width()
            cropped_height = self.captured_image.height()
        else:
            # Save new file
            base_dir = os.path.join("images", "teaching")
            # Use tool_id as folder name (UUID)
            images_dir = os.path.join(base_dir, self.tool_id) if self.tool_id else base_dir
            # Make absolute path to ensure consistency
            images_dir = os.path.abspath(images_dir)
            os.makedirs(images_dir, exist_ok=True)
            
            import time
            filename = f"capture_{int(time.time())}.png"
            filepath = os.path.join(images_dir, filename)
        
        # Dùng _captured_bgr nếu có (ảnh mới capture)
        # Nếu không có (ảnh load từ file), dùng QPixmap convert
        if not self._loaded_from_existing and hasattr(self, '_captured_bgr') and self._captured_bgr is not None:
            # Dùng trực tiếp BGR array đã capture
            bgr_full = self._captured_bgr
            
            if selection_rect and not selection_rect.isEmpty():
                # Crop từ BGR array
                x1 = int(selection_rect.x())
                y1 = int(selection_rect.y())
                x2 = int(selection_rect.x() + selection_rect.width())
                y2 = int(selection_rect.y() + selection_rect.height())
                
                # Clamp vào trong ảnh
                h, w = bgr_full.shape[:2]
                x1 = max(0, min(x1, w - 1))
                y1 = max(0, min(y1, h - 1))
                x2 = max(x1 + 1, min(x2, w))
                y2 = max(y1 + 1, min(y2, h))
                
                bgr_cropped = bgr_full[y1:y2, x1:x2].copy()
            else:
                bgr_cropped = bgr_full
            
            # Save bằng imencode + open() để hỗ trợ Unicode path
            # cv2.imwrite không hỗ trợ Unicode path trên Windows
            try:
                _, buffer = cv2.imencode('.png', bgr_cropped)
                with open(filepath, 'wb') as f:
                    f.write(buffer)
                print(f"[DEBUG] Saved using imencode: {filepath}")
            except Exception as e:
                print(f"[ERROR] Failed to save image: {e}")
                # Fallback: try cv2.imwrite anyway
                cv2.imwrite(filepath, bgr_cropped)
            
            cropped_width = bgr_cropped.shape[1]
            cropped_height = bgr_cropped.shape[0]
            
            print(f"[DEBUG Teaching] Saved from BGR array: {filepath}")
            print(f"[DEBUG Teaching] Size: {cropped_width}x{cropped_height}")
            
            # Verify file was saved
            if os.path.exists(filepath):
                print(f"[DEBUG] File verified: {filepath}")
            else:
                print(f"[ERROR] File NOT saved: {filepath}")
        else:
            # Fallback: convert từ QPixmap (cho trường hợp load ảnh cũ)
            if selection_rect and not selection_rect.isEmpty():
                crop_rect = QRect(
                    int(selection_rect.x()),
                    int(selection_rect.y()),
                    int(selection_rect.width()),
                    int(selection_rect.height())
                )
                cropped = self.captured_image.copy(crop_rect)
            else:
                cropped = self.captured_image
            
            # Convert QPixmap -> numpy BGR
            qimg = cropped.toImage()
            qimg = qimg.convertToFormat(QImage.Format.Format_RGB888)
            
            width = qimg.width()
            height = qimg.height()
            bytes_per_line = qimg.bytesPerLine()
            
            ptr = qimg.bits()
            ptr.setsize(height * bytes_per_line)
            arr = np.array(ptr).reshape((height, bytes_per_line))
            arr_rgb = arr[:, :width * 3].reshape((height, width, 3))
            bgr_cropped = cv2.cvtColor(arr_rgb, cv2.COLOR_RGB2BGR)
            
            # Save bằng imencode + open() để hỗ trợ Unicode path
            try:
                _, buffer = cv2.imencode('.png', bgr_cropped)
                with open(filepath, 'wb') as f:
                    f.write(buffer)
                print(f"[DEBUG] Saved using imencode: {filepath}")
            except Exception as e:
                print(f"[ERROR] Failed to save image: {e}")
                cv2.imwrite(filepath, bgr_cropped)
            
            cropped_width = width
            cropped_height = height
            
            print(f"[DEBUG Teaching] Saved from QPixmap: {filepath}")
            print(f"[DEBUG Teaching] Size: {cropped_width}x{cropped_height}")
        
        # Tính click point relative to cropped image
        click_x = None
        click_y = None
        if click_point:
            print(f"[DEBUG get_cropped] click_point in scene: ({click_point.x()}, {click_point.y()})")
            print(f"[DEBUG get_cropped] selection_rect: {selection_rect}")
            print(f"[DEBUG get_cropped] cropped image size: {cropped_width}x{cropped_height}")
            
            if selection_rect and not selection_rect.isEmpty():
                # Click point trong tọa độ scene = tọa độ ảnh gốc
                # Chuyển sang tọa độ relative với ảnh đã crop
                click_x = int(click_point.x() - selection_rect.x())
                click_y = int(click_point.y() - selection_rect.y())
                print(f"[DEBUG get_cropped] click relative to crop: ({click_x}, {click_y})")
                
                # Clamp vào trong cropped image
                click_x = max(0, min(click_x, cropped_width - 1))
                click_y = max(0, min(click_y, cropped_height - 1))
                print(f"[DEBUG get_cropped] after clamp: ({click_x}, {click_y})")
            else:
                # Không có selection rect
                click_x = int(click_point.x())
                click_y = int(click_point.y())
                print(f"[DEBUG get_cropped] no selection, click: ({click_x}, {click_y})")
                
                # Clamp vào trong ảnh
                click_x = max(0, min(click_x, cropped_width - 1))
                click_y = max(0, min(click_y, cropped_height - 1))
                print(f"[DEBUG get_cropped] after clamp: ({click_x}, {click_y})")
        
        # Trả về tọa độ góc của selection rect trên ảnh gốc
        corner_x1, corner_y1, corner_x2, corner_y2 = None, None, None, None
        if selection_rect and not selection_rect.isEmpty():
            corner_x1 = int(selection_rect.x())
            corner_y1 = int(selection_rect.y()) 
            corner_x2 = int(selection_rect.x() + selection_rect.width())
            corner_y2 = int(selection_rect.y() + selection_rect.height())
        
        # Get window size when teaching image was captured
        window_width = getattr(self, '_captured_window_width', None)
        window_height = getattr(self, '_captured_window_height', None)
        
        return filepath, click_x, click_y, corner_x1, corner_y1, corner_x2, corner_y2, window_width, window_height


    def toggle_mask_drawing(self):
        """Toggle mask drawing mode."""
        self.drawing_mask = not self.drawing_mask
        
        if self.drawing_mask:
            self.draw_mask_btn.setText("Tắt Vẽ Mask")
            self.draw_mask_btn.setStyleSheet("background-color: #FF9800; color: white;")  # Orange
            self.graphics_view.setCursor(QCursor(Qt.CursorShape.CrossCursor))
            # Disable region selection mode (but NOT click selection)
            self.graphics_view.drawing_selection = False
            self.select_region_btn.setStyleSheet("")
            # Keep click selection available
        else:
            self.draw_mask_btn.setText("Vẽ Mask")
            self.draw_mask_btn.setStyleSheet("")
            self.graphics_view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    def clear_all_masks(self):
        """Clear all mask regions."""
        for item in self.mask_rect_items:
            self.scene.removeItem(item)
        self.mask_rect_items.clear()
        self.selected_mask_index = None
    
    def add_mask_rect(self, rect: QRectF):
        """Add a mask rectangle to the scene."""
        if rect.isEmpty() or rect.width() < 5 or rect.height() < 5:
            return
        
        # Create mask rect item
        mask_item = QGraphicsRectItem(rect)
        pen = QPen(QColor(255, 0, 0), 1)
        pen.setCosmetic(True)
        mask_item.setPen(pen)
        mask_item.setBrush(QColor(255, 0, 0, 76))  # Red semi-transparent (alpha=0.3*255)
        mask_item.setZValue(999)  # Below selection but above image
        
        self.scene.addItem(mask_item)
        self.mask_rect_items.append(mask_item)
    
    def select_mask_at_pos(self, scene_pos: QPointF) -> bool:
        """Select mask at position. Returns True if mask was selected."""
        for i, item in enumerate(self.mask_rect_items):
            if item.rect().contains(scene_pos):
                # Deselect previous
                if self.selected_mask_index is not None and self.selected_mask_index < len(self.mask_rect_items):
                    old_item = self.mask_rect_items[self.selected_mask_index]
                    old_pen = QPen(QColor(255, 0, 0), 1)
                    old_pen.setCosmetic(True)
                    old_item.setPen(old_pen)
                
                # Select new
                self.selected_mask_index = i
                selected_pen = QPen(QColor(255, 165, 0), 1)
                selected_pen.setCosmetic(True)
                item.setPen(selected_pen)
                return True
        
        # Clicked outside all masks - deselect
        if self.selected_mask_index is not None and self.selected_mask_index < len(self.mask_rect_items):
            old_item = self.mask_rect_items[self.selected_mask_index]
            old_pen = QPen(QColor(255, 0, 0), 1)
            old_pen.setCosmetic(True)
            old_item.setPen(old_pen)
        self.selected_mask_index = None
        return False
    
    def delete_selected_mask(self):
        """Delete currently selected mask."""
        if self.selected_mask_index is not None and self.selected_mask_index < len(self.mask_rect_items):
            item = self.mask_rect_items[self.selected_mask_index]
            self.scene.removeItem(item)
            del self.mask_rect_items[self.selected_mask_index]
            self.selected_mask_index = None
    
    def get_mask_regions(self) -> list:
        """Get mask regions as list of dicts with coordinates relative to cropped image.
        
        If there's a selection_rect (crop), mask coordinates are converted from
        absolute (on original image) to relative (on cropped image).
        """
        mask_regions = []
        
        # Get selection rect to check if we need to convert coordinates
        selection_rect = self.graphics_view.selection_rect
        
        for item in self.mask_rect_items:
            try:
                # Check if item is still valid (not deleted)
                if item.scene() is None:
                    continue
                rect = item.rect()
            except Exception:
                # Skip invalid items
                continue
            
            if selection_rect and not selection_rect.isEmpty():
                # Convert from absolute (original image) to relative (cropped image)
                # Mask rect is in scene coordinates (same as original image)
                # Need to subtract selection_rect offset
                relative_x = int(rect.x() - selection_rect.x())
                relative_y = int(rect.y() - selection_rect.y())
                
                # Clamp to cropped image bounds
                crop_width = int(selection_rect.width())
                crop_height = int(selection_rect.height())
                
                # Skip masks that are completely outside crop region
                if (relative_x + rect.width() < 0 or relative_x >= crop_width or
                    relative_y + rect.height() < 0 or relative_y >= crop_height):
                    continue
                
                # Clip mask to crop boundaries
                clip_x = max(0, relative_x)
                clip_y = max(0, relative_y)
                clip_w = min(int(rect.width()), crop_width - clip_x)
                clip_h = min(int(rect.height()), crop_height - clip_y)
                
                # Adjust width/height if mask starts before crop
                if relative_x < 0:
                    clip_w += relative_x
                if relative_y < 0:
                    clip_h += relative_y
                
                if clip_w > 0 and clip_h > 0:
                    mask_regions.append({
                        "x": clip_x,
                        "y": clip_y,
                        "w": clip_w,
                        "h": clip_h
                    })
            else:
                # No crop, use absolute coordinates
                mask_regions.append({
                    "x": int(rect.x()),
                    "y": int(rect.y()),
                    "w": int(rect.width()),
                    "h": int(rect.height())
                })
        
        return mask_regions
    
    def validate_mask_regions(self) -> bool:
        """Validate that mask regions don't cover > 90% of image."""
        if not self.mask_rect_items or not self.captured_image:
            return True
        
        img_area = self.captured_image.width() * self.captured_image.height()
        masked_area = 0
        for item in self.mask_rect_items:
            try:
                # Check if item is still valid (not deleted)
                if item.scene() is None:
                    continue
                rect = item.rect()
                masked_area += rect.width() * rect.height()
            except Exception:
                # Skip invalid items
                continue
        
        masked_percentage = (masked_area / img_area) * 100
        
        if masked_percentage > 90:
            QMessageBox.warning(
                self,
                "Mask quá nhiều",
                f"Mask phủ {masked_percentage:.1f}% ảnh.\n"
                "Phải còn ít nhất 10% để matching.\n"
                "Vui lòng xóa bớt mask regions."
            )
            return False
        
        return True

    def accept(self):
        """Override accept to validate mask regions before closing."""
        if not self.validate_mask_regions():
            return
        super().accept()
