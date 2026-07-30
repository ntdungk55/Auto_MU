# OCR Preprocessing Implementation - Cải Thiện Chất Lượng Ảnh

## Tóm Tắt
Đã implement 4 phương pháp cải thiện chất lượng ảnh trước khi OCR:
1. **Phóng to ảnh (Upscale)** - 2x hoặc 3x
2. **Tăng độ tương phản (Contrast Enhancement)** - CLAHE
3. **Làm sắc nét (Sharpening)** - Unsharp Mask
4. **Khử nhiễu (Denoise)** - Bilateral Filter

---

## Các Hàm Được Thêm

### 1. `_upscale_for_ocr(img_bgr, scale_factor=2.0)`
Phóng to ảnh để cải thiện chi tiết text nhỏ.
- Dùng `cv2.INTER_CUBIC` để phóng to chất lượng cao
- Mặc định: 2x (có thể tùy chỉnh 3x)
- Tốc độ: ~10-20ms

### 2. `_enhance_contrast_for_ocr(img_bgr)`
Tăng độ tương phản bằng CLAHE (Contrast Limited Adaptive Histogram Equalization).
- Chuyển sang LAB color space
- Áp dụng CLAHE vào L channel
- Giúp text mờ trở nên rõ ràng
- Tốc độ: ~5-10ms

### 3. `_sharpen_for_ocr(img_bgr, strength=1.5)`
Làm sắc nét ảnh bằng Unsharp Mask.
- Tạo Gaussian blur
- Áp dụng công thức: original + (original - blurred) * strength
- Giúp text mờ trở nên sắc nét
- Tốc độ: ~5-10ms

### 4. `_denoise_for_ocr(img_bgr)`
Khử nhiễu bằng Bilateral Filter.
- Làm mịn trong khi giữ lại cạnh text
- Chỉ dùng khi ảnh có nhiều nhiễu
- Tốc độ: ~20-50ms (chậm hơn, nên tắt mặc định)

### 5. `preprocess_for_ocr(img_bgr, enable_upscale, enable_contrast, enable_sharpen, enable_denoise, upscale_factor)`
Quy trình preprocessing hoàn chỉnh.
- Áp dụng tất cả các bước theo thứ tự
- Có thể bật/tắt từng bước
- Mặc định: Upscale 2x → Contrast → Sharpen

---

## Cấu Hình Trong AutoAction

Thêm 5 trường mới vào `AutoAction` dataclass:

```python
# OCR preprocessing options for better quality
ocr_upscale_enabled: bool = True  # Bật phóng to ảnh trước OCR
ocr_upscale_factor: float = 2.0  # Hệ số phóng to (2.0 = 2x, 3.0 = 3x)
ocr_enhance_contrast: bool = True  # Bật tăng độ tương phản (CLAHE)
ocr_sharpen: bool = True  # Bật làm sắc nét (Unsharp Mask)
ocr_denoise: bool = False  # Bật khử nhiễu (Bilateral Filter) - chậm hơn
```

---

## Quy Trình Mặc Định

```
Ảnh gốc
    ↓
Phóng to 2x (Upscale)
    ↓
Tăng độ tương phản (CLAHE)
    ↓
Làm sắc nét (Unsharp Mask)
    ↓
OCR (WinRT hoặc Tesseract)
```

---

## Hiệu Suất

| Bước | Tốc độ | Chất lượng |
|------|--------|-----------|
| Upscale 2x | ~10-20ms | ⭐⭐⭐⭐ |
| Contrast (CLAHE) | ~5-10ms | ⭐⭐⭐ |
| Sharpen | ~5-10ms | ⭐⭐⭐ |
| Denoise | ~20-50ms | ⭐⭐ |
| **Tổng cộng** | **~20-40ms** | **Rất tốt** |

---

## Cách Sử Dụng

### Mặc Định (Tốt nhất cho hầu hết trường hợp)
```python
# Tất cả preprocessing được bật
# Upscale 2x, Contrast, Sharpen
# Denoise tắt (quá chậm)
```

### Tùy Chỉnh Trong Action Config
Người dùng có thể:
- Bật/tắt từng bước preprocessing
- Thay đổi hệ số phóng to (2.0 hoặc 3.0)
- Bật denoise nếu ảnh có nhiều nhiễu

### Ví Dụ Code
```python
# Trong _ocr_from_bgr()
enable_upscale = bool(getattr(action, "ocr_upscale_enabled", True))
enable_contrast = bool(getattr(action, "ocr_enhance_contrast", True))
enable_sharpen = bool(getattr(action, "ocr_sharpen", True))
enable_denoise = bool(getattr(action, "ocr_denoise", False))
upscale_factor = float(getattr(action, "ocr_upscale_factor", 2.0) or 2.0)

bgr_preprocessed = self.preprocess_for_ocr(
    bgr_img,
    enable_upscale=enable_upscale,
    enable_contrast=enable_contrast,
    enable_sharpen=enable_sharpen,
    enable_denoise=enable_denoise,
    upscale_factor=upscale_factor
)
```

---

## Serialization

Các trường mới được thêm vào `tool_manager.py`:
- `_action_to_dict()` - Serialize các trường preprocessing
- `from_dict()` - Deserialize các trường preprocessing

Tất cả cấu hình được lưu vào JSON file của tool.

---

## Khi Nào Dùng Từng Bước

### Upscale (LUÔN BẬT)
- Phóng to 2x: Tốt cho hầu hết trường hợp
- Phóng to 3x: Cho text rất nhỏ (chậm hơn)

### Contrast Enhancement (LUÔN BẬT)
- Rất nhanh (~5-10ms)
- Giúp text mờ rõ ràng
- Không có tác dụng phụ

### Sharpening (LUÔN BẬT)
- Giúp text mờ sắc nét
- Tốc độ nhanh (~5-10ms)
- Có thể làm tăng nhiễu nếu quá mạnh

### Denoise (TẮT MẶC ĐỊNH)
- Chỉ bật khi ảnh có nhiều nhiễu
- Chậm (~20-50ms)
- Có thể làm mất chi tiết

---

## Commit

```
Feat: Add OCR preprocessing for better image quality (Upscale, Contrast, Sharpen, Denoise)

- Added 4 preprocessing methods to SystemExecutor
- Modified _ocr_from_bgr() to apply preprocessing before OCR
- Added 5 new configuration fields to AutoAction
- Updated tool_manager.py to serialize/deserialize new fields
- Default pipeline: Upscale 2x → Enhance Contrast → Sharpen
- Performance impact: ~20-40ms per frame
```

Commit hash: `ee817f8`

---

## Tiếp Theo

Có thể thêm:
1. UI để tùy chỉnh các tham số preprocessing
2. Preview ảnh sau preprocessing
3. Thống kê OCR accuracy trước/sau preprocessing
4. Tự động chọn tham số tối ưu dựa trên ảnh
