# Manual Test: Process Selection for Algorithm Testing Dialog

## Mục đích
Test tính năng chọn process/window để chụp ảnh trong Multi-Image Algorithm Testing Dialog.

## Điều kiện tiên quyết
- Có ít nhất 2 window/process đang chạy (ví dụ: Notepad, Calculator, MU Online)
- Đã có một tool với action IMAGE_DETECT hoặc MOUSE_CLICK có teaching image

## Test Case 1: Mở Dialog và Kiểm tra UI

**Các bước thực hiện:**
1. Mở main app
2. Chọn một tool có action IMAGE_DETECT/MOUSE_CLICK
3. Click "Sửa Tool" 
4. Chọn một action có teaching image
5. Click "Multi-Image Algorithm Testing"

**Kết quả mong đợi:**
- Dialog mở thành công
- Có dropdown chọn window cạnh nút "📷 Capture New"
- Dropdown hiển thị danh sách windows có sẵn
- Có nút "🔄" để refresh danh sách window
- Layout không bị vỡ

## Test Case 2: Chọn Window và Capture

**Các bước thực hiện:**
1. Mở thêm một app khác (ví dụ: Notepad, Calculator)
2. Trong dialog, chọn window khác từ dropdown
3. Click "📷 Capture New"

**Kết quả mong đợi:**
- Screenshot được chụp từ window đã chọn (không phải window mặc định)
- Ảnh được thêm vào danh sách captures
- Ảnh hiển thị đúng nội dung của window đã chọn

## Test Case 3: Refresh Window List

**Các bước thực hiện:**
1. Mở thêm một app mới
2. Click nút "🔄" để refresh danh sách
3. Kiểm tra dropdown

**Kết quả mong đợi:**
- Danh sách window được cập nhật
- App mới xuất hiện trong dropdown
- Selection hiện tại được giữ nguyên (nếu window vẫn tồn tại)

## Test Case 4: Không có Window nào

**Các bước thực hiện:**
1. Đóng tất cả windows có thể (trừ main app)
2. Click "🔄" để refresh
3. Thử capture

**Kết quả mong đợi:**
- Dropdown hiển thị "Không tìm thấy window"
- Click "📷 Capture New" hiển thị warning "Chưa chọn window để chụp ảnh!"

## Test Case 5: Window bị đóng giữa chừng

**Các bước thực hiện:**
1. Chọn một window từ dropdown
2. Đóng window đó
3. Click "📷 Capture New"

**Kết quả mong đợi:**
- Hiển thị error message phù hợp
- App không crash

## Cài đặt cần kiểm tra
- Window selection hoạt động độc lập với main app window selection
- Capture từ window đã chọn thay vì window mặc định
- UI responsive và không bị vỡ layout
- Error handling khi window không tồn tại

## Ghi chú
- Feature này cho phép test algorithm với ảnh từ nhiều window khác nhau
- Không ảnh hưởng đến functionality hiện tại
- Backward compatible - vẫn dùng target_window_hwnd làm default