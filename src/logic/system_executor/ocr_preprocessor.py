"""OCR Preprocessing - Builder pattern for image quality improvement."""

import cv2
import numpy as np


class OCRPreprocessor:
    """Builder pattern cho OCR preprocessing - cải thiện chất lượng ảnh trước OCR."""
    
    def __init__(self, img_bgr: np.ndarray, ui_log_func=None):
        """Khởi tạo preprocessor với ảnh input.
        
        Args:
            img_bgr: Ảnh BGR input
            ui_log_func: Hàm để log (tùy chọn)
        """
        self.img = img_bgr.copy() if img_bgr is not None else None
        self.ui_log = ui_log_func or (lambda x: None)
    
    def upscale(self, scale_factor: float = 2.0) -> 'OCRPreprocessor':
        """Phóng to ảnh để cải thiện chi tiết (2x hoặc 3x khuyến nghị)."""
        if self.img is None or scale_factor <= 1.0:
            return self
        
        try:
            h, w = self.img.shape[:2]
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            
            # Dùng INTER_CUBIC để phóng to (chất lượng tốt hơn INTER_LINEAR)
            self.img = cv2.resize(self.img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Upscale]</span> Lỗi: {e}")
        
        return self
    
    def enhance_contrast(self, clip_limit: float = 3.0) -> 'OCRPreprocessor':
        """Tăng độ tương phản bằng CLAHE để cải thiện OCR."""
        if self.img is None:
            return self
        
        try:
            # Chuyển sang LAB color space
            img_lab = cv2.cvtColor(self.img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(img_lab)
            
            # Áp dụng CLAHE vào L channel với custom clip_limit
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            l_clahe = clahe.apply(l)
            
            # Gộp lại
            img_lab_enhanced = cv2.merge([l_clahe, a, b])
            self.img = cv2.cvtColor(img_lab_enhanced, cv2.COLOR_LAB2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Contrast]</span> Lỗi: {e}")
        
        return self
    
    def sharpen(self, strength: float = 1.5) -> 'OCRPreprocessor':
        """Làm sắc nét ảnh để cải thiện độ rõ của text."""
        if self.img is None:
            return self
        
        try:
            # Tạo Gaussian blur
            blurred = cv2.GaussianBlur(self.img, (0, 0), 1.0)
            
            # Unsharp mask: original + (original - blurred) * strength
            self.img = cv2.addWeighted(self.img, 1.0 + strength, blurred, -strength, 0)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Sharpen]</span> Lỗi: {e}")
        
        return self
    
    def denoise(self, filter_size: int = 9) -> 'OCRPreprocessor':
        """Khử nhiễu trong khi giữ lại các cạnh text."""
        if self.img is None:
            return self
        
        try:
            # Bilateral filter: làm mịn trong khi giữ lại cạnh
            # filter_size should be odd and positive
            filter_size = max(3, filter_size)
            if filter_size % 2 == 0:
                filter_size += 1
            
            self.img = cv2.bilateralFilter(self.img, filter_size, 75, 75)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Denoise]</span> Lỗi: {e}")
        
        return self
    
    def morphological_opening(self, kernel_size: int = 3) -> 'OCRPreprocessor':
        """Loại bỏ các viền nhỏ, chấm nhiễu bằng Opening (Erosion + Dilation)."""
        if self.img is None:
            return self
        
        try:
            # Convert to grayscale for morphology
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            
            # Create elliptical kernel
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Opening = Erosion followed by Dilation
            opened = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
            
            # Convert back to BGR
            self.img = cv2.cvtColor(opened, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Morphological Opening]</span> Lỗi: {e}")
        
        return self
    
    def morphological_closing(self, kernel_size: int = 3) -> 'OCRPreprocessor':
        """Lấp đầy các khoảng trống nhỏ trong text bằng Closing (Dilation + Erosion)."""
        if self.img is None:
            return self
        
        try:
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Closing = Dilation followed by Erosion
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            self.img = cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Morphological Closing]</span> Lỗi: {e}")
        
        return self
    
    def remove_small_components(self, min_area: int = 50) -> 'OCRPreprocessor':
        """Loại bỏ các component nhỏ (chấm nhiễu, viền thừa) dựa trên kích thước."""
        if self.img is None:
            return self
        
        try:
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            
            # Binary threshold using Otsu's method
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
            
            # Create output image
            output = np.zeros_like(binary)
            
            # Keep only components larger than min_area
            for i in range(1, num_labels):  # Skip background (label 0)
                area = stats[i, cv2.CC_STAT_AREA]
                if area >= min_area:
                    output[labels == i] = 255
            
            self.img = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Remove Small Components]</span> Lỗi: {e}")
        
        return self
    
    def median_filter(self, kernel_size: int = 5) -> 'OCRPreprocessor':
        """Khử chấm nhiễu bằng Median Filter - hiệu quả với salt-and-pepper noise."""
        if self.img is None:
            return self
        
        try:
            # Ensure kernel_size is odd and positive
            kernel_size = max(3, kernel_size)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            # Median filter rất hiệu quả với salt-and-pepper noise
            self.img = cv2.medianBlur(self.img, kernel_size)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Median Filter]</span> Lỗi: {e}")
        
        return self
    
    def edge_preserving_filter(self, flags: int = 1, sigma_s: float = 50, sigma_r: float = 0.4) -> 'OCRPreprocessor':
        """Khử nhiễu mà vẫn giữ lại cạnh text bằng Edge-Preserving Filter."""
        if self.img is None:
            return self
        
        try:
            # Edge-preserving filter
            # flags: 1 = RECURS_FILTER, 2 = NORMCONV_FILTER
            self.img = cv2.edgePreservingFilter(self.img, flags=flags, sigma_s=sigma_s, sigma_r=sigma_r)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[Edge-Preserving Filter]</span> Lỗi: {e}")
        
        return self
    
    def nlm_denoising(self, h: float = 10, template_window_size: int = 7, search_window_size: int = 21) -> 'OCRPreprocessor':
        """Khử nhiễu cao cấp bằng Non-Local Means - rất mạnh cho texture noise."""
        if self.img is None:
            return self
        
        try:
            # Non-Local Means Denoising - rất mạnh cho texture noise
            self.img = cv2.fastNlMeansDenoisingColored(self.img, None, h, h, template_window_size, search_window_size)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[NLM Denoising]</span> Lỗi: {e}")
        
        return self
    
    def build(self) -> np.ndarray:
        """Trả về ảnh đã được xử lý."""
        return self.img
