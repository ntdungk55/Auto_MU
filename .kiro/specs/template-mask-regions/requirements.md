# Feature: Template Mask Regions - Bỏ qua vùng text động khi matching

## 1. Tổng quan

Cho phép user đánh dấu các vùng text động (thay đổi giữa các lần chạy) trên teaching image. Các vùng này sẽ bị bỏ qua khi template matching, giúp tăng độ chính xác khi chỉ có text thay đổi mà layout/icon không đổi.

## 2. User Stories

- Là user, tôi muốn đánh dấu vùng text động trên teaching image, để template matching không bị ảnh hưởng bởi text thay đổi
- Là user, tôi muốn vẽ nhiều mask regions trên cùng 1 teaching image, để bỏ qua nhiều vùng text khác nhau
- Là user, tôi muốn xóa mask region đã vẽ (bằng Delete key hoặc chuột phải), để sửa lỗi khi vẽ nhầm
- Là user, tôi muốn threshold cao mà vẫn match được, để tránh false positive

## 3. Acceptance Criteria

1. **Vẽ mask regions:**
   - Có button "Vẽ Mask" trong ImageCaptureDialog
   - Click button → bật chế độ vẽ mask
   - Vẽ nhiều hình chữ nhật màu đỏ semi-transparent
   - Mỗi mask region hiển thị rõ ràng trên ảnh

2. **Xóa mask regions:**
   - Click vào mask region → highlight (viền dày hơn)
   - Nhấn Delete key → xóa mask đã select
   - Chuột phải vào mask → menu "Xóa mask" → xóa
   - Có button "Xóa tất cả mask"

3. **Lưu/Load mask regions:**
   - Mask regions lưu vào action.mask_regions (list of dict)
   - Format: `[{"x": 10, "y": 20, "w": 50, "h": 30}, ...]`
   - Tọa độ relative to teaching image (không phải screen)
   - Load lại teaching image → mask regions hiển thị đúng

4. **Template matching với mask:**
   - Khi có mask_regions → tạo mask array
   - Dùng cv2.matchTemplate() với mask parameter
   - Vùng mask = 0 (ignore), vùng khác = 255 (match)
   - Threshold cao vẫn match được khi chỉ text thay đổi

5. **Backward compatible:**
   - Action không có mask_regions → matching bình thường
   - Không breaking changes với code cũ

## 4. Input/Output

**Input:**
- Teaching image (PNG file)
- User vẽ mask regions (drag mouse)
- User select và xóa mask regions

**Output:**
- action.mask_regions: `[{"x": int, "y": int, "w": int, "h": int}, ...]`
- Template matching với mask applied
- Score cao hơn khi text thay đổi

## 5. Sơ đồ khối

```
┌─────────────────────────────────────┐
│  ImageCaptureDialog                 │
│  - Button "Vẽ Mask"                 │
│  - Vẽ nhiều rectangles (màu đỏ)    │
│  - Click select, Delete/Right-click│
│  - Save mask_regions to action     │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  AutoAction                         │
│  - mask_regions: list[dict]         │
│    [{"x":10,"y":20,"w":50,"h":30}] │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  ToolManager                        │
│  - Save mask_regions to JSON        │
│  - Load mask_regions from JSON      │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  SystemExecutor                     │
│  - Create mask array from regions   │
│  - cv2.matchTemplate(mask=mask)     │
│  - Higher score with text changes   │
└─────────────────────────────────────┘
```

## 6. Technical Notes

**Mask Array Creation:**
```python
mask = np.ones(template.shape[:2], dtype=np.uint8) * 255
for region in mask_regions:
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    mask[y:y+h, x:x+w] = 0  # Ignore this region
```

**Template Matching:**
```python
result = cv2.matchTemplate(screenshot_gray, template_gray, cv2.TM_CCOEFF_NORMED, mask=mask)
```

**UI Considerations:**
- Mask regions màu đỏ với alpha=0.3 để thấy ảnh bên dưới
- Selected mask có viền dày hơn (3px vs 2px)
- Context menu chỉ hiện khi chuột phải vào mask region

**Validation:**
- Mask regions không được overlap toàn bộ ảnh (phải còn ít nhất 10% để match)
- Tọa độ mask phải nằm trong teaching image bounds

**Performance:**
- Mask array chỉ tạo 1 lần khi load template
- Cache mask array trong _template_gray_cache
