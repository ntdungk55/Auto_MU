# Manual Test Plan: Input Blocking

## Mục đích
Test feature khóa input (chuột + bàn phím) khi thực hiện action để tránh user vô tình làm gián đoạn automation.

---

## Test Case 1: Checkbox và Spinbox trong Tool Settings

**Mục đích:** Verify UI controls hiển thị đúng và lưu settings

**Điều kiện tiên quyết:**
- Đã có ít nhất 1 tool trong hệ thống
- Tool có ít nhất 1 action

**Các bước thực hiện:**
1. Mở Tool Editor
2. Click vào tool bất kỳ
3. Click nút "Tool Settings" (hoặc menu Tool → Settings)
4. Quan sát dialog Tool Settings

**Kết quả mong đợi:**
- ✅ Hiển thị checkbox "Khóa input khi thực hiện action"
- ✅ Hiển thị spinbox "Thời gian khóa tối đa" với suffix " giây"
- ✅ Spinbox có giá trị mặc định 3.0
- ✅ Spinbox có range 0.1 - 10.0 (test bằng cách nhập giá trị)
- ✅ Checkbox mặc định unchecked (nếu tool mới)

**Cài đặt cần kiểm tra:**
- Checkbox: unchecked
- Spinbox: 3.0 giây

---

## Test Case 2: Warning Message khi Enable

**Mục đích:** Verify warning message hiển thị khi checkbox được check

**Điều kiện tiên quyết:**
- Đang mở Tool Settings Dialog

**Các bước thực hiện:**
1. Check vào checkbox "Khóa input khi thực hiện action"
2. Quan sát dialog

**Kết quả mong đợi:**
- ✅ Hiển thị thông báo: "Ấn F12 để dừng hoàn toàn"
- ✅ Thông báo có màu sắc nổi bật (warning color)

**Các bước tiếp theo:**
1. Uncheck checkbox
2. Quan sát dialog

**Kết quả mong đợi:**
- ✅ Thông báo biến mất

---

## Test Case 3: Data Persistence

**Mục đích:** Verify settings được lưu và load đúng

**Điều kiện tiên quyết:**
- Đang mở Tool Settings Dialog

**Các bước thực hiện:**
1. Check checkbox "Khóa input khi thực hiện action"
2. Đổi spinbox thành 5.0 giây
3. Click OK để đóng dialog
4. Đóng Tool Editor
5. Mở lại Tool Editor
6. Mở lại tool đó
7. Mở lại Tool Settings

**Kết quả mong đợi:**
- ✅ Checkbox vẫn checked
- ✅ Spinbox vẫn là 5.0 giây
- ✅ Warning message vẫn hiển thị

**Cài đặt cần kiểm tra:**
- Checkbox: checked
- Spinbox: 5.0 giây

---

## Test Case 4: Spinbox Range Validation

**Mục đích:** Verify spinbox clamp giá trị đúng

**Điều kiện tiên quyết:**
- Đang mở Tool Settings Dialog

**Các bước thực hiện:**
1. Thử nhập giá trị 0.05 vào spinbox
2. Click ra ngoài hoặc nhấn Enter
3. Quan sát giá trị

**Kết quả mong đợi:**
- ✅ Giá trị tự động clamp thành 0.1

**Các bước tiếp theo:**
1. Thử nhập giá trị 15.0 vào spinbox
2. Click ra ngoài hoặc nhấn Enter
3. Quan sát giá trị

**Kết quả mong đợi:**
- ✅ Giá trị tự động clamp thành 10.0

**Cài đặt cần kiểm tra:**
- Spinbox min: 0.1
- Spinbox max: 10.0

---

## Test Case 5: Block Input khi KEYBOARD Action

**Mục đích:** Verify input bị khóa khi thực hiện KEYBOARD action

**Điều kiện tiên quyết:**
- Tool có 1 KEYBOARD action (ví dụ: gõ "test")
- Tool Settings: block_input_enabled = True, block_input_duration = 3.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Ngay khi action bắt đầu, thử di chuột và ấn phím bất kỳ
3. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔒 Đã khóa input (3.0 giây)"
- ✅ Chuột và bàn phím KHÔNG phản hồi trong thời gian action chạy
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau khi action xong
- ✅ Sau khi unlock, chuột và bàn phím hoạt động bình thường

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 3.0 giây

---

## Test Case 6: Block Input khi MOUSE_CLICK Action

**Mục đích:** Verify input bị khóa khi thực hiện MOUSE_CLICK action

**Điều kiện tiên quyết:**
- Tool có 1 MOUSE_CLICK action (click vào hình ảnh)
- Tool Settings: block_input_enabled = True, block_input_duration = 3.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Ngay khi action bắt đầu, thử di chuột và ấn phím bất kỳ
3. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔒 Đã khóa input (3.0 giây)"
- ✅ Chuột và bàn phím KHÔNG phản hồi trong thời gian action chạy
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau khi action xong
- ✅ Sau khi unlock, chuột và bàn phím hoạt động bình thường

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 3.0 giây

---

## Test Case 7: Block Input khi IMAGE_DETECT Action

