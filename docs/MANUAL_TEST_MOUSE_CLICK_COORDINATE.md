# Manual Test Plan: Mouse Click Coordinate Mode

## Test Case 1: Chọn chế độ click trong dialog settings

**Mục đích:** Kiểm tra dropdown chọn chế độ click hoạt động đúng

**Điều kiện tiên quyết:**
- App đang chạy
- Có tool với action MOUSE_CLICK

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action MOUSE_CLICK
3. Click "Cài đặt"
4. Tìm dropdown "Chế độ click"
5. Chọn "Click theo tọa độ"
6. Quan sát UI thay đổi
7. Chọn lại "Click theo hình ảnh"
8. Quan sát UI thay đổi

**Kết quả mong đợi:**
- Dropdown hiển thị 2 options: "Click theo hình ảnh", "Click theo tọa độ"
- Khi chọn "Click theo tọa độ": ẩn layouts Nhận diện ảnh, Ảnh Teaching; hiện layout Teaching điểm click
- Khi chọn "Click theo hình ảnh": hiện layouts Nhận diện ảnh, Ảnh Teaching; ẩn layout Teaching điểm click
- Layouts chung (Thời gian chờ, Tùy chọn click, Nhảy về step) luôn hiện

---

## Test Case 2: Teaching điểm click cho chế độ tọa độ

**Mục đích:** Kiểm tra teaching điểm click hoạt động đúng

**Điều kiện tiên quyết:**
- App đang chạy
- Có window game đang mở
- Đã chọn chế độ "Click theo tọa độ"

**Các bước thực hiện:**
1. Trong dialog settings, click button "Teaching điểm click"
2. Dialog Teaching mở ra
3. Kiểm tra button "Chọn vùng" bị disable/ẩn
4. Click "Chụp ảnh"
5. Click "Chọn điểm click"
6. Click vào vị trí muốn click trên ảnh
7. Click "OK"
8. Quan sát tọa độ hiển thị trong dialog settings

**Kết quả mong đợi:**
- Dialog Teaching mở ra với button "Chọn vùng" bị disable
- Có thể chụp ảnh và chọn điểm click
- Sau khi OK, tọa độ (X, Y) hiển thị trong dialog settings
- Tọa độ là client coordinates (trong window game)

---

## Test Case 3: Restore điểm click khi mở lại dialog

**Mục đích:** Kiểm tra điểm click được restore khi mở lại dialog teaching

**Điều kiện tiên quyết:**
- Đã teaching điểm click cho chế độ tọa độ (Test Case 2)

**Các bước thực hiện:**
1. Đóng dialog settings
2. Mở lại dialog settings
3. Click button "Teaching điểm click"
4. Quan sát dialog Teaching

**Kết quả mong đợi:**
- Dialog Teaching hiển thị ảnh đã chụp trước đó
- Điểm click (marker xanh) hiển thị đúng vị trí đã chọn

---

## Test Case 4: Persistence - Save và Load

**Mục đích:** Kiểm tra settings được lưu và load đúng

**Điều kiện tiên quyết:**
- Đã cấu hình action với chế độ "Click theo tọa độ"

**Các bước thực hiện:**
1. Cấu hình action với chế độ "Click theo tọa độ"
2. Teaching điểm click tại (100, 200)
3. Click OK để lưu
4. Đóng app hoàn toàn
5. Mở lại app
6. Mở Tool Editor
7. Chọn action đã cấu hình
8. Click "Cài đặt"

**Kết quả mong đợi:**
- Dropdown hiển thị "Click theo tọa độ"
- Tọa độ hiển thị (100, 200)
- Mở dialog Teaching thấy điểm click đúng vị trí

---

## Test Case 5: Chuyển đổi chế độ - Xóa resources cũ

**Mục đích:** Kiểm tra resources cũ được xóa khi chuyển chế độ

**Điều kiện tiên quyết:**
- Đã cấu hình action với chế độ "Click theo hình ảnh" (có ảnh teaching)

**Các bước thực hiện:**
1. Mở dialog settings của action có ảnh teaching
2. Ghi nhớ đường dẫn ảnh teaching
3. Chuyển sang chế độ "Click theo tọa độ"
4. Click OK để lưu
5. Kiểm tra file ảnh teaching cũ

**Kết quả mong đợi:**
- File ảnh teaching cũ bị xóa
- Các fields image_path, click_x, click_y bị clear

---

## Test Case 6: Runtime - Click theo tọa độ

**Mục đích:** Kiểm tra action click theo tọa độ hoạt động đúng

**Điều kiện tiên quyết:**
- Đã cấu hình action với chế độ "Click theo tọa độ"
- Đã teaching điểm click

**Các bước thực hiện:**
1. Chạy tool
2. Quan sát action MOUSE_CLICK thực thi
3. Kiểm tra vị trí click

**Kết quả mong đợi:**
- Click đúng vào vị trí đã teaching
- Log hiển thị "Click tại (X, Y)"
- Không có template matching (không tìm ảnh)

---

## Test Case 7: Runtime - Click theo hình ảnh (không thay đổi)

**Mục đích:** Kiểm tra chế độ click theo hình ảnh vẫn hoạt động như cũ

**Điều kiện tiên quyết:**
- Đã cấu hình action với chế độ "Click theo hình ảnh"
- Đã teaching ảnh và điểm click

**Các bước thực hiện:**
1. Chạy tool
2. Quan sát action MOUSE_CLICK thực thi

**Kết quả mong đợi:**
- Template matching hoạt động bình thường
- Click đúng vào vị trí trong ảnh đã teaching
- Log hiển thị "Tìm thấy ảnh (score: X.XX)"

---

## Test Case 8: Error handling - Tọa độ không hợp lệ

**Mục đích:** Kiểm tra xử lý lỗi khi tọa độ không hợp lệ

**Điều kiện tiên quyết:**
- Action với chế độ "Click theo tọa độ" nhưng chưa teaching

**Các bước thực hiện:**
1. Tạo action MOUSE_CLICK mới
2. Chọn chế độ "Click theo tọa độ"
3. KHÔNG teaching điểm click
4. Chạy tool

**Kết quả mong đợi:**
- Action fail với log lỗi rõ ràng
- Log: "Thất bại: chưa cấu hình tọa độ click"
