# Manual Test Plan: Event Notify Checkbox Enable/Disable

## Test Case 1: UI Checkbox Display và Interaction

**Mục đích:** Verify checkbox hiển thị đúng vị trí và hoạt động đúng

**Điều kiện tiên quyết:**
- App đã được build và chạy
- Có tool với action "Thông báo sự kiện" đã có sẵn mốc thời gian

**Các bước thực hiện:**
1. Mở tool editor
2. Click vào action "Thông báo sự kiện" 
3. Click nút "Cài đặt" để mở dialog
4. Quan sát UI của các mốc thời gian hiện có
5. Click nút "➕ Thêm mốc" để thêm mốc mới
6. Quan sát UI của mốc mới được thêm

**Kết quả mong đợi:**
- Mỗi mốc thời gian có checkbox ở bên trái QTimeEdit
- Layout: `[☑️] [HH:MM] [🗑️ Xóa]`
- Mốc mới được thêm có checkbox checked mặc định
- Các mốc cũ (từ format cũ) có checkbox checked mặc định

**Cài đặt cần kiểm tra:**
- Checkbox position: Trước QTimeEdit
- Default state: Checked (enabled)

---

## Test Case 2: Visual Feedback khi Toggle Checkbox

**Mục đích:** Verify gray out effect khi disable checkbox

**Điều kiện tiên quyết:**
- Dialog "Thông báo sự kiện" đang mở
- Có ít nhất 2 mốc thời gian

**Các bước thực hiện:**
1. Quan sát trạng thái ban đầu của QTimeEdit (enabled, màu bình thường)
2. Click để uncheck checkbox của mốc thời gian đầu tiên
3. Quan sát thay đổi visual của QTimeEdit
4. Click để check lại checkbox
5. Quan sát thay đổi visual của QTimeEdit
6. Thử thay đổi thời gian trong QTimeEdit khi checkbox unchecked
7. Thử thay đổi thời gian trong QTimeEdit khi checkbox checked

**Kết quả mong đợi:**
- Khi checkbox unchecked: QTimeEdit bị gray out (màu xám, disabled)
- Khi checkbox checked: QTimeEdit hiển thị bình thường (enabled)
- Khi disabled: Không thể edit thời gian trong QTimeEdit
- Khi enabled: Có thể edit thời gian bình thường
- Thay đổi visual xảy ra ngay lập tức (real-time)

**Cài đặt cần kiểm tra:**
- Visual feedback: Gray out effect
- Interaction: Enable/disable editing

---

## Test Case 3: Data Persistence - Save và Load

**Mục đích:** Verify trạng thái checkbox được save và load đúng

**Điều kiện tiên quyết:**
- Dialog "Thông báo sự kiện" đang mở
- Có ít nhất 3 mốc thời gian

**Các bước thực hiện:**
1. Set trạng thái checkbox như sau:
   - Mốc 1: Checked (enabled)
   - Mốc 2: Unchecked (disabled) 
   - Mốc 3: Checked (enabled)
2. Click "Lưu" để save settings
3. Đóng dialog
4. Mở lại dialog "Thông báo sự kiện"
5. Kiểm tra trạng thái checkbox của từng mốc
6. Kiểm tra visual state của QTimeEdit tương ứng

**Kết quả mong đợi:**
- Trạng thái checkbox được restore đúng như lúc save
- Visual feedback (gray out) được áp dụng đúng
- Thời gian trong QTimeEdit không bị thay đổi

**Cài đặt cần kiểm tra:**
- Checkbox states: Đúng như lúc save
- Time values: Không bị mất
- Visual feedback: Consistent với checkbox state

---

## Test Case 4: Backward Compatibility với Tool JSON Cũ

**Mục đích:** Verify tool cũ (format string) được convert đúng

**Điều kiện tiên quyết:**
- Có file tool JSON với format cũ:
```json
"event_notify_times": ["10:58", "09:10", "11:10"]
```

**Các bước thực hiện:**
1. Load tool có format cũ
2. Mở action "Thông báo sự kiện"
3. Click "Cài đặt" để mở dialog
4. Kiểm tra trạng thái checkbox của tất cả mốc
5. Kiểm tra thời gian hiển thị có đúng không
6. Save settings
7. Đóng app
8. Mở lại app và load tool
9. Kiểm tra format JSON trong file tool