**Mục đích:** Verify input bị khóa khi thực hiện IMAGE_DETECT action

**Điều kiện tiên quyết:**
- Tool có 1 IMAGE_DETECT action (timeout 30s)
- Tool Settings: block_input_enabled = True, block_input_duration = 3.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Ngay khi action bắt đầu, thử di chuột và ấn phím bất kỳ
3. Đợi 3 giây
4. Thử lại di chuột và ấn phím
5. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔒 Đã khóa input (3.0 giây)"
- ✅ Trong 3 giây đầu: chuột và bàn phím KHÔNG phản hồi
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau 3 giây
- ✅ Sau 3 giây: chuột và bàn phím hoạt động bình thường (action vẫn chạy đến hết timeout 30s)

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 3.0 giây
- Action timeout: 30.0 giây

---

## Test Case 8: Không Block khi Disabled

**Mục đích:** Verify input KHÔNG bị khóa khi checkbox unchecked

**Điều kiện tiên quyết:**
- Tool có 1 action bất kỳ
- Tool Settings: block_input_enabled = False

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Ngay khi action bắt đầu, thử di chuột và ấn phím bất kỳ
3. Quan sát log

**Kết quả mong đợi:**
- ✅ Log KHÔNG hiển thị "🔒 Đã khóa input"
- ✅ Chuột và bàn phím hoạt động bình thường
- ✅ Action vẫn chạy đúng

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = False

---

## Test Case 9: Emergency Hotkey F12

**Mục đích:** Verify hotkey dừng tool và unlock input

**Điều kiện tiên quyết:**
- Tool có 1 IMAGE_DETECT action (timeout 30s)
- Tool Settings: block_input_enabled = True, block_input_duration = 10.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Đợi action bắt đầu (log hiển thị "🔒 Đã khóa input")
3. Ấn phím F12
4. Quan sát log và trạng thái tool

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔓 Đã mở khóa input" ngay lập tức
- ✅ Log hiển thị "⚠️ Emergency stop: Đã dừng tool do hotkey"
- ✅ Tool dừng hoàn toàn (STOP COMPLETELY, không phải pause)
- ✅ Chuột và bàn phím hoạt động bình thường
- ✅ Status panel hiển thị tool đã dừng

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 10.0 giây

---

## Test Case 10: Không Block trong Delay

**Mục đích:** Verify input KHÔNG bị khóa trong thời gian delay

**Điều kiện tiên quyết:**
- Tool có 1 KEYBOARD action với delay = 5.0 giây
- Tool Settings: block_input_enabled = True, block_input_duration = 3.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Đợi action thực hiện xong (log hiển thị "✓ Thành công")
3. Quan sát log hiển thị "🔓 Đã mở khóa input"
4. Trong thời gian delay 5 giây, thử di chuột và ấn phím
5. Quan sát

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔒 Đã khóa input" khi action bắt đầu
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau khi action xong (trước delay)
- ✅ Trong thời gian delay: chuột và bàn phím hoạt động bình thường
- ✅ Log KHÔNG hiển thị "🔒 Đã khóa input" lần nữa trong delay

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 3.0 giây
- Action delay: 5.0 giây

---

## Test Case 11: Không Block trong Loop Pre/Post Delay

**Mục đích:** Verify input KHÔNG bị khóa trong loop_pre_delay và loop_post_delay

**Điều kiện tiên quyết:**
- Tool có 1 action bất kỳ
- Tool Settings: loop_enabled = True, loop_pre_delay = 30 (3s), loop_post_delay = 30 (3s)
- Tool Settings: block_input_enabled = True, block_input_duration = 3.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Quan sát log trong thời gian loop_pre_delay (3s đầu)
3. Thử di chuột và ấn phím trong thời gian này
4. Đợi action chạy xong
5. Quan sát log trong thời gian loop_post_delay (3s cuối)
6. Thử di chuột và ấn phím trong thời gian này

**Kết quả mong đợi:**
- ✅ Trong loop_pre_delay: chuột và bàn phím hoạt động bình thường
- ✅ Log KHÔNG hiển thị "🔒 Đã khóa input" trong loop_pre_delay
- ✅ Log hiển thị "🔒 Đã khóa input" khi action bắt đầu
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau khi action xong
- ✅ Trong loop_post_delay: chuột và bàn phím hoạt động bình thường
- ✅ Log KHÔNG hiển thị "🔒 Đã khóa input" trong loop_post_delay

**Cài đặt cần kiểm tra:**
- Tool Settings: loop_enabled = True
- Tool Settings: loop_pre_delay = 30 (3 giây)
- Tool Settings: loop_post_delay = 30 (3 giây)
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 3.0 giây

---

## Test Case 12: Block Duration Shorter than Action

**Mục đích:** Verify unlock sau block_input_duration nếu action chạy lâu hơn

**Điều kiện tiên quyết:**
- Tool có 1 IMAGE_DETECT action (timeout 30s)
- Tool Settings: block_input_enabled = True, block_input_duration = 2.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Đợi 2 giây
3. Thử di chuột và ấn phím
4. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔒 Đã khóa input (2.0 giây)"
- ✅ Trong 2 giây đầu: chuột và bàn phím KHÔNG phản hồi
- ✅ Log hiển thị "🔓 Đã mở khóa input" sau 2 giây
- ✅ Sau 2 giây: chuột và bàn phím hoạt động bình thường
- ✅ Action vẫn tiếp tục chạy đến hết timeout 30s

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 2.0 giây
- Action timeout: 30.0 giây

