# Manual Test Plan: Telegram Timeout Notification

## Test Case 1: Checkbox hiển thị trong Tool Settings

**Mục đích:** Verify checkbox "Thông báo Telegram khi timeout" hiển thị đúng

**Điều kiện tiên quyết:**
- App đang chạy
- Có ít nhất 1 tool đã tạo

**Các bước thực hiện:**
1. Click vào tool trong danh sách
2. Click button "Tool Settings"
3. Quan sát dialog Tool Settings

**Kết quả mong đợi:**
- Dialog Tool Settings mở ra
- Có checkbox "Thông báo Telegram khi timeout" hiển thị
- Checkbox mặc định là unchecked

---

## Test Case 2: Check checkbox khi Telegram chưa config

**Mục đích:** Verify message box hiển thị khi Telegram chưa được cấu hình

**Điều kiện tiên quyết:**
- App đang chạy
- Telegram chưa được cấu hình (không có bot_token hoặc chat_id)
- Tool Settings Dialog đang mở

**Các bước thực hiện:**
1. Click vào checkbox "Thông báo Telegram khi timeout"
2. Quan sát message box

**Kết quả mong đợi:**
- Message box hiển thị với nội dung: "Telegram chưa được cấu hình. Bạn có muốn mở cài đặt Telegram không?"
- Message box có 2 buttons: "Có" và "Không"

**Cài đặt cần kiểm tra:**
- `telegram_bot_token_dpapi_b64`: không tồn tại hoặc rỗng trong app_state.json
- `telegram_chat_id`: không tồn tại hoặc rỗng trong app_state.json

---

## Test Case 3: Chọn "Có" trong message box

**Mục đích:** Verify TelegramConfigDialog mở khi user chọn "Có"

**Điều kiện tiên quyết:**
- Đang ở Test Case 2
- Message box đang hiển thị

**Các bước thực hiện:**
1. Click button "Có" trong message box
2. Quan sát dialog mở ra

**Kết quả mong đợi:**
- TelegramConfigDialog mở ra
- Checkbox "Thông báo Telegram khi timeout" vẫn unchecked
- Tool Settings Dialog vẫn mở phía sau

---

## Test Case 4: Chọn "Không" trong message box

**Mục đích:** Verify checkbox không được check khi user chọn "Không"

**Điều kiện tiên quyết:**
- Đang ở Test Case 2
- Message box đang hiển thị

**Các bước thực hiện:**
1. Click button "Không" trong message box
2. Quan sát checkbox

**Kết quả mong đợi:**
- Message box đóng
- Checkbox "Thông báo Telegram khi timeout" vẫn unchecked
- Tool Settings Dialog vẫn mở

---

## Test Case 5: Check checkbox khi Telegram đã config

**Mục đích:** Verify checkbox có thể check khi Telegram đã được cấu hình

**Điều kiện tiên quyết:**
- App đang chạy
- Telegram đã được cấu hình (có bot_token và chat_id)
- Tool Settings Dialog đang mở

**Các bước thực hiện:**
1. Click vào checkbox "Thông báo Telegram khi timeout"
2. Quan sát checkbox

**Kết quả mong đợi:**
- Checkbox được check
- Không có message box hiển thị
- Setting được lưu ngay lập tức

**Cài đặt cần kiểm tra:**
- `telegram_bot_token_dpapi_b64`: có giá trị trong app_state.json
- `telegram_chat_id`: có giá trị trong app_state.json
- `notify_on_timeout`: True trong tool JSON file

---

## Test Case 6: Uncheck checkbox

**Mục đích:** Verify checkbox có thể uncheck và setting được lưu

**Điều kiện tiên quyết:**
- Đang ở Test Case 5
- Checkbox đang checked

**Các bước thực hiện:**
1. Click vào checkbox "Thông báo Telegram khi timeout" để uncheck
2. Click "OK" để đóng dialog
3. Mở lại Tool Settings Dialog
4. Quan sát checkbox

**Kết quả mong đợi:**
- Checkbox được uncheck
- Setting được lưu
- Khi mở lại dialog, checkbox vẫn unchecked

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: False trong tool JSON file

---

## Test Case 7: Persistence sau khi restart app

**Mục đích:** Verify setting persist sau khi restart app

**Điều kiện tiên quyết:**
- Đã hoàn thành Test Case 5
- Checkbox đang checked và đã lưu

**Các bước thực hiện:**
1. Đóng app
2. Mở lại app
3. Mở Tool Settings Dialog
4. Quan sát checkbox

**Kết quả mong đợi:**
- Checkbox vẫn checked
- Setting được restore đúng

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: True trong tool JSON file

---

## Test Case 8: Gửi notification khi timeout stop completely

**Mục đích:** Verify notification được gửi khi tool timeout và stop completely

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = True
- Tool có action sẽ timeout (ví dụ: IMAGE_DETECT với hình ảnh không tồn tại)
- Tool KHÔNG có `continue_on_timeout`, `timeout_goto_enabled`, hoặc `restart_on_timeout`

**Các bước thực hiện:**
1. Chạy tool
2. Đợi action timeout
3. Quan sát log và Telegram

**Kết quả mong đợi:**
- Tool dừng hoàn toàn (stop completely)
- Log hiển thị: "Tool đã dừng hoàn toàn do TIMEOUT."
- Telegram notification được gửi với nội dung:
  - Tool name
  - Action name bị timeout
