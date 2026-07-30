# Multi-step Preprocessing Pipeline - Hoàn thành

## Tóm tắt Feature

Feature cho phép áp dụng nhiều thuật toán preprocessing liên tiếp trong tab "Hiệu chỉnh", thay vì chỉ chọn 1 thuật toán như trước đây. Các thuật toán được áp dụng theo thứ tự từ trên xuống dưới trong một pipeline.

## Đã hoàn thành

### 1. UI Components
- ✅ Thêm QListWidget để hiển thị pipeline với drag & drop enabled
- ✅ Thay đổi QComboBox thành dropdown để chọn thuật toán (loại bỏ option "none")
- ✅ Thêm nút "➕ Add" để thêm thuật toán vào pipeline
- ✅ Thêm nút "➖ Remove" để xóa thuật toán đã chọn
- ✅ Remove button chỉ enabled khi có item được chọn

### 2. Functionality
- ✅ Thêm thuật toán vào pipeline với parameters mặc định
- ✅ Xóa thuật toán khỏi pipeline
- ✅ Drag & drop để sắp xếp lại thứ tự thuật toán
- ✅ Áp dụng pipeline ngay lập tức khi thêm/xóa/reorder
- ✅ Pipeline được áp dụng theo thứ tự từ trên xuống dưới

### 3. Data Structure
- ✅ Pipeline lưu dưới dạng list: `[{"algorithm": "upscale_2x", "params": {}}, ...]`
- ✅ Mỗi thuật toán có parameters mặc định từ ALGORITHMS definition
- ✅ Save config lưu toàn bộ pipeline vào JSON

### 4. Edge Cases
- ✅ Pipeline có thể rỗng (không áp dụng thuật toán nào)
- ✅ Có thể thêm cùng một thuật toán nhiều lần
- ✅ Drag & drop chỉ trong cùng một list

## Files đã thay đổi

### src/ui/image_preprocessing_widget.py
**Thay đổi chính:**
- Import thêm `QListWidget`
- Thay đổi `__init__`: Xóa `current_algo`, `current_params`, `param_widgets` → Thêm `pipeline` (list)
- Thay đổi `init_ui()`: 
  - Xóa phần parameters area (QScrollArea với dynamic widgets)
  - Thêm dropdown + Add/Remove buttons
  - Thêm QListWidget với drag & drop
- Xóa methods: `on_algorithm_changed()`, `on_param_changed()`
- Thêm methods mới:
  - `add_algorithm()`: Thêm thuật toán vào pipeline
  - `remove_algorithm()`: Xóa thuật toán khỏi pipeline
  - `on_pipeline_selection_changed()`: Enable/disable Remove button
  - `on_pipeline_reordered()`: Xử lý drag & drop reorder
- Cập nhật `process_image()`: Áp dụng toàn bộ pipeline thay vì 1 thuật toán
- Cập nhật `save_config()`: Lưu pipeline thay vì single algorithm
- Cập nhật `get_current_config()`: Trả về pipeline

**Kết quả:**
- File size: ~450 lines (giảm từ ~500 lines do xóa parameter widgets logic)
- Code đơn giản hơn, dễ maintain hơn

## Manual Test

Vui lòng test theo hướng dẫn tại: **docs/MANUAL_TEST_PREPROCESSING_PIPELINE.md**

### Test Cases chính:
1. ✅ Thêm thuật toán vào pipeline
2. ✅ Xóa thuật toán khỏi pipeline
3. ✅ Drag & drop để sắp xếp lại
4. ✅ Áp dụng pipeline phức tạp (3+ thuật toán)
5. ✅ Lưu và load config

## Commit

**Commit hash:** `434bf1197c780b99542e8ce224b4f1d5b87912ad`

**Commit message:** `[Feature] Multi-step Preprocessing Pipeline - Cho phép áp dụng nhiều thuật toán preprocessing theo thứ tự`

## Technical Notes

### Design Pattern
- **Pipeline Pattern**: Áp dụng chuỗi các transformations theo thứ tự
- **Drag & Drop**: Sử dụng Qt's built-in drag & drop với `InternalMove` mode

### Performance
- Mỗi lần thêm/xóa/reorder → process lại toàn bộ pipeline
- Với ảnh lớn + pipeline dài có thể chậm, nhưng acceptable cho use case hiện tại

### Future Improvements (nếu cần)
- Thêm khả năng edit parameters cho từng thuật toán trong pipeline
- Thêm nút "Clear All" để xóa toàn bộ pipeline
- Thêm preview cho từng bước trong pipeline (hiển thị intermediate results)
- Cache intermediate results để tránh reprocess khi chỉ thay đổi cuối pipeline

## Kết luận

Feature đã hoàn thành đầy đủ theo requirements. UI đơn giản, dễ sử dụng. Pipeline hoạt động chính xác theo thứ tự từ trên xuống dưới. Tất cả unit tests pass.