---

## Test Case 13: Error Handling - BlockInput() Fails

**Mục đích:** Verify tool không crash khi BlockInput() API fail

**Điều kiện tiên quyết:**
- Tool có 1 action bất kỳ
- Tool Settings: block_input_enabled = True
- **Chạy app KHÔNG với quyền admin** (để BlockInput() có thể fail)

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Quan sát log

**Kết quả mong đợi:**
- ✅ Log có thể hiển thị "⚠️ Không thể khóa input (cần quyền admin?)"
- ✅ Tool KHÔNG crash
- ✅ Action vẫn chạy bình thường
- ✅ Chuột và bàn phím vẫn hoạt động (vì BlockInput() fail)

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Chạy app không với quyền admin

---

## Test Case 14: Multiple Actions in Tool

**Mục đích:** Verify block/unlock đúng cho từng action

**Điều kiện tiên quyết:**
- Tool có 3 actions:
  1. KEYBOARD action (delay 1s)
  2. MOUSE_CLICK action (delay 1s)
  3. IMAGE_DETECT action (timeout 5s)
- Tool Settings: block_input_enabled = True, block_input_duration = 2.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Quan sát log cho từng action
3. Thử di chuột và ấn phím trong từng giai đoạn

**Kết quả mong đợi:**
- ✅ Action 1: Log "🔒 Đã khóa input" → action chạy → Log "🔓 Đã mở khóa input" → delay 1s (không khóa)
- ✅ Action 2: Log "🔒 Đã khóa input" → action chạy → Log "🔓 Đã mở khóa input" → delay 1s (không khóa)
- ✅ Action 3: Log "🔒 Đã khóa input" → sau 2s → Log "🔓 Đã mở khóa input" → action tiếp tục chạy đến hết 5s
- ✅ Mỗi action có 1 cặp lock/unlock riêng
- ✅ Không bị khóa trong delay giữa các action

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 2.0 giây

---

## Test Case 15: Tool Stop/Pause Unlocks Input

**Mục đích:** Verify input được unlock khi tool dừng hoặc pause

**Điều kiện tiên quyết:**
- Tool có 1 IMAGE_DETECT action (timeout 30s)
- Tool Settings: block_input_enabled = True, block_input_duration = 10.0

**Các bước thực hiện:**
1. Chạy tool (F4)
2. Đợi action bắt đầu (log hiển thị "🔒 Đã khóa input")
3. Ấn F6 để pause tool
4. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔓 Đã mở khóa input" ngay khi pause
- ✅ Chuột và bàn phím hoạt động bình thường
- ✅ Tool ở trạng thái pause

**Các bước tiếp theo:**
1. Chạy lại tool (F4)
2. Đợi action bắt đầu (log hiển thị "🔒 Đã khóa input")
3. Ấn F7 để stop completely
4. Quan sát log

**Kết quả mong đợi:**
- ✅ Log hiển thị "🔓 Đã mở khóa input" ngay khi stop
- ✅ Chuột và bàn phím hoạt động bình thường
- ✅ Tool ở trạng thái stopped

**Cài đặt cần kiểm tra:**
- Tool Settings: block_input_enabled = True
- Tool Settings: block_input_duration = 10.0 giây

---

## Test Case 16: Persistence After Restart App

**Mục đích:** Verify settings persist sau khi restart app

**Điều kiện tiên quyết:**
- Tool có settings: block_input_enabled = True, block_input_duration = 7.5

**Các bước thực hiện:**
1. Đóng app hoàn toàn
2. Mở lại app
3. Mở Tool Editor
4. Mở tool đã config
5. Mở Tool Settings

**Kết quả mong đợi:**
- ✅ Checkbox "Khóa input khi thực hiện action" vẫn checked
- ✅ Spinbox vẫn là 7.5 giây
- ✅ Warning message vẫn hiển thị

**Cài đặt cần kiểm tra:**
- Checkbox: checked
- Spinbox: 7.5 giây

---

## Ghi chú

### Về Emergency Hotkey
- Hotkey F12 được chọn vì:
  - Dễ ấn (1 phím duy nhất)
  - Ít conflict với hotkey khác
  - Có thể ấn bằng 1 tay

### Về BlockInput() API
- Cần quyền admin để hoạt động đúng
- Nếu không có quyền admin, API có thể fail nhưng tool vẫn chạy bình thường
- BlockInput() chỉ block input từ user, KHÔNG block input từ automation

### Về Testing
- Test trên Windows 10/11
- Test với nhiều loại action khác nhau
- Test với nhiều giá trị block_input_duration khác nhau
- Test emergency hotkey trong nhiều tình huống

### Về Safety
- LUÔN có cách thoát khẩn cấp (F12)
- LUÔN unlock input trong finally block
- LUÔN unlock input khi tool stop/pause/crash
