# Manual Test Plan: Algorithm Parameters Settings Dialog

## Test Case 1: Mở Settings Dialog bằng Double-Click

**Mục đích:** Kiểm tra việc mở dialog khi double-click vào item

**Điều kiện tiên quyết:**
- Đã tải ảnh lên
- Đã thêm ít nhất 1 thuật toán có parameters vào pipeline (ví dụ: Gaussian Blur)

**Các bước thực hiện:**
1. Mở tab "Hiệu chỉnh"
2. Tải ảnh lên
3. Thêm thuật toán "Gaussian Blur" vào pipeline
4. Double-click vào item "Gaussian Blur" trong list

**Kết quả mong đợi:**
- Dialog "Algorithm Parameters" mở ra
- Hiển thị parameter "Kernel Size" với giá trị mặc định 5
- Có nút OK và Cancel

---

## Test Case 2: Preview Realtime khi Thay Đổi Parameters

**Mục đích:** Kiểm tra preview ngay lập tức khi thay đổi parameter

**Điều kiện tiên quyết:**
- Dialog Settings đang mở (từ Test Case 1)

**Các bước thực hiện:**
1. Thay đổi "Kernel Size" từ 5 → 11
2. Quan sát ảnh preview

**Kết quả mong đợi:**
- Ảnh preview cập nhật ngay lập tức
- Ảnh bị blur nhiều hơn (do kernel size lớn hơn)
- Pipeline list vẫn hiển thị "Gaussian Blur" (chưa thay đổi)

---

## Test Case 3: Click OK để Lưu Thay Đổi

**Mục đích:** Kiểm tra việc lưu parameters khi click OK

**Điều kiện tiên quyết:**
- Dialog Settings đang mở
- Đã thay đổi parameter (ví dụ: Kernel Size = 11)

**Các bước thực hiện:**
1. Click nút OK
2. Quan sát ảnh processed và pipeline

**Kết quả mong đợi:**
- Dialog đóng lại
- Ảnh processed vẫn giữ nguyên kết quả (blur với kernel size 11)
- Nếu double-click lại vào item → Kernel Size hiển thị 11 (đã lưu)

---

## Test Case 4: Click Cancel để Hủy Thay Đổi

**Mục đích:** Kiểm tra việc restore parameters khi click Cancel

**Điều kiện tiên quyết:**
- Đã thêm thuật toán "Gaussian Blur" với Kernel Size = 5
- Đã lưu (OK) một lần

**Các bước thực hiện:**
1. Double-click vào "Gaussian Blur"
2. Thay đổi Kernel Size từ 5 → 15
3. Quan sát preview (ảnh blur nhiều)
4. Click Cancel
5. Quan sát ảnh processed

**Kết quả mong đợi:**
- Dialog đóng lại
- Ảnh processed trở về trạng thái cũ (blur với kernel size 5)
- Nếu double-click lại → Kernel Size vẫn là 5 (không lưu thay đổi)

---

## Test Case 5: Thuật Toán Không Có Parameters

**Mục đích:** Kiểm tra dialog với thuật toán không có parameters

**Điều kiện tiên quyết:**
- Đã tải ảnh lên

**Các bước thực hiện:**
1. Thêm thuật toán "Upscale 2x" vào pipeline
2. Double-click vào item "Upscale 2x"

**Kết quả mong đợi:**
- Dialog mở ra
- Hiển thị thông báo "Thuật toán này không có tham số"
- Chỉ có nút Close (không có OK/Cancel)

---

## Test Case 6: Nhiều Thuật Toán với Parameters Độc Lập

**Mục đích:** Kiểm tra việc edit parameters của nhiều thuật toán độc lập

**Điều kiện tiên quyết:**
- Đã tải ảnh lên

**Các bước thực hiện:**
1. Thêm "Gaussian Blur" (Kernel Size = 5)
2. Thêm "CLAHE" (Clip Limit = 2.0, Tile Grid Size = 8)
3. Double-click vào "Gaussian Blur" → Đổi Kernel Size = 9 → OK
4. Double-click vào "CLAHE" → Kiểm tra parameters

**Kết quả mong đợi:**
- CLAHE vẫn giữ parameters cũ (Clip Limit = 2.0, Tile Grid Size = 8)
- Gaussian Blur đã thay đổi (Kernel Size = 9)
- Hai thuật toán không ảnh hưởng lẫn nhau

---

## Test Case 7: Step Size Phù Hợp với Range

**Mục đích:** Kiểm tra step size tự động

**Điều kiện tiên quyết:**
- Đã tải ảnh lên

**Các bước thực hiện:**
1. Thêm "Binary Threshold" vào pipeline
2. Double-click vào item
3. Quan sát step size của "Threshold" (range: 0-255)

**Kết quả mong đợi:**
- Step size = 1 (vì range = 255, phù hợp với step = 1)
- Có thể tăng/giảm từng đơn vị 1

---

## Test Case 8: Pipeline với 3+ Thuật Toán

**Mục đích:** Kiểm tra edit parameters trong pipeline phức tạp

**Điều kiện tiên quyết:**
- Đã tải ảnh lên

**Các bước thực hiện:**
1. Thêm "Upscale 2x"
2. Thêm "Gaussian Blur" (Kernel Size = 5)
3. Thêm "CLAHE" (Clip Limit = 2.0)
4. Double-click vào "Gaussian Blur" → Đổi Kernel Size = 7 → OK
5. Quan sát ảnh processed

**Kết quả mong đợi:**
- Ảnh được xử lý theo thứ tự: Upscale → Gaussian Blur (kernel=7) → CLAHE
- Preview chính xác với pipeline đã chỉnh

---

## Test Case 9: Lưu Config với Parameters Đã Chỉnh

**Mục đích:** Kiểm tra việc lưu config với parameters đã edit

**Điều kiện tiên quyết:**
- Đã thêm và edit parameters của thuật toán

**Các bước thực hiện:**
1. Thêm "Gaussian Blur" → Edit Kernel Size = 9 → OK
2. Click "💾 Lưu cấu hình cho OCR"
3. Mở file `preprocessing_config.json` để kiểm tra

**Kết quả mong đợi:**
- File JSON chứa:
```json
{
  "pipeline": [
    {
      "algorithm": "gaussian_blur",
      "params": {
        "kernel_size": 9
      }
    }
  ]
}
```

---

## Cài đặt cần kiểm tra

Không có settings đặc biệt cho feature này.

---

## Ghi chú

- Test trên nhiều loại thuật toán khác nhau (có params, không có params)
- Test với ảnh lớn để kiểm tra performance của preview
- Test Cancel nhiều lần để đảm bảo không bị memory leak
