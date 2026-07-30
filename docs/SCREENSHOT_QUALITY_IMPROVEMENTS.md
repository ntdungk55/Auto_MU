# Screenshot Quality Improvements for Game Window Capture

## Current Implementation
The current `capture_window_screenshot()` method uses:
- `PrintWindow()` with `PW_CLIENTONLY` flag (primary method)
- Fallback to `PW_RENDERFULLCONTENT` for DirectX/OpenGL games
- Final fallback to `BitBlt()` if PrintWindow fails
- DPI awareness enabled

## Quality Issues & Solutions

### 1. **Upscaling for Better OCR Quality** ⭐ RECOMMENDED
**Problem:** Small text in screenshots may be hard for OCR to read accurately.

**Solution:** Upscale the captured image before OCR processing.

```python
def _upscale_for_ocr(self, img_bgr: np.ndarray, scale_factor: float = 2.0) -> np.ndarray:
    """Upscale image for better OCR quality (2x or 3x recommended)."""
    if img_bgr is None or scale_factor <= 1.0:
        return img_bgr
    
    h, w = img_bgr.shape[:2]
    new_w = int(w * scale_factor)
    new_h = int(h * scale_factor)
    
    # Use INTER_CUBIC for upscaling (better quality than INTER_LINEAR)
    upscaled = cv2.resize(img_bgr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
    return upscaled
```

**When to use:**
- Before OCR processing (especially for small text)
- 2x upscaling is usually sufficient
- 3x for very small text (but slower)

**Trade-off:** Slightly slower OCR, but much better accuracy for small text.

---

### 2. **Contrast Enhancement** ⭐ RECOMMENDED
**Problem:** Low contrast text is hard to read.

**Solution:** Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).

```python
def _enhance_contrast_for_ocr(self, img_bgr: np.ndarray) -> np.ndarray:
    """Enhance contrast for better OCR readability."""
    if img_bgr is None:
        return img_bgr
    
    # Convert to LAB color space
    img_lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(img_lab)
    
    # Apply CLAHE to L channel
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_clahe = clahe.apply(l)
    
    # Merge back
    img_lab_enhanced = cv2.merge([l_clahe, a, b])
    img_enhanced = cv2.cvtColor(img_lab_enhanced, cv2.COLOR_LAB2BGR)
    
    return img_enhanced
```

**When to use:**
- Before OCR processing
- Especially for low-contrast game UIs
- Very fast operation

---

### 3. **Sharpening Filter** ⭐ RECOMMENDED
**Problem:** Blurry text reduces OCR accuracy.

**Solution:** Apply unsharp mask.

```python
def _sharpen_for_ocr(self, img_bgr: np.ndarray, strength: float = 1.5) -> np.ndarray:
    """Sharpen image to improve text clarity."""
    if img_bgr is None:
        return img_bgr
    
    # Create Gaussian blur
    blurred = cv2.GaussianBlur(img_bgr, (0, 0), 1.0)
    
    # Unsharp mask: original + (original - blurred) * strength
    sharpened = cv2.addWeighted(img_bgr, 1.0 + strength, blurred, -strength, 0)
    
    return sharpened
```

**When to use:**
- Before OCR processing
- Especially for blurry game text
- Strength 1.0-2.0 recommended

---

### 4. **Binarization (Black & White)** ⭐ OPTIONAL
**Problem:** Color noise interferes with OCR.

**Solution:** Convert to binary (black & white only).

```python
def _binarize_for_ocr(self, img_bgr: np.ndarray, threshold: int = 127) -> np.ndarray:
    """Convert to binary for cleaner OCR."""
    if img_bgr is None:
        return img_bgr
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # Apply Otsu's thresholding (automatic threshold)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Convert back to BGR for consistency
    binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
    
    return binary_bgr
```

**When to use:**
- For high-contrast text (white on black, black on white)
- NOT recommended for colored text
- Very aggressive, may lose some information

---

### 5. **Denoise** ⭐ OPTIONAL
**Problem:** Noise in screenshot reduces OCR accuracy.

**Solution:** Apply bilateral filter or morphological operations.

```python
def _denoise_for_ocr(self, img_bgr: np.ndarray) -> np.ndarray:
    """Remove noise while preserving edges."""
    if img_bgr is None:
        return img_bgr
    
    # Bilateral filter: smooth while preserving edges
    denoised = cv2.bilateralFilter(img_bgr, 9, 75, 75)
    
    return denoised
```

**When to use:**
- For noisy screenshots
- Slower than other methods
- Good for preserving text edges

---

## Recommended Pipeline for Best Quality

```python
def preprocess_for_ocr(self, img_bgr: np.ndarray) -> np.ndarray:
    """Complete preprocessing pipeline for best OCR quality."""
    if img_bgr is None:
        return None
    
    # Step 1: Upscale (2x for better detail)
    img = self._upscale_for_ocr(img_bgr, scale_factor=2.0)
    
    # Step 2: Enhance contrast
    img = self._enhance_contrast_for_ocr(img)
    
    # Step 3: Sharpen
    img = self._sharpen_for_ocr(img, strength=1.5)
    
    # Step 4: Optional denoise (if noisy)
    # img = self._denoise_for_ocr(img)
    
    return img
```

---

## Implementation Recommendations

### Quick Win (Minimal Performance Impact)
1. **Upscale 2x** - Best quality/performance ratio
2. **Enhance contrast** - Very fast, big improvement

### Maximum Quality (Slower)
1. Upscale 2x
2. Enhance contrast
3. Sharpen
4. Denoise (optional)

### For Different Game Types

**Text-Heavy Games (RPG, Strategy):**
- Upscale 2x
- Enhance contrast
- Sharpen

**Low-Contrast UI (Dark themes):**
- Upscale 2x
- Enhance contrast (CLAHE)
- Sharpen

**Noisy Screenshots:**
- Upscale 2x
- Denoise
- Enhance contrast
- Sharpen

---

## Performance Impact

| Method | Speed | Quality Gain |
|--------|-------|--------------|
| Upscale 2x | ~10-20ms | ⭐⭐⭐⭐ |
| Contrast (CLAHE) | ~5-10ms | ⭐⭐⭐ |
| Sharpen | ~5-10ms | ⭐⭐⭐ |
| Denoise | ~20-50ms | ⭐⭐ |
| Binarize | ~5-10ms | ⭐⭐ |

---

## Configuration Options

Add to `AutoAction` dataclass:

```python
# OCR preprocessing options
ocr_upscale_factor: float = 2.0  # 1.0 = no upscale, 2.0 = 2x, 3.0 = 3x
ocr_enhance_contrast: bool = True  # CLAHE
ocr_sharpen: bool = True  # Unsharp mask
ocr_denoise: bool = False  # Bilateral filter
ocr_binarize: bool = False  # Black & white only
```

---

## Testing Recommendations

1. **Capture a screenshot** from your game
2. **Try each preprocessing method** individually
3. **Measure OCR accuracy** improvement
4. **Choose the best combination** for your game
5. **Save the configuration** in the action

---

## Notes

- **Upscaling is the most impactful** - always recommended
- **Contrast enhancement is very fast** - almost always worth it
- **Sharpening helps with blurry text** - recommended
- **Denoise is slower** - only use if needed
- **Binarization is aggressive** - only for high-contrast text
- **Order matters** - upscale first, then enhance, then sharpen

---

## Current Code Location

`system_executor.py` - `capture_window_screenshot()` method (line 674)

To implement: Add preprocessing methods and call them before OCR processing in `_run_passive_read()` and `execute_with_timeout()`.
