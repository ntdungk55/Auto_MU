"""Template Matching Preprocessing - Builder pattern for image quality improvement for template matching."""

import cv2
import numpy as np


def apply_rgb_range_filter_to_bgr(img: np.ndarray, config: dict) -> np.ndarray:
    """Filter the configured RGB range in HSV while preserving BGR output."""
    if img is None or img.size == 0:
        return img

    channel_ranges = (
        sorted((max(0, min(255, int(config.get("blue_min", 0)))),
                max(0, min(255, int(config.get("blue_max", 255)))))),
        sorted((max(0, min(255, int(config.get("green_min", 0)))),
                max(0, min(255, int(config.get("green_max", 255)))))),
        sorted((max(0, min(255, int(config.get("red_min", 0)))),
                max(0, min(255, int(config.get("red_max", 255)))))),
    )
    corners_bgr = np.array(
        [
            (blue, green, red)
            for blue in channel_ranges[0]
            for green in channel_ranges[1]
            for red in channel_ranges[2]
        ],
        dtype=np.uint8,
    ).reshape(-1, 1, 3)
    corners_hsv = cv2.cvtColor(corners_bgr, cv2.COLOR_BGR2HSV).reshape(-1, 3)
    saturation_min = int(corners_hsv[:, 1].min())
    value_min = int(corners_hsv[:, 2].min())

    hue_ranges: list[tuple[int, int]]
    if saturation_min == 0:
        hue_ranges = [(0, 179)]
    else:
        hues = np.unique(corners_hsv[:, 0].astype(np.int16))
        circular_gaps = np.diff(np.r_[hues, hues[0] + 180])
        gap_index = int(np.argmax(circular_gaps))
        hue_start = int(hues[(gap_index + 1) % len(hues)])
        hue_end = int(hues[gap_index])
        hue_ranges = (
            [(hue_start, hue_end)]
            if hue_start <= hue_end
            else [(0, hue_end), (hue_start, 179)]
        )

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for hue_min, hue_max in hue_ranges:
        lower = np.array([hue_min, saturation_min, value_min], dtype=np.uint8)
        upper = np.array([hue_max, 255, 255], dtype=np.uint8)
        mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

    return cv2.bitwise_and(img, img, mask=mask)


