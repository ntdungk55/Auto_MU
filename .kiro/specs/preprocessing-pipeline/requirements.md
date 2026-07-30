# Feature: Multi-step Preprocessing Pipeline

## 1. Tổng quan
Cho phép áp dụng nhiều thuật toán preprocessing liên tiếp trong tab "Hiệu chỉnh", thay vì chỉ chọn 1 thuật toán như hiện tại. Các thuật toán được áp dụng theo thứ tự từ trên xuống dưới trong một pipeline.

## 2. User Stories
- Là người dùng, tôi muốn thêm nhiều thuật toán preprocessing vào một pipeline, để có thể xử lý ảnh phức tạp hơn
- Là người dùng, tôi muốn sắp xếp thứ tự các thuật toán bằng drag & drop, để dễ dàng thay đổi pipeline
- Là người dùng, tôi muốn xóa thuật toán khỏi pipeline, để điều chỉnh xử lý
- Là người dùng, tôi muốn thấy kết quả ngay khi thêm/xóa/sắp xếp thuật toán, để biết pipeline có hiệu quả không

## 3. Acceptance Criteria
1. UI có QListWidget hiển thị danh sách các thuật toán trong pipeline
2. Có nút "Add Algorithm" để thêm thuật toán mới vào pipeline
3. Có nút "Remove" để xóa thuật toán đã chọn khỏi pipeline
4. QListWidget hỗ trợ drag & drop để sắp xếp thứ tự
5. Khi thêm/xóa/sắp xếp thuật toán, ảnh output được cập nhật ngay lập tức
6. Các thuật toán được áp dụng theo thứ tự từ trên xuống dưới
7. Mỗi thuật toán có giá trị parameters mặc định

## 4. Input/Output

**Input:**
- Ảnh gốc (từ file hoặc clipboard)
- Danh sách các thuật toán được chọn
- Thứ tự các thuật toán trong pipeline
- Parameters cho mỗi thuật toán (mặc định)

**Output:**
- Ảnh sau khi đã áp dụng tất cả các thuật toán theo thứ tự

## 5. Sơ đồ khối

```
┌─────────────────┐
│   Ảnh gốc       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Algorithm 1    │ (ví dụ: Upscale 2x)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Algorithm 2    │ (ví dụ: Enhance Contrast)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Algorithm 3    │ (ví dụ: Sharpen)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ảnh output     │
└─────────────────┘
```

## 6. Technical Notes

**Các thuật toán hiện có:**
- Upscale (factor: 2.0)
- Enhance Contrast
- Sharpen
- Denoise
- Grayscale
- Threshold (value: 127)
- Invert

**UI Components:**
- QListWidget với drag & drop enabled
- QPushButton "Add Algorithm" → mở dialog chọn thuật toán
- QPushButton "Remove" → xóa item đã chọn
- QPushButton "Clear All" → xóa tất cả

**Data Structure:**
```python
pipeline = [
    {"algorithm": "upscale", "params": {"factor": 2.0}},
    {"algorithm": "enhance_contrast", "params": {}},
    {"algorithm": "sharpen", "params": {}},
]
```

**Ràng buộc:**
- Pipeline có thể rỗng (không áp dụng thuật toán nào)
- Có thể thêm cùng một thuật toán nhiều lần
- Drag & drop chỉ trong cùng một list (không drag ra ngoài)
