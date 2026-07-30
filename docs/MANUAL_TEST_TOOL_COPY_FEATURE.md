# Manual Test Plan: Tool Copy Feature

## Test Case 1: Basic Tool Copy
**Mục đích:** Kiểm tra chức năng copy tool cơ bản

**Điều kiện tiên quyết:**
- App đã khởi động
- Có ít nhất 1 tool trong hệ thống
- Đang ở màn Home

**Các bước thực hiện:**
1. Chọn một tool trong combo "Chọn tool"
2. Click button "Sao chép Tool"
3. Trong dialog, nhập tên mới: "Test Copy Tool"
4. Click "OK"

**Kết quả mong đợi:**
- Dialog đóng
- Hiển thị message "Đã sao chép tool thành công: Test Copy Tool"
- Tool combo refresh và chọn tool mới
- Tool mới xuất hiện trong danh sách

**Cài đặt cần kiểm tra:**
- Tool copy có UUID khác với tool gốc
- Tool copy có tên "Test Copy Tool"
- Tool copy có cùng settings với tool gốc

---

## Test Case 2: Copy Tool với Teaching Images
**Mục đích:** Kiểm tra copy tool có teaching images

**Điều kiện tiên quyết:**
- Có tool với teaching images (action có image_path)
- Images tồn tại trong thư mục images/{tool_id}/

**Các bước thực hiện:**
1. Chọn tool có teaching images
2. Click "Sao chép Tool"
3. Nhập tên: "Tool with Images Copy"
4. Click "OK"
5. Kiểm tra thư mục images/{new_tool_id}/

**Kết quả mong đợi:**
- Tool copy thành công
- Thư mục images/{new_tool_id}/ được tạo
- Tất cả teaching images được copy
- Image paths trong actions được update

**Cài đặt cần kiểm tra:**
- Thư mục images/{new_tool_id}/ tồn tại
- Files images có nội dung giống tool gốc
- Action image_path chứa new_tool_id thay vì old_tool_id

---

## Test Case 3: Button Enable/Disable
**Mục đích:** Kiểm tra trạng thái button "Sao chép Tool"

**Điều kiện tiên quyết:**
- App đã khởi động
- Đang ở màn Home

**Các bước thực hiện:**
1. Không chọn tool nào (combo trống hoặc "Chưa có tool nào")
2. Quan sát button "Sao chép Tool"
3. Chọn một tool bất kỳ
4. Quan sát button "Sao chép Tool"

**Kết quả mong đợi:**
- Bước 2: Button "Sao chép Tool" bị disable (xám)
- Bước 4: Button "Sao chép Tool" được enable (có thể click)

**Cài đặt cần kiểm tra:**
- Button placement giữa "Sửa Tool" và "Xóa Tool"
- Button text là "Sao chép Tool"

---

## Test Case 4: Validation - Tên Trống
**Mục đích:** Kiểm tra validation khi nhập tên trống

**Điều kiện tiên quyết:**
- Có tool để copy
- Dialog copy tool đã mở

**Các bước thực hiện:**
1. Để trống input field
2. Click "OK"
3. Thử nhập chỉ khoảng trắng "   "
4. Click "OK"

**Kết quả mong đợi:**
- Bước 2: Hiển thị lỗi "Tên tool không được để trống"
- Bước 4: Hiển thị lỗi "Tên tool không được để trống"
- Dialog không đóng
- Tool không được tạo

**Cài đặt cần kiểm tra:**
- Error message rõ ràng và dễ hiểu
- Input field focus vào để user sửa

---

## Test Case 5: Validation - Tên Trùng
**Mục đích:** Kiểm tra validation khi nhập tên đã tồn tại

**Điều kiện tiên quyết:**
- Có ít nhất 2 tools trong hệ thống
- Dialog copy tool đã mở

**Các bước thực hiện:**
1. Nhập tên của tool khác đã tồn tại
2. Click "OK"

**Kết quả mong đợi:**
- Hiển thị lỗi "Tên tool đã tồn tại"
- Dialog không đóng
- Tool không được tạo

**Cài đặt cần kiểm tra:**
- Error message chính xác
- Có thể thử tên khác mà không cần đóng dialog

