"""
Image Preprocessing Lab Widget
Allows users to test different preprocessing algorithms on uploaded images.
"""
import cv2
import numpy as np
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox, QSlider, QSpinBox, QDoubleSpinBox,
                            QFileDialog, QGroupBox, QScrollArea, QMessageBox, QListWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
import json
import os


class ImagePreprocessingWidget(QWidget):
    """Widget for testing image preprocessing algorithms."""
    
    # Algorithm definitions with parameters
    ALGORITHMS = {
        "none": {"name": "Không xử lý", "params": []},
        
        # Resize & Scaling
        "upscale_2x": {"name": "Upscale 2x", "params": []},
        "upscale_3x": {"name": "Upscale 3x", "params": []},
        "upscale_4x": {"name": "Upscale 4x", "params": []},
        "downscale_0.5x": {"name": "Downscale 0.5x", "params": []},
        "downscale_0.75x": {"name": "Downscale 0.75x", "params": []},
        
        # Denoise
        "gaussian_blur": {"name": "Gaussian Blur", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 31, "step": 2, "default": 5}
        ]},
        "median_blur": {"name": "Median Blur", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 31, "step": 2, "default": 5}
        ]},
        "bilateral_filter": {"name": "Bilateral Filter", "params": [
            {"name": "d", "label": "Diameter", "type": "int", "min": 1, "max": 15, "default": 9},
            {"name": "sigma_color", "label": "Sigma Color", "type": "int", "min": 10, "max": 200, "default": 75},
            {"name": "sigma_space", "label": "Sigma Space", "type": "int", "min": 10, "max": 200, "default": 75}
        ]},
        "nlmeans_denoise": {"name": "Non-Local Means Denoise", "params": [
            {"name": "h", "label": "Filter Strength", "type": "int", "min": 1, "max": 30, "default": 10},
            {"name": "template_window_size", "label": "Template Window", "type": "int", "min": 3, "max": 11, "step": 2, "default": 7},
            {"name": "search_window_size", "label": "Search Window", "type": "int", "min": 5, "max": 31, "step": 2, "default": 21}
        ]},
        
        # Contrast & Brightness
        "auto_contrast": {"name": "Auto Contrast", "params": []},
        "clahe": {"name": "CLAHE", "params": [
            {"name": "clip_limit", "label": "Clip Limit", "type": "float", "min": 0.1, "max": 10.0, "step": 0.1, "default": 2.0},
            {"name": "tile_grid_size", "label": "Tile Grid Size", "type": "int", "min": 2, "max": 16, "default": 8}
        ]},
        "gamma_correction": {"name": "Gamma Correction", "params": [
            {"name": "gamma", "label": "Gamma", "type": "float", "min": 0.1, "max": 3.0, "step": 0.1, "default": 1.0}
        ]},
        "normalize": {"name": "Normalize (0-255)", "params": []},
        
        # Thresholding
        "binary_threshold": {"name": "Binary Threshold", "params": [
            {"name": "threshold", "label": "Threshold", "type": "int", "min": 0, "max": 255, "default": 127}
        ]},
        "otsu_threshold": {"name": "Otsu Threshold", "params": []},
        "adaptive_mean": {"name": "Adaptive Threshold (Mean)", "params": [
            {"name": "block_size", "label": "Block Size", "type": "int", "min": 3, "max": 99, "step": 2, "default": 11},
            {"name": "C", "label": "Constant C", "type": "int", "min": -20, "max": 20, "default": 2}
        ]},
        "adaptive_gaussian": {"name": "Adaptive Threshold (Gaussian)", "params": [
            {"name": "block_size", "label": "Block Size", "type": "int", "min": 3, "max": 99, "step": 2, "default": 11},
            {"name": "C", "label": "Constant C", "type": "int", "min": -20, "max": 20, "default": 2}
        ]},
        
        # Morphology
        "erosion": {"name": "Erosion", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 21, "step": 2, "default": 3}
        ]},
        "dilation": {"name": "Dilation", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 21, "step": 2, "default": 3}
        ]},
        "opening": {"name": "Opening", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 21, "step": 2, "default": 3}
        ]},
        "closing": {"name": "Closing", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 21, "step": 2, "default": 3}
        ]},
        "tophat": {"name": "Top-Hat (White)", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 51, "step": 2, "default": 11}
        ]},
        "blackhat": {"name": "Black-Hat", "params": [
            {"name": "kernel_size", "label": "Kernel Size", "type": "int", "min": 1, "max": 51, "step": 2, "default": 11}
        ]},
        
        # Sharpening
        "unsharp_mask": {"name": "Unsharp Mask", "params": [
            {"name": "amount", "label": "Amount", "type": "float", "min": 0.1, "max": 3.0, "step": 0.1, "default": 1.0}
        ]},
        "laplacian_sharpen": {"name": "Laplacian Sharpening", "params": []},
        
        # Edge Enhancement
        "canny_edge": {"name": "Canny Edge Detection", "params": [
            {"name": "threshold1", "label": "Threshold 1", "type": "int", "min": 0, "max": 255, "default": 50},
            {"name": "threshold2", "label": "Threshold 2", "type": "int", "min": 0, "max": 255, "default": 150}
        ]},
        "sobel_edge": {"name": "Sobel Edge", "params": []},
        
        # Color Space
        "grayscale": {"name": "Grayscale", "params": []},
        "invert": {"name": "Invert (Negative)", "params": []},
        
        # Skew Correction
        "deskew": {"name": "Deskew (Auto-rotate)", "params": []},
        
        # Combo Pipelines
        "bright_on_dark": {"name": "Combo: Chữ sáng nền tối", "params": []},
        "small_text_noisy": {"name": "Combo: Chữ nhỏ + nhiễu", "params": []},
        "screenshot": {"name": "Combo: Ảnh chụp màn hình", "params": []},
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_image = None  # numpy BGR
        self.processed_image = None  # numpy BGR
        self.pipeline = []  # List of {"algorithm": algo_id, "params": {...}}
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout()
        
        # Top: Load image button
        top_layout = QHBoxLayout()
        self.load_btn = QPushButton("Tải ảnh lên")
        self.load_btn.clicked.connect(self.load_image)
        self.filename_label = QLabel("Chưa tải ảnh")
        top_layout.addWidget(self.load_btn)
        top_layout.addWidget(self.filename_label)
        top_layout.addStretch()
        main_layout.addLayout(top_layout)
        
        # Middle: Original (left) | Processed (right)
        images_layout = QHBoxLayout()
        
        # Original image
        orig_group = QGroupBox("Ảnh gốc")
        orig_layout = QVBoxLayout()
        self.original_label = QLabel("Chưa có ảnh")
        self.original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.original_label.setMinimumSize(400, 300)
        self.original_label.setStyleSheet("border: 1px solid #ccc;")
        orig_layout.addWidget(self.original_label)
        orig_group.setLayout(orig_layout)
        images_layout.addWidget(orig_group)
        
        # Processed image
        proc_group = QGroupBox("Ảnh đã xử lý")
        proc_layout = QVBoxLayout()
        self.processed_label = QLabel("Chưa xử lý")
        self.processed_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.processed_label.setMinimumSize(400, 300)
        self.processed_label.setStyleSheet("border: 1px solid #ccc;")
        proc_layout.addWidget(self.processed_label)
        proc_group.setLayout(proc_layout)
        images_layout.addWidget(proc_group)
        
        main_layout.addLayout(images_layout)
        
        # Bottom: Pipeline controls
        controls_group = QGroupBox("Pipeline Xử Lý")
        controls_layout = QVBoxLayout()
        
        # Add algorithm controls
        add_layout = QHBoxLayout()
        add_layout.addWidget(QLabel("Thêm thuật toán:"))
        self.algo_combo = QComboBox()
        for algo_id, algo_info in self.ALGORITHMS.items():
            if algo_id != "none":  # Skip "none" option
                self.algo_combo.addItem(algo_info["name"], algo_id)
        add_layout.addWidget(self.algo_combo, 1)
        
        self.add_btn = QPushButton("➕ Add")
        self.add_btn.clicked.connect(self.add_algorithm)
        add_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("➖ Remove")
        self.remove_btn.clicked.connect(self.remove_algorithm)
        self.remove_btn.setEnabled(False)
        add_layout.addWidget(self.remove_btn)
        
        controls_layout.addLayout(add_layout)
        
        # Pipeline list
        pipeline_label = QLabel("Pipeline (kéo thả để sắp xếp):")
        controls_layout.addWidget(pipeline_label)
        
        self.pipeline_list = QListWidget()
        self.pipeline_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.pipeline_list.setMaximumHeight(150)
        self.pipeline_list.itemSelectionChanged.connect(self.on_pipeline_selection_changed)
        self.pipeline_list.itemDoubleClicked.connect(self.edit_algorithm_params)
        self.pipeline_list.model().rowsMoved.connect(self.on_pipeline_reordered)
        controls_layout.addWidget(self.pipeline_list)
        
        # Save config button
        save_layout = QHBoxLayout()
        self.save_config_btn = QPushButton("💾 Lưu cấu hình cho OCR")
        self.save_config_btn.clicked.connect(self.save_config)
        self.save_config_btn.setEnabled(False)
        save_layout.addWidget(self.save_config_btn)
        save_layout.addStretch()
        controls_layout.addLayout(save_layout)
        
        controls_group.setLayout(controls_layout)
        main_layout.addWidget(controls_group)
        
        self.setLayout(main_layout)
    
    def load_image(self):
        """Load an image file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.bmp *.tiff)"
        )
        if not filename:
            return
        
        try:
            # Use imdecode for Unicode path support (cv2.imread corrupts Unicode paths on Windows)
            with open(filename, 'rb') as f:
                file_bytes = np.frombuffer(f.read(), dtype=np.uint8)
            self.original_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
            
            if self.original_image is None:
                QMessageBox.warning(self, "Lỗi", "Không thể đọc file ảnh.")
                return
            
            self.filename_label.setText(os.path.basename(filename))
            self.display_image(self.original_image, self.original_label)
            
            # Clear pipeline and reprocess
            self.pipeline.clear()
            self.pipeline_list.clear()
            self.process_image()
            self.save_config_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Lỗi khi tải ảnh: {e}")
    
    def add_algorithm(self):
        """Add selected algorithm to pipeline."""
        algo_id = self.algo_combo.currentData()
        if not algo_id:
            return
        
        # Get default parameters
        algo_info = self.ALGORITHMS.get(algo_id, {})
        params = {}
        for param_def in algo_info.get("params", []):
            params[param_def["name"]] = param_def.get("default", 0)
        
        # Add to pipeline
        self.pipeline.append({"algorithm": algo_id, "params": params})
        
        # Update list display
        algo_name = algo_info["name"]
        self.pipeline_list.addItem(algo_name)
        
        # Process image immediately
        self.process_image()
    
    def remove_algorithm(self):
        """Remove selected algorithm from pipeline."""
        current_row = self.pipeline_list.currentRow()
        if current_row < 0:
            return
        
        # Remove from pipeline
        del self.pipeline[current_row]
        
        # Remove from list display
        self.pipeline_list.takeItem(current_row)
        
        # Process image immediately
        self.process_image()
    
    def on_pipeline_selection_changed(self):
        """Handle pipeline list selection change."""
        has_selection = self.pipeline_list.currentRow() >= 0
        self.remove_btn.setEnabled(has_selection)
    
    def on_pipeline_reordered(self):
        """Handle pipeline reordering via drag & drop."""
        # Rebuild pipeline based on current list order
        new_pipeline = []
        for i in range(self.pipeline_list.count()):
            item_text = self.pipeline_list.item(i).text()
            # Find matching algorithm in old pipeline
            for algo_entry in self.pipeline:
                algo_info = self.ALGORITHMS.get(algo_entry["algorithm"], {})
                if algo_info["name"] == item_text:
                    new_pipeline.append(algo_entry)
                    break
        
        self.pipeline = new_pipeline
        
        # Process image immediately
        self.process_image()
    
    def edit_algorithm_params(self, item):
        """Open dialog to edit algorithm parameters."""
        # Get index of clicked item
        index = self.pipeline_list.row(item)
        if index < 0 or index >= len(self.pipeline):
            return
        
        # Get algorithm info
        algo_entry = self.pipeline[index]
        algo_id = algo_entry["algorithm"]
        current_params = algo_entry["params"]
        algo_info = self.ALGORITHMS.get(algo_id, {})
        algo_params_def = algo_info.get("params", [])
        
        # Open dialog
        from .algorithm_params_dialog import AlgorithmParamsDialog
        dialog = AlgorithmParamsDialog(
            algo_id=algo_id,
            current_params=current_params,
            algo_params_def=algo_params_def,
            original_image=self.original_image,
            parent_widget=self,
            pipeline_index=index
        )
        dialog.exec()
    
    def process_image(self):
        """Apply pipeline to the original image."""
        if self.original_image is None:
            return
        
        try:
            # Start with original image
            result = self.original_image.copy()
            
            # Apply each algorithm in pipeline
            for algo_entry in self.pipeline:
                result = ImagePreprocessingWidget.apply_algorithm(
                    result,
                    algo_entry["algorithm"],
                    algo_entry["params"]
                )
            
            self.processed_image = result
            self.display_image(self.processed_image, self.processed_label)
        except Exception as e:
            self.processed_label.setText(f"Lỗi xử lý: {e}")
    
    @staticmethod
    def apply_algorithm(img, algo_id, params):
        """Apply the specified algorithm with parameters."""
        if algo_id == "none":
            return img
        
        # Convert to grayscale for algorithms that need it
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        
        # Resize & Scaling
        if algo_id == "upscale_2x":
            return cv2.resize(img, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        elif algo_id == "upscale_3x":
            return cv2.resize(img, (0, 0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
        elif algo_id == "upscale_4x":
            return cv2.resize(img, (0, 0), fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        elif algo_id == "downscale_0.5x":
            return cv2.resize(img, (0, 0), fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)
        elif algo_id == "downscale_0.75x":
            return cv2.resize(img, (0, 0), fx=0.75, fy=0.75, interpolation=cv2.INTER_AREA)
        
        # Denoise
        elif algo_id == "gaussian_blur":
            k = params.get("kernel_size", 5)
            if k % 2 == 0:
                k += 1
            return cv2.GaussianBlur(img, (k, k), 0)
        elif algo_id == "median_blur":
            k = params.get("kernel_size", 5)
            if k % 2 == 0:
                k += 1
            return cv2.medianBlur(img, k)
        elif algo_id == "bilateral_filter":
            return cv2.bilateralFilter(img, params.get("d", 9), params.get("sigma_color", 75), params.get("sigma_space", 75))
        elif algo_id == "nlmeans_denoise":
            if len(img.shape) == 3:
                return cv2.fastNlMeansDenoisingColored(img, None, params.get("h", 10), params.get("h", 10), 
                                                       params.get("template_window_size", 7), params.get("search_window_size", 21))
            else:
                return cv2.fastNlMeansDenoising(img, None, params.get("h", 10), 
                                               params.get("template_window_size", 7), params.get("search_window_size", 21))
        
        # Contrast & Brightness
        elif algo_id == "auto_contrast":
            return cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
        elif algo_id == "clahe":
            clahe = cv2.createCLAHE(clipLimit=params.get("clip_limit", 2.0), 
                                   tileGridSize=(params.get("tile_grid_size", 8), params.get("tile_grid_size", 8)))
            return clahe.apply(gray)
        elif algo_id == "gamma_correction":
            gamma = params.get("gamma", 1.0)
            inv_gamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            return cv2.LUT(img, table)
        elif algo_id == "normalize":
            return cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX)
        
        # Thresholding
        elif algo_id == "binary_threshold":
            _, result = cv2.threshold(gray, params.get("threshold", 127), 255, cv2.THRESH_BINARY)
            return result
        elif algo_id == "otsu_threshold":
            _, result = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return result
        elif algo_id == "adaptive_mean":
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 
                                        params.get("block_size", 11), params.get("C", 2))
        elif algo_id == "adaptive_gaussian":
            return cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 
                                        params.get("block_size", 11), params.get("C", 2))
        
        # Morphology
        elif algo_id in ("erosion", "dilation", "opening", "closing", "tophat", "blackhat"):
            k = params.get("kernel_size", 3)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
            if algo_id == "erosion":
                return cv2.erode(gray, kernel)
            elif algo_id == "dilation":
                return cv2.dilate(gray, kernel)
            elif algo_id == "opening":
                return cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            elif algo_id == "closing":
                return cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            elif algo_id == "tophat":
                return cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
            elif algo_id == "blackhat":
                return cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        
        # Sharpening
        elif algo_id == "unsharp_mask":
            blurred = cv2.GaussianBlur(img, (0, 0), 3)
            amount = params.get("amount", 1.0)
            return cv2.addWeighted(img, 1.0 + amount, blurred, -amount, 0)
        elif algo_id == "laplacian_sharpen":
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            return cv2.convertScaleAbs(laplacian)
        
        # Edge Enhancement
        elif algo_id == "canny_edge":
            return cv2.Canny(gray, params.get("threshold1", 50), params.get("threshold2", 150))
        elif algo_id == "sobel_edge":
            sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
            sobel = cv2.magnitude(sobelx, sobely)
            return cv2.convertScaleAbs(sobel)
        
        # Color Space
        elif algo_id == "grayscale":
            return gray
        elif algo_id == "invert":
            return cv2.bitwise_not(img)
        
        # Skew Correction
        elif algo_id == "deskew":
            coords = np.column_stack(np.where(gray > 0))
            if len(coords) < 10:
                return img
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            (h, w) = img.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        
        # Combo Pipelines
        elif algo_id == "bright_on_dark":
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (11, 11))
            top = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, k)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            top = clahe.apply(top)
            top = cv2.GaussianBlur(top, (3, 3), 0)
            _, result = cv2.threshold(top, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return result
        elif algo_id == "small_text_noisy":
            # Upscale x2 + Denoise + Sharpen + Otsu
            upscaled = cv2.resize(img, (0, 0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray_up = cv2.cvtColor(upscaled, cv2.COLOR_BGR2GRAY) if len(upscaled.shape) == 3 else upscaled
            denoised = cv2.fastNlMeansDenoising(gray_up, None, 10, 7, 21)
            blurred = cv2.GaussianBlur(denoised, (0, 0), 3)
            sharpened = cv2.addWeighted(denoised, 1.5, blurred, -0.5, 0)
            _, result = cv2.threshold(sharpened, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return result
        elif algo_id == "screenshot":
            # Denoise + Auto Contrast + Adaptive Threshold
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            normalized = cv2.normalize(denoised, None, 0, 255, cv2.NORM_MINMAX)
            result = cv2.adaptiveThreshold(normalized, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            return result
        
        return img
    
    def display_image(self, img, label):
        """Display a cv2 image in a QLabel."""
        if img is None:
            return
        
        # Convert to RGB for display
        if len(img.shape) == 2:
            # Grayscale
            rgb_img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        else:
            # BGR to RGB
            rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        h, w, ch = rgb_img.shape
        bytes_per_line = ch * w
        qt_img = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale to fit label
        pixmap = QPixmap.fromImage(qt_img)
        scaled_pixmap = pixmap.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        label.setPixmap(scaled_pixmap)
    
    def save_config(self):
        """Save current preprocessing config to a file."""
        if self.original_image is None:
            QMessageBox.warning(self, "Lỗi", "Chưa có ảnh để lưu cấu hình.")
            return
        
        if not self.pipeline:
            QMessageBox.warning(self, "Lỗi", "Pipeline rỗng, không có gì để lưu.")
            return
        
        config = {
            "pipeline": self.pipeline
        }
        
        # Save to a known location
        config_path = os.path.join(os.path.dirname(__file__), "..", "preprocessing_config.json")
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            # Build summary text
            algo_names = [self.ALGORITHMS[entry["algorithm"]]["name"] for entry in self.pipeline]
            summary = " → ".join(algo_names)
            
            QMessageBox.information(
                self, 
                "Thành công", 
                f"Đã lưu pipeline:\n{summary}\n\n"
                f"Bạn có thể load cấu hình này vào action 'Đọc dữ liệu' để OCR tự động áp dụng."
            )
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể lưu cấu hình: {e}")
    
    def get_current_config(self):
        """Return current preprocessing config."""
        return {
            "pipeline": self.pipeline.copy()
        }