class TemplateMatchingPreprocessor:
    """Builder pattern cho Template Matching preprocessing - cải thiện chất lượng ảnh trước template matching."""
    
    def __init__(self, img_bgr: np.ndarray, ui_log_func=None):
        """Khởi tạo preprocessor với ảnh input.
        
        Args:
            img_bgr: Ảnh BGR input
            ui_log_func: Hàm để log (tùy chọn)
        """
        self.img = img_bgr.copy() if img_bgr is not None else None
        self.ui_log = ui_log_func or (lambda x: None)
    
    def upscale(self, scale_factor: float = 2.0) -> 'TemplateMatchingPreprocessor':
        """Phóng to ảnh để cải thiện chi tiết template matching."""
        if self.img is None or scale_factor <= 1.0:
            return self
        
        try:
            h, w = self.img.shape[:2]
            new_w = int(w * scale_factor)
            new_h = int(h * scale_factor)
            
            # Dùng INTER_CUBIC để phóng to (chất lượng tốt hơn INTER_LINEAR)
            self.img = cv2.resize(self.img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Upscale]</span> Lỗi: {e}")
        
        return self
    
    def enhance_contrast(self, clip_limit: float = 3.0) -> 'TemplateMatchingPreprocessor':
        """Tăng độ tương phản bằng CLAHE để cải thiện template matching."""
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
            self.ui_log(f"<span style='color:red;'>[TM Contrast]</span> Lỗi: {e}")
        
        return self
    
    def sharpen(self, strength: float = 1.5) -> 'TemplateMatchingPreprocessor':
        """Làm sắc nét ảnh để cải thiện độ rõ của template matching."""
        if self.img is None:
            return self
        
        try:
            # Tạo Gaussian blur
            blurred = cv2.GaussianBlur(self.img, (0, 0), 1.0)
            
            # Unsharp mask: original + (original - blurred) * strength
            self.img = cv2.addWeighted(self.img, 1.0 + strength, blurred, -strength, 0)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Sharpen]</span> Lỗi: {e}")
        
        return self
    
    def denoise(self, filter_size: int = 9) -> 'TemplateMatchingPreprocessor':
        """Khử nhiễu trong khi giữ lại các cạnh cho template matching."""
        if self.img is None:
            return self
        
        try:
            # Bilateral filter: làm mịn trong khi giữ lại cạnh
            filter_size = max(3, filter_size)
            if filter_size % 2 == 0:
                filter_size += 1
            
            self.img = cv2.bilateralFilter(self.img, filter_size, 75, 75)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Denoise]</span> Lỗi: {e}")
        
        return self
    
    def morphological_opening(self, kernel_size: int = 3) -> 'TemplateMatchingPreprocessor':
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
            self.ui_log(f"<span style='color:red;'>[TM Morphological Opening]</span> Lỗi: {e}")
        
        return self
    
    def morphological_closing(self, kernel_size: int = 3) -> 'TemplateMatchingPreprocessor':
        """Lấp đầy các khoảng trống nhỏ trong template bằng Closing (Dilation + Erosion)."""
        if self.img is None:
            return self
        
        try:
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # Closing = Dilation followed by Erosion
            closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
            
            self.img = cv2.cvtColor(closed, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Morphological Closing]</span> Lỗi: {e}")
        
        return self
    
    def remove_small_components(self, min_area: int = 50) -> 'TemplateMatchingPreprocessor':
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
            self.ui_log(f"<span style='color:red;'>[TM Remove Small Components]</span> Lỗi: {e}")
        
        return self
    
    def median_filter(self, kernel_size: int = 5) -> 'TemplateMatchingPreprocessor':
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
            self.ui_log(f"<span style='color:red;'>[TM Median Filter]</span> Lỗi: {e}")
        
        return self
    
    def edge_preserving_filter(self, flags: int = 1, sigma_s: float = 50, sigma_r: float = 0.4) -> 'TemplateMatchingPreprocessor':
        """Khử nhiễu mà vẫn giữ lại cạnh template bằng Edge-Preserving Filter."""
        if self.img is None:
            return self
        
        try:
            # Edge-preserving filter
            # flags: 1 = RECURS_FILTER, 2 = NORMCONV_FILTER
            self.img = cv2.edgePreservingFilter(self.img, flags=flags, sigma_s=sigma_s, sigma_r=sigma_r)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Edge-Preserving Filter]</span> Lỗi: {e}")
        
        return self
    
    def nlm_denoising(self, h: float = 10, template_window_size: int = 7, search_window_size: int = 21) -> 'TemplateMatchingPreprocessor':
        """Khử nhiễu cao cấp bằng Non-Local Means - rất mạnh cho texture noise."""
        if self.img is None:
            return self
        
        try:
            # Non-Local Means Denoising - rất mạnh cho texture noise
            self.img = cv2.fastNlMeansDenoisingColored(self.img, None, h, h, template_window_size, search_window_size)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM NLM Denoising]</span> Lỗi: {e}")
        
        return self
    
    def gaussian_blur(self, kernel_size: int = 5, sigma_x: float = 0) -> 'TemplateMatchingPreprocessor':
        """Làm mờ Gaussian để giảm noise cho template matching."""
        if self.img is None:
            return self
        
        try:
            # Ensure kernel_size is odd and positive
            kernel_size = max(3, kernel_size)
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            # If sigma_x is 0, calculate automatically
            if sigma_x == 0:
                sigma_x = 0.3 * ((kernel_size - 1) * 0.5 - 1) + 0.8
            
            self.img = cv2.GaussianBlur(self.img, (kernel_size, kernel_size), sigma_x)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Gaussian Blur]</span> Lỗi: {e}")
        
        return self
    
    def histogram_equalization(self) -> 'TemplateMatchingPreprocessor':
        """Cân bằng histogram để cải thiện độ tương phản cho template matching."""
        if self.img is None:
            return self
        
        try:
            # Convert to YUV color space
            img_yuv = cv2.cvtColor(self.img, cv2.COLOR_BGR2YUV)
            
            # Apply histogram equalization to Y channel
            img_yuv[:, :, 0] = cv2.equalizeHist(img_yuv[:, :, 0])
            
            # Convert back to BGR
            self.img = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Histogram Equalization]</span> Lỗi: {e}")
        
        return self
    
    def canny_edge_detection(self, low_threshold: int = 50, high_threshold: int = 150) -> 'TemplateMatchingPreprocessor':
        """Phát hiện cạnh bằng Canny để tạo edge map cho template matching."""
        if self.img is None:
            return self
        
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
            
            # Apply Canny edge detection
            edges = cv2.Canny(gray, low_threshold, high_threshold)
            
            # Convert back to 3-channel
            self.img = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Canny Edge Detection]</span> Lỗi: {e}")
        
        return self
    
    def alpha_blend_recovery(self, alpha: float = 0.7, sigma: float = 15.0) -> 'TemplateMatchingPreprocessor':
        """Khôi phục dialog có alpha blending (trong suốt) bằng cách ước lượng nền và tách lớp.
        
        Thuật toán:
        1. Ước lượng nền bằng Gaussian Blur mạnh (low-frequency)
        2. Giải phương trình alpha blending ngược: F = (C - (1-a)*B) / a
        3. Đặt lên nền trắng để làm nổi
        
        Args:
            alpha: Độ trong suốt của dialog (0.01-0.99), default 0.7
            sigma: Sigma cho Gaussian Blur (5-50), default 15
        """
        if self.img is None:
            return self
        
        try:
            # Validate parameters
            alpha = max(0.01, min(0.99, alpha))  # Clamp to [0.01, 0.99]
            sigma = max(5.0, min(50.0, sigma))   # Clamp to [5, 50]
            
            # Convert to float32 [0, 1]
            C = self.img.astype(np.float32) / 255.0
            
            # Estimate background using strong Gaussian Blur (low-frequency)
            B = cv2.GaussianBlur(C, (0, 0), sigmaX=sigma, sigmaY=sigma)
            
            # Recover foreground layer using inverse alpha blending
            # Original: C = alpha * F + (1 - alpha) * B
            # Solve for F: F = (C - (1 - alpha) * B) / alpha
            F = (C - (1.0 - alpha) * B) / max(alpha, 1e-6)
            
            # Clip to valid range [0, 1]
            F = np.clip(F, 0.0, 1.0)
            
            # Place on white background to make dialog pop
            bg_white = np.ones_like(F)
            out = F * 1.0 + bg_white * 0.0  # Keep F, flat background
            
            # Convert back to uint8 [0, 255]
            self.img = (out * 255).astype(np.uint8)
            
        except Exception as e:
            self.ui_log(f"<span style='color:red;'>[TM Alpha Blend Recovery]</span> Lỗi: {e}")
        
        return self
    
    def build(self) -> np.ndarray:
        """Trả về ảnh đã được xử lý."""
        return self.img
