# Manual Test Plan: Algorithm Testing OCR Section

## Mô tả
Test tính năng OCR trong Algorithm Testing Dialog với logic mới:
- Đọc text từ **ảnh screenshot** đang được chọn (không phải teaching image)
- Hỗ trợ **Fixed ROI** crop ảnh trước khi OCR
- Bảng kết quả **7 cột**: No., Engine, Algorithms, Screenshot, Text, Conf, Time (ms)
- Mỗi lần "Run OCR" **thêm 1 dòng mới** (không thay thế)

---

## Test Case 1: Kiểm tra bảng kết quả 7 cột

**Mục đích:** Xác nhận bảng OCR Results có đúng 7 cột

**Điều kiện tiên quyết:**
- Mở Algorithm Testing Dialog từ một action có teaching image

**Các bước thực hiện:**
1. Mở dialog Algorithm Testing
2. Nhìn vào section "OCR Testing" bên phải
3. Kiểm tra bảng "OCR Results"

**Kết quả mong đợi:**
- Bảng có đúng 7 cột: No., Engine, Algorithms, Screenshot, Text, Conf, Time (ms)

---

## Test Case 2: OCR đọc từ screenshot đang chọn

**Mục đích:** Xác nhận OCR đọc từ ảnh screenshot (không phải teaching image)

**Điều kiện tiên quyết:**
- Có ít nhất 1 ảnh trong Window Captures List

**Các bước thực hiện:**
1. Chọn 1 ảnh screenshot trong danh sách Window Captures
2. Nhấn "▶️ Run OCR"
3. Chờ kết quả

**Kết quả mong đợi:**
- Cột "Screenshot" hiển thị tên file ảnh đang được chọn
- Text được đọc từ ảnh screenshot đó (không phải teaching image)
- Cột "Algorithms" hiển thị "None" nếu chưa add algorithm nào

---

## Test Case 3: OCR với Fixed ROI

**Mục đích:** Xác nhận OCR crop ảnh theo Fixed ROI khi được bật

**Điều kiện tiên quyết:**
- Action có `use_fixed_roi = True` với ROI hợp lệ (roi_x, roi_y, roi_w, roi_h)
- Có ít nhất 1 ảnh screenshot

**Các bước thực hiện:**
1. Mở dialog từ action có Fixed ROI được bật
2. Chọn 1 ảnh screenshot
3. Nhấn "▶️ Run OCR"

**Kết quả mong đợi:**
- OCR chỉ đọc vùng ROI của ảnh (không đọc toàn bộ)
- Kết quả text phản ánh nội dung trong vùng ROI

---

## Test Case 4: OCR không có Fixed ROI (đọc toàn bộ ảnh)

**Mục đích:** Xác nhận OCR đọc toàn bộ ảnh khi Fixed ROI tắt

**Điều kiện tiên quyết:**
- Action có `use_fixed_roi = False`
- Có ít nhất 1 ảnh screenshot

**Các bước thực hiện:**
1. Mở dialog từ action không có Fixed ROI
2. Chọn 1 ảnh screenshot
3. Nhấn "▶️ Run OCR"

**Kết quả mong đợi:**
- OCR đọc toàn bộ ảnh screenshot
- Text kết quả đầy đủ hơn so với khi dùng ROI

---

## Test Case 5: OCR với algorithms

**Mục đích:** Xác nhận cột Algorithms hiển thị đúng tên thuật toán đã áp dụng

**Điều kiện tiên quyết:**
- Có ít nhất 1 ảnh screenshot

**Các bước thực hiện:**
1. Add 2 algorithms vào danh sách: "Upscale 2x" và "Enhance Contrast"
2. Chọn 1 ảnh screenshot
3. Nhấn "▶️ Run OCR"

**Kết quả mong đợi:**
- Cột "Algorithms" hiển thị: "🔍 Upscale 2x, ✨ Enhance Contrast"
- OCR được thực hiện sau khi áp dụng các thuật toán đó

---

## Test Case 6: Nhiều lần Run OCR tích lũy kết quả

**Mục đích:** Xác nhận mỗi lần Run OCR thêm 1 dòng mới (không xóa dòng cũ)

**Điều kiện tiên quyết:**
- Có ít nhất 2 ảnh screenshot

**Các bước thực hiện:**
1. Chọn ảnh screenshot thứ 1, nhấn "▶️ Run OCR"
2. Chờ kết quả (dòng 1 xuất hiện)
3. Chọn ảnh screenshot thứ 2, nhấn "▶️ Run OCR"
4. Chờ kết quả

**Kết quả mong đợi:**
- Bảng có 2 dòng
- Dòng 1: screenshot thứ 1
- Dòng 2: screenshot thứ 2
- Dòng 1 không bị xóa

---

## Test Case 7: Chuyển ảnh xóa kết quả cũ

**Mục đích:** Xác nhận khi chọn ảnh khác, bảng OCR Results bị xóa

**Điều kiện tiên quyết:**
- Đã có kết quả OCR trong bảng

**Các bước thực hiện:**
1. Chạy OCR cho ảnh A → có kết quả trong bảng
2. Click chọn ảnh B trong danh sách

**Kết quả mong đợi:**
- Bảng OCR Results bị xóa sạch khi chọn ảnh mới

---

## Test Case 8: OCR không có ảnh được chọn

**Mục đích:** Xác nhận thông báo lỗi khi chưa chọn ảnh

**Điều kiện tiên quyết:**
- Không có ảnh nào được chọn trong danh sách

**Các bước thực hiện:**
1. Không chọn ảnh nào
2. Nhấn "▶️ Run OCR"

**Kết quả mong đợi:**
- Không crash
- In ra log: "[OCR] Vui lòng chọn một ảnh screenshot để chạy OCR"
- Nút Run OCR vẫn enabled