- Format rõ ràng, dễ đọc

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: True
- `continue_on_timeout`: False (hoặc không có)
- `timeout_goto_enabled`: False (hoặc không có)
- `restart_on_timeout`: False

---

## Test Case 9: Không gửi notification khi notify_on_timeout = False

**Mục đích:** Verify notification KHÔNG được gửi khi setting tắt

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = False
- Tool có action sẽ timeout

**Các bước thực hiện:**
1. Chạy tool
2. Đợi action timeout
3. Quan sát log và Telegram

**Kết quả mong đợi:**
- Tool dừng hoàn toàn
- Log hiển thị: "Tool đã dừng hoàn toàn do TIMEOUT."
- Telegram notification KHÔNG được gửi

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: False

---

## Test Case 10: Không gửi notification khi continue_on_timeout

**Mục đích:** Verify notification KHÔNG được gửi khi tool continue

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = True
- Action có `continue_on_timeout` = True

**Các bước thực hiện:**
1. Chạy tool
2. Đợi action timeout
3. Quan sát log và Telegram

**Kết quả mong đợi:**
- Tool bỏ qua step và chạy tiếp
- Log hiển thị: "Timeout → bỏ qua step này và làm tiếp step sau"
- Telegram notification KHÔNG được gửi

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: True
- `continue_on_timeout`: True

---

## Test Case 11: Không gửi notification khi timeout_goto

**Mục đích:** Verify notification KHÔNG được gửi khi tool goto step

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = True
- Action có `timeout_goto_enabled` = True

**Các bước thực hiện:**
1. Chạy tool
2. Đợi action timeout
3. Quan sát log và Telegram

**Kết quả mong đợi:**
- Tool nhảy về step khác
- Log hiển thị: "Timeout → nhảy về Step X"
- Telegram notification KHÔNG được gửi

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: True
- `timeout_goto_enabled`: True

---

## Test Case 12: Không gửi notification khi restart_on_timeout

**Mục đích:** Verify notification KHÔNG được gửi khi tool restart

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = True
- Tool có `restart_on_timeout` = True

**Các bước thực hiện:**
1. Chạy tool
2. Đợi action timeout
3. Quan sát log và Telegram

**Kết quả mong đợi:**
- Tool chạy lại từ đầu
- Log hiển thị: "Timeout → chạy lại từ đầu (reset về step 1)"
- Telegram notification KHÔNG được gửi

**Cài đặt cần kiểm tra:**
- `notify_on_timeout`: True
- `restart_on_timeout`: True

---

## Test Case 13: Deduplication - không gửi duplicate trong 60s

**Mục đích:** Verify deduplication hoạt động đúng

**Điều kiện tiên quyết:**
- Telegram đã được cấu hình
- Tool có `notify_on_timeout` = True
- Tool có action sẽ timeout

**Các bước thực hiện:**
1. Chạy tool lần 1
2. Đợi timeout → notification gửi
3. Chạy lại tool ngay lập tức (trong vòng 60s)
4. Đợi timeout lần 2
5. Quan sát Telegram

**Kết quả mong đợi:**
- Lần 1: Notification được gửi
- Lần 2: Notification KHÔNG được gửi (dedup)
- Log vẫn hiển thị timeout cả 2 lần

---

## Test Case 14: Deduplication - gửi lại sau 60s

**Mục đích:** Verify notification được gửi lại sau 60s

**Điều kiện tiên quyết:**
- Đã hoàn thành Test Case 13
- Đã đợi hơn 60s kể từ lần gửi đầu tiên

**Các bước thực hiện:**
1. Đợi hơn 60s kể từ lần gửi notification đầu tiên
2. Chạy lại tool
3. Đợi timeout
4. Quan sát Telegram

**Kết quả mong đợi:**
- Notification được gửi lại
- Nội dung giống lần đầu

---

## Test Case 15: Error handling - Telegram API fail

**Mục đích:** Verify tool không crash khi Telegram API fail

**Điều kiện tiên quyết:**
- Tool có `notify_on_timeout` = True
- Telegram config sai (ví dụ: bot_token không hợp lệ)

**Các bước thực hiện:**
1. Chạy tool
2. Đợi timeout
3. Quan sát log và app

**Kết quả mong đợi:**
- Tool vẫn dừng hoàn toàn bình thường
- Log hiển thị error về Telegram (nếu có)
- App KHÔNG crash
- Tool vẫn hoạt động bình thường

---

## Summary Checklist

- [ ] Test Case 1: Checkbox hiển thị
- [ ] Test Case 2: Message box khi chưa config
- [ ] Test Case 3: Mở Telegram config
- [ ] Test Case 4: Hủy check
- [ ] Test Case 5: Check khi đã config
- [ ] Test Case 6: Uncheck
- [ ] Test Case 7: Persistence
- [ ] Test Case 8: Gửi notification
- [ ] Test Case 9: Không gửi khi tắt
- [ ] Test Case 10: Không gửi khi continue
- [ ] Test Case 11: Không gửi khi goto
- [ ] Test Case 12: Không gửi khi restart
- [ ] Test Case 13: Deduplication trong 60s
- [ ] Test Case 14: Gửi lại sau 60s
- [ ] Test Case 15: Error handling