---

## Test Case 6: Cancel Dialog
**Mục đích:** Kiểm tra hủy bỏ copy tool

**Điều kiện tiên quyết:**
- Dialog copy tool đã mở

**Các bước thực hiện:**
1. Nhập tên bất kỳ
2. Click "Cancel" hoặc nhấn ESC
3. Kiểm tra danh sách tools

**Kết quả mong đợi:**
- Dialog đóng
- Không có tool mới được tạo
- Không có message nào hiển thị
- Tool combo không thay đổi

**Cài đặt cần kiểm tra:**
- Dialog đóng sạch sẽ
- Không có side effects

---

## Test Case 7: Copy Tool Phức Tạp
**Mục đích:** Kiểm tra copy tool có nhiều settings phức tạp

**Điều kiện tiên quyết:**
- Có tool với settings phức tạp:
  - Loop enabled với count mode
  - Timeout notifications enabled
  - Input blocking enabled
  - Multiple actions với các settings khác nhau

**Các bước thực hiện:**
1. Chọn tool phức tạp
2. Copy với tên "Complex Copy"
3. Mở Tool Settings của tool copy
4. So sánh với tool gốc

**Kết quả mong đợi:**
- Tất cả settings được copy chính xác
- Loop settings giống hệt
- Notification settings giống hệt
- Input blocking settings giống hệt
- Tất cả actions với đầy đủ properties

**Cài đặt cần kiểm tra:**
- Loop enabled: True/False
- Loop mode: forever/count
- Loop count: số chính xác
- Pre/post delays: giá trị chính xác
- Timeout behaviors: stop/restart
- User input mode: ignore/pause/stop
- Notification settings: enabled/disabled
- Input blocking: enabled/disabled với duration

---

## Test Case 8: Independence Test
**Mục đích:** Kiểm tra tool copy độc lập với tool gốc

**Điều kiện tiên quyết:**
- Đã copy tool thành công

**Các bước thực hiện:**
1. Mở Tool Settings của tool gốc
2. Thay đổi một số settings (ví dụ: loop count)
3. Save và đóng
4. Mở Tool Settings của tool copy
5. Kiểm tra settings

**Kết quả mong đợi:**
- Tool copy không bị ảnh hưởng bởi thay đổi của tool gốc
- Settings của tool copy vẫn giữ nguyên giá trị ban đầu
- Có thể chỉnh sửa tool copy độc lập

**Cài đặt cần kiểm tra:**
- Tool copy có UUID riêng
- File JSON riêng trong thư mục tools/
- Thư mục images riêng (nếu có)

---

## Test Case 9: Error Handling
**Mục đích:** Kiểm tra xử lý lỗi khi copy thất bại

**Điều kiện tiên quyết:**
- Có tool để copy
- Tạo điều kiện lỗi (ví dụ: readonly filesystem, disk full)

**Các bước thực hiện:**
1. Thử copy tool trong điều kiện lỗi
2. Quan sát error message
3. Kiểm tra trạng thái hệ thống

**Kết quả mong đợi:**
- Hiển thị error message rõ ràng
- Không tạo tool không hoàn chỉnh
- Hệ thống vẫn ổn định
- Có thể thử lại sau khi fix lỗi

**Cài đặt cần kiểm tra:**
- Error message có ý nghĩa
- Không có partial files được tạo
- App không crash

---

## Test Case 10: Performance Test
**Mục đích:** Kiểm tra performance khi copy tool lớn

**Điều kiện tiên quyết:**
- Tool có nhiều actions (>50)
- Tool có nhiều teaching images (>20 files)
- Images có kích thước lớn

**Các bước thực hiện:**
1. Copy tool lớn
2. Đo thời gian thực hiện
3. Kiểm tra memory usage
4. Verify tính đúng đắn của copy

**Kết quả mong đợi:**
- Copy hoàn thành trong thời gian hợp lý (<30s)
- Memory usage không tăng quá mức
- Tất cả data được copy chính xác
- UI không bị freeze

**Cài đặt cần kiểm tra:**
- Progress indication (nếu có)
- Responsive UI during copy
- Complete data integrity