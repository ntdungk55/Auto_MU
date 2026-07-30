# Manual Test Plan: Preprocessing Pipeline

## Mục đích
Test tính năng multi-step preprocessing pipeline trong tab Hiệu chỉnh.

---

## Test Case 1: Thêm thuật toán vào pipeline

**Mục đích:** Kiểm tra thêm thuật toán mới

**Các bước thực hiện:**
1. Mở tab "Hiệu chỉnh"
2. Load một ảnh (từ file hoặc clipboard)
3. Click nút "Add Algorithm"
4. Chọn "Upscale" từ dialog
5. Click OK

**Kết quả mong đợi:**
- "Upscale (2.0x)" xuất hiện trong list
- Ảnh output được upscale 2x
- Ảnh hiển thị ngay lập tức

---

## Test Case 2: Thêm nhiều thuật toán

**Mục đích:** Kiểm tra pipeline với nhiều thuật toán

**Các bước thực hiện:**
1. Tiếp tục từ Test Case 1
2. Click "Add Algorithm" → chọn "Enhance Contrast"
3. Click "Add Algorithm" → chọn "Sharpen"

**Kết quả mong đợi:**
- List có 3 items: Upscale, Enhance Contrast, Sharpen
- Ảnh output được áp dụng cả 3 thuật toán theo thứ tự
- Chất lượng ảnh cải thiện rõ rệt

---

## Test Case 3: Drag & Drop để sắp xếp

**Mục đích:** Kiểm tra sắp xếp thứ tự thuật toán

**Các bước thực hiện:**
1. Tiếp tục từ Test Case 2
2. Drag "Sharpen" lên trên "Enhance Contrast"
3. Thả chuột

**Kết quả mong đợi:**
- Thứ tự mới: Upscale, Sharpen, Enhance Contrast
- Ảnh output được cập nhật với thứ tự mới
- Kết quả khác với trước khi drag

---

## Test Case 4: Xóa thuật toán

**Mục đích:** Kiểm tra xóa thuật toán khỏi pipeline

**Các bước thực hiện:**
1. Tiếp tục từ Test Case 3
2. Click chọn "Sharpen" trong list
3. Click nút "Remove"

**Kết quả mong đợi:**
- "Sharpen" bị xóa khỏi list
- List còn 2 items: Upscale, Enhance Contrast
- Ảnh output được cập nhật (không có sharpen)

---

## Test Case 5: Clear All

**Mục đích:** Kiểm tra xóa tất cả thuật toán

**Các bước thực hiện:**
1. Tiếp tục từ Test Case 4
2. Click nút "Clear All"

**Kết quả mong đợi:**
- List rỗng
- Ảnh output = ảnh gốc (không có preprocessing)

---

## Test Case 6: Thêm cùng thuật toán nhiều lần

**Mục đích:** Kiểm tra thêm duplicate algorithm

**Các bước thực hiện:**
1. Click "Add Algorithm" → "Upscale"
2. Click "Add Algorithm" → "Upscale" lần nữa

**Kết quả mong đợi:**
- List có 2 items "Upscale (2.0x)"
- Ảnh được upscale 2 lần (4x tổng cộng)

---

## Test Case 7: Pipeline rỗng

**Mục đích:** Kiểm tra khi không có thuật toán nào

**Các bước thực hiện:**
1. Đảm bảo list rỗng (Clear All nếu cần)
2. Load ảnh mới

**Kết quả mong đợi:**
- Ảnh output = ảnh gốc
- Không có lỗi

---

## Test Case 8: Load ảnh mới với pipeline có sẵn

**Mục đích:** Kiểm tra pipeline được giữ nguyên khi load ảnh mới

**Các bước thực hiện:**
1. Tạo pipeline: Upscale → Enhance Contrast
2. Load ảnh mới

**Kết quả mong đợi:**
- Pipeline vẫn giữ nguyên
- Ảnh mới được áp dụng pipeline
- Kết quả hiển thị ngay

---

## Lưu ý
- Test với nhiều loại ảnh khác nhau (màu, grayscale, kích thước khác nhau)
- Kiểm tra performance với pipeline dài (>5 thuật toán)
- Kiểm tra drag & drop hoạt động mượt mà
