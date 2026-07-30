# Manual Test Plan: Tool ID System

## Mục đích
Kiểm tra hệ thống quản lý tools bằng UUID hoạt động đúng, cho phép rename tool mà không tạo duplicate.

---

## Test Case 1: Migration Script

**Mục đích:** Verify migration script chạy thành công và migrate tất cả tools

**Điều kiện tiên quyết:**
- Có ít nhất 2-3 tools hiện tại trong `tools/`
- Có teaching images trong `images/{tool_name}/`
- App đang đóng

**Các bước thực hiện:**
1. Backup thủ công `tools/` và `images/` (để so sánh)
2. Chạy migration script: `python tools/migrate_to_uuid.py`
3. Kiểm tra console output - không có errors
4. Kiểm tra `tools_backup/` và `images_backup/` đã được tạo
5. Kiểm tra `tools/` chỉ có files với tên UUID (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.json`)
6. Mở 1 file JSON, verify có field `"id"` với giá trị UUID
7. Kiểm tra `images/` chỉ có folders với tên UUID
8. Verify số lượng tools và images không thay đổi

**Kết quả mong đợi:**
- ✅ Migration script chạy thành công, không có errors
- ✅ Backup folders được tạo với đầy đủ files
- ✅ Tất cả tools có field `id` với UUID hợp lệ
- ✅ Teaching images được move vào folders UUID
- ✅ Files/folders cũ đã bị xóa
- ✅ Số lượng tools và images không đổi

**Cài đặt cần kiểm tra:**
- N/A (migration script)

---

## Test Case 2: Load Tools Sau Migration

**Mục đích:** Verify app load được tools sau migration

**Điều kiện tiên quyết:**
- Đã chạy migration script thành công
- App đang đóng

**Các bước thực hiện:**
1. Khởi động app
2. Kiểm tra tool combo dropdown
3. Verify tất cả tools hiển thị đúng tên
4. Chọn từng tool và verify settings load đúng
5. Kiểm tra log - không có errors

**Kết quả mong đợi:**
- ✅ App khởi động thành công
- ✅ Tool combo hiển thị đầy đủ tools với tên đúng
- ✅ Chọn tool load đúng settings
- ✅ Không có errors trong log

**Cài đặt cần kiểm tra:**
- Tool combo: Hiển thị tên tools
- Tool settings: Loop, timeout, etc.

---

## Test Case 3: Rename Tool

**Mục đích:** Verify rename tool không tạo duplicate

**Điều kiện tiên quyết:**
- App đang chạy
- Có ít nhất 1 tool

**Các bước thực hiện:**
1. Chọn tool "Tool A" trong combo
2. Click "Sửa Tool"
3. Đổi tên thành "Tool A Renamed"
4. Click "Lưu"
5. Đóng dialog
6. Kiểm tra tool combo - chỉ có "Tool A Renamed", không có "Tool A"
7. Kiểm tra folder `tools/` - chỉ có 1 file JSON cho tool này
8. Mở file JSON, verify `name` = "Tool A Renamed" và `id` không đổi

**Kết quả mong đợi:**
- ✅ Tool được rename thành công
- ✅ Không tạo tool mới (duplicate)
- ✅ Tool combo chỉ hiển thị tên mới
- ✅ File JSON có tên UUID không đổi
- ✅ Field `name` trong JSON được update
- ✅ Field `id` trong JSON không đổi

**Cài đặt cần kiểm tra:**
- Tool name: "Tool A Renamed"
- Tool ID: Không đổi

---

## Test Case 4: Rename Tool - Trùng Tên

**Mục đích:** Verify không cho phép rename tool thành tên đã tồn tại

**Điều kiện tiên quyết:**
- App đang chạy
- Có ít nhất 2 tools: "Tool A" và "Tool B"

**Các bước thực hiện:**
1. Chọn tool "Tool A"
2. Click "Sửa Tool"
3. Đổi tên thành "Tool B" (trùng với tool khác)
4. Click "Lưu"
5. Kiểm tra error dialog

**Kết quả mong đợi:**
- ✅ Hiển thị error dialog: "Tên tool đã tồn tại. Vui lòng chọn tên khác."
- ✅ Tool không được lưu
- ✅ Dialog không đóng
- ✅ User có thể sửa lại tên

**Cài đặt cần kiểm tra:**
- Error message: "Tên tool đã tồn tại. Vui lòng chọn tên khác."

---

## Test Case 5: Create New Tool

**Mục đích:** Verify tạo tool mới với UUID

**Điều kiện tiên quyết:**
- App đang chạy

**Các bước thực hiện:**
1. Click "Tạo Tool"
2. Nhập tên: "New Tool"
3. Thêm 1 action bất kỳ
4. Click "Lưu"
5. Kiểm tra tool combo - có "New Tool"
6. Kiểm tra folder `tools/` - có file JSON mới với tên UUID
7. Mở file JSON, verify có field `"id"` với UUID hợp lệ

**Kết quả mong đợi:**
- ✅ Tool mới được tạo thành công
- ✅ Tool có UUID unique
- ✅ File JSON có tên UUID
- ✅ Tool hiển thị trong combo

**Cài đặt cần kiểm tra:**
- Tool name: "New Tool"
- Tool ID: UUID hợp lệ (36 ký tự)

---

## Test Case 6: Delete Tool

**Mục đích:** Verify xóa tool theo UUID

**Điều kiện tiên quyết:**
- App đang chạy
- Có ít nhất 1 tool

**Các bước thực hiện:**
1. Chọn tool "Test Tool"
2. Click "Xóa Tool"
3. Confirm xóa
4. Kiểm tra tool combo - không còn "Test Tool"
5. Kiểm tra folder `tools/` - file JSON đã bị xóa
6. Kiểm tra folder `images/{tool_id}/` - đã bị xóa (nếu có)

**Kết quả mong đợi:**
- ✅ Tool được xóa thành công
- ✅ File JSON bị xóa
- ✅ Teaching images folder bị xóa
- ✅ Tool không còn trong combo

**Cài đặt cần kiểm tra:**
- N/A

---

## Test Case 7: Teaching Images Path

**Mục đích:** Verify teaching images được lưu theo tool ID

**Điều kiện tiên quyết:**
- App đang chạy
- Có 1 tool với UUID

**Các bước thực hiện:**
1. Chọn tool
2. Click "Sửa Tool"
3. Thêm action IMAGE_DETECT
4. Click "Tạo ảnh Teaching"
5. Chụp ảnh và crop
6. Click "Lưu"
7. Kiểm tra folder `images/{tool_id}/` - có file ảnh mới
8. Mở file JSON của tool, verify `image_path` có format `images/{tool_id}/capture_*.png`

**Kết quả mong đợi:**
- ✅ Teaching image được lưu vào `images/{tool_id}/`
- ✅ Path trong JSON đúng format
- ✅ Ảnh có thể load và hiển thị

**Cài đặt cần kiểm tra:**
- Image path: `images/{tool_id}/capture_*.png`

---

## Test Case 8: Rename Tool - Teaching Images Không Đổi

**Mục đích:** Verify rename tool không ảnh hưởng teaching images path

**Điều kiện tiên quyết:**
- App đang chạy
- Có 1 tool với teaching images

**Các bước thực hiện:**
1. Chọn tool có teaching images
2. Note lại image_path hiện tại (mở JSON file)
3. Click "Sửa Tool"
4. Đổi tên tool
5. Click "Lưu"
6. Mở JSON file, verify `image_path` không đổi
7. Verify ảnh vẫn load được

**Kết quả mong đợi:**
- ✅ Tool được rename thành công
- ✅ Image path không đổi (vẫn dùng tool ID)
- ✅ Teaching images vẫn load được
- ✅ Không có broken image paths

**Cài đặt cần kiểm tra:**
- Image path: Không đổi sau rename

---

## Test Case 9: Run Tool Sau Migration

**Mục đích:** Verify tool chạy bình thường sau migration

**Điều kiện tiên quyết:**
- App đang chạy
- Đã migration thành công
- Có 1 tool với actions

**Các bước thực hiện:**
1. Chọn window game
2. Chọn tool
3. Click "Chạy Tool" (F5)
4. Verify tool chạy bình thường
5. Kiểm tra log - không có errors
6. Verify actions execute đúng

**Kết quả mong đợi:**
- ✅ Tool chạy thành công
- ✅ Actions execute đúng
- ✅ Teaching images load được
- ✅ Không có errors

**Cài đặt cần kiểm tra:**
- Tool execution: Chạy bình thường
- Image detection: Hoạt động đúng

---

## Test Case 10: Tool Settings Persist

**Mục đích:** Verify tool settings được lưu đúng sau rename

**Điều kiện tiên quyết:**
- App đang chạy
- Có 1 tool với settings đặc biệt (loop, timeout, etc.)

**Các bước thực hiện:**
1. Chọn tool
2. Click "Cài đặt Tool"
3. Note lại tất cả settings hiện tại
4. Đóng dialog
5. Click "Sửa Tool"
6. Đổi tên tool
7. Click "Lưu"
8. Click "Cài đặt Tool" lại
9. Verify tất cả settings không đổi

**Kết quả mong đợi:**
- ✅ Tool settings không bị mất sau rename
- ✅ Loop settings đúng
- ✅ Timeout settings đúng
- ✅ User input settings đúng
- ✅ Telegram settings đúng

**Cài đặt cần kiểm tra:**
- Loop enabled: Không đổi
- Loop count: Không đổi
- Stop on timeout: Không đổi
- User input mode: Không đổi
- Notify on timeout: Không đổi

---

## Test Case 11: Multiple Tools - No Conflict

**Mục đích:** Verify nhiều tools không conflict với nhau

**Điều kiện tiên quyết:**
- App đang chạy
- Có ít nhất 3 tools

**Các bước thực hiện:**
1. Tạo 3 tools: "Tool A", "Tool B", "Tool C"
2. Mỗi tool có teaching images riêng
3. Rename "Tool A" → "Tool A2"
4. Rename "Tool B" → "Tool B2"
5. Verify tất cả tools vẫn hoạt động
6. Verify teaching images không bị lẫn lộn

**Kết quả mong đợi:**
- ✅ Tất cả tools có UUID unique
- ✅ Rename không ảnh hưởng tools khác
- ✅ Teaching images của mỗi tool độc lập
- ✅ Không có conflict

**Cài đặt cần kiểm tra:**
- Tool IDs: Tất cả unique
- Tool names: Đúng sau rename
- Teaching images: Không lẫn lộn

---

## Test Case 12: Rollback Migration

**Mục đích:** Verify có thể rollback nếu migration lỗi

**Điều kiện tiên quyết:**
- Đã chạy migration script
- Có backup folders

**Các bước thực hiện:**
1. Stop app
2. Delete `tools/` và `images/`
3. Copy `tools_backup/` → `tools/`
4. Copy `images_backup/` → `images/`
5. Git revert code changes
6. Khởi động app với code cũ
7. Verify app hoạt động bình thường với tools cũ

**Kết quả mong đợi:**
- ✅ Rollback thành công
- ✅ App load được tools cũ
- ✅ Không mất data

**Cài đặt cần kiểm tra:**
- N/A (rollback test)

---

## Summary Checklist

Sau khi hoàn thành tất cả test cases, verify:

- [ ] Migration script chạy thành công
- [ ] Tất cả tools có UUID
- [ ] Rename tool không tạo duplicate
- [ ] Không cho phép trùng tên
- [ ] Teaching images dùng tool ID
- [ ] Tool settings persist sau rename
- [ ] Tools chạy bình thường sau migration
- [ ] Có thể rollback nếu cần

**Nếu tất cả pass → Feature hoàn thành! ✅**