**Kết quả mong đợi:**
- Tất cả mốc từ format cũ có checkbox checked (enabled=true)
- Thời gian hiển thị đúng (10:58, 09:10, 11:10)
- Sau khi save, format JSON chuyển thành:
```json
"event_notify_times": [
  {"time": "10:58", "enabled": true},
  {"time": "09:10", "enabled": true}, 
  {"time": "11:10", "enabled": true}
]
```

**Cài đặt cần kiểm tra:**
- Migration: String array → Dict array
- Default enabled: true cho tất cả mốc cũ
- Data integrity: Không mất thời gian

---

## Test Case 5: Runtime Behavior - Chỉ Xử Lý Mốc Enabled

**Mục đích:** Verify khi chạy auto chỉ xử lý mốc enabled

**Điều kiện tiên quyết:**
- Tool có action "Thông báo sự kiện" với mixed enabled/disabled times
- Thời gian hiện tại gần với một mốc disabled và một mốc enabled

**Các bước thực hiện:**
1. Cài đặt mốc thời gian như sau:
   - 14:30 - Disabled (unchecked)
   - 14:32 - Enabled (checked)
   - 14:35 - Disabled (unchecked)
2. Save settings
3. Chạy tool vào lúc 14:29 (trước mốc đầu tiên)
4. Quan sát log và behavior của action
5. Đợi đến 14:31 (sau mốc disabled, trước mốc enabled)
6. Quan sát behavior
7. Đợi đến 14:33 (sau mốc enabled)
8. Quan sát behavior

**Kết quả mong đợi:**
- Lúc 14:30: Action không trigger (mốc disabled)
- Lúc 14:32: Action trigger bình thường (mốc enabled)
- Lúc 14:35: Action không trigger (mốc disabled)
- Log hiển thị chỉ xử lý mốc enabled
- Mốc disabled bị skip hoàn toàn

**Cài đặt cần kiểm tra:**
- Runtime filtering: Chỉ process enabled=true
- Logging: Clear indication về mốc nào được xử lý
- Behavior: Consistent với checkbox state

---

## Test Case 6: Edge Case - Tất Cả Mốc Disabled

**Mục đích:** Verify behavior khi tất cả mốc đều disabled

**Điều kiện tiên quyết:**
- Tool có action "Thông báo sự kiện" với ít nhất 2 mốc thời gian

**Các bước thực hiện:**
1. Mở dialog "Thông báo sự kiện"
2. Uncheck tất cả checkbox (disable tất cả mốc)
3. Thử click "Lưu"
4. Nếu được phép save, chạy tool
5. Quan sát behavior của action

**Kết quả mong đợi:**
- Option A: Dialog hiển thị warning "Phải có ít nhất 1 mốc enabled" và không cho save
- Option B: Cho phép save, nhưng khi chạy action sẽ timeout/skip ngay lập tức
- Behavior phải consistent và predictable

**Cài đặt cần kiểm tra:**
- Validation: Có warning hay không
- Runtime behavior: Timeout/skip logic
- User experience: Clear feedback

---

## Test Case 7: Data Persistence - App Restart

**Mục đích:** Verify data persistence qua app restart (Critical test!)

**Điều kiện tiên quyết:**
- Tool đã được save với mixed checkbox states

**Các bước thực hiện:**
1. Cài đặt checkbox states:
   - Mốc 1: Enabled
   - Mốc 2: Disabled
   - Mốc 3: Enabled
2. Save tool
3. Đóng hoàn toàn app
4. Mở lại app
5. Load tool
6. Mở dialog "Thông báo sự kiện"
7. Kiểm tra checkbox states
8. Kiểm tra visual feedback (gray out)

**Kết quả mong đợi:**
- Checkbox states được restore chính xác
- Visual feedback (gray out) được áp dụng đúng
- Không có data loss
- Tool JSON file chứa đúng format mới

**Cài đặt cần kiểm tra:**
- Persistence: Checkbox states qua app restart
- JSON format: Dict array với enabled field
- Visual consistency: Gray out effect

---

## Tóm Tắt Test Cases

| Test Case | Focus | Priority |
|-----------|-------|----------|
| 1 | UI Display | High |
| 2 | Visual Feedback | High |
| 3 | Save/Load | Critical |
| 4 | Backward Compatibility | High |
| 5 | Runtime Behavior | Critical |
| 6 | Edge Case | Medium |
| 7 | App Restart Persistence | Critical |

**Lưu ý:** Test Cases 3, 5, 7 là CRITICAL vì liên quan đến data persistence và runtime behavior - core functionality của feature.