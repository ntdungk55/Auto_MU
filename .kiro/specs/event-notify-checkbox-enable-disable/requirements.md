# Feature: Checkbox Enable/Disable cho Mốc Thời Gian Sự Kiện

## 1. Tổng quan

Thêm checkbox vào từng mốc thời gian trong action "Thông báo sự kiện" để user có thể tạm thời enable/disable các mốc thời gian mà không cần xóa chúng khỏi danh sách. Khi chạy auto, chỉ các mốc được enable (checked) mới được xử lý.

## 2. User Stories

- Là một user sử dụng action "Thông báo sự kiện", tôi muốn có thể tạm thời disable một số mốc thời gian, để tôi không cần xóa và thêm lại chúng khi muốn sử dụng.
- Là một user, tôi muốn thấy rõ ràng mốc nào đang enabled/disabled trong UI, để tôi biết mốc nào sẽ được chạy khi auto.
- Là một user, tôi muốn các mốc disabled được hiển thị mờ đi, để tôi dễ phân biệt với các mốc đang active.

## 3. Acceptance Criteria

### 3.1 UI Checkbox
1. WHEN user mở dialog cài đặt "Thông báo sự kiện" THEN mỗi mốc thời gian SHALL có một checkbox ở bên trái QTimeEdit
2. WHEN user thêm mốc thời gian mới THEN checkbox SHALL được checked (enabled) mặc định
3. WHEN user click checkbox THEN trạng thái enable/disable của mốc thời gian SHALL được toggle

### 3.2 Visual Feedback
1. WHEN checkbox được unchecked (disabled) THEN QTimeEdit SHALL được gray out (setEnabled(False))
2. WHEN checkbox được checked (enabled) THEN QTimeEdit SHALL hiển thị bình thường (setEnabled(True))
3. WHEN user thay đổi trạng thái checkbox THEN UI SHALL cập nhật visual feedback ngay lập tức

### 3.3 Data Persistence
1. WHEN user save settings THEN trạng thái enabled/disabled của từng mốc SHALL được lưu vào JSON
2. WHEN user mở lại dialog THEN trạng thái checkbox SHALL được restore đúng như lúc save
3. WHEN user save → close app → reopen THEN trạng thái checkbox SHALL được giữ nguyên

### 3.4 Backward Compatibility
1. WHEN load tool JSON cũ (format string array) THEN tất cả mốc thời gian SHALL được convert thành enabled mặc định
2. WHEN load tool JSON mới (format dict array) THEN trạng thái enabled SHALL được đọc từ field "enabled"
3. WHEN convert format cũ sang mới THEN không được mất dữ liệu thời gian

### 3.5 Runtime Behavior
1. WHEN chạy auto action "Thông báo sự kiện" THEN chỉ các mốc có enabled=true SHALL được xử lý
2. WHEN tất cả mốc đều disabled THEN action SHALL trả về timeout hoặc skip
3. WHEN có ít nhất 1 mốc enabled THEN action SHALL hoạt động bình thường với các mốc enabled

## 4. Input/Output

**Input:**
- Danh sách mốc thời gian hiện tại (format cũ hoặc mới)
- User interaction: click checkbox, thay đổi thời gian

**Output:**
- UI: Checkbox + QTimeEdit với visual feedback
- Data: JSON format mới `[{"time": "10:58", "enabled": true}, ...]`
- Runtime: Chỉ xử lý các mốc enabled=true

## 5. Sơ đồ khối (Text-based)

```
┌─────────────────────────────────────────┐
│           UI Dialog                     │
│  ┌─────────────────────────────────┐    │
│  │ ☑️ [10:58] 🗑️ Xóa              │    │
│  │ ☐ [09:10] 🗑️ Xóa (grayed out) │    │
│  │ ☑️ [11:10] 🗑️ Xóa              │    │
│  └─────────────────────────────────┘    │
│           ↓ Save                        │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         JSON Storage                    │
│ "event_notify_times": [                 │
│   {"time": "10:58", "enabled": true},   │
│   {"time": "09:10", "enabled": false},  │
│   {"time": "11:10", "enabled": true}    │
│ ]                                       │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│        Runtime Processing               │
│ Only process enabled times:             │
│ - 10:58 ✅ (enabled)                   │
│ - 09:10 ❌ (disabled, skip)            │
│ - 11:10 ✅ (enabled)                   │
└─────────────────────────────────────────┘
```

## 6. Technical Notes

### Data Format Migration
- **Format cũ:** `"event_notify_times": ["10:58", "09:10", "11:10"]`
- **Format mới:** `"event_notify_times": [{"time": "10:58", "enabled": true}, ...]`
- Migration: Detect type của first item, nếu là string thì convert tất cả thành dict với enabled=true

### UI Layout Changes
- Thêm QCheckBox vào layout của mỗi item trong QListWidget
- Layout: `[QCheckBox] [QTimeEdit] [QPushButton "🗑️ Xóa"]`
- Connect signal: `QCheckBox.stateChanged` → update QTimeEdit.setEnabled()

### Persistence Requirements (5 bước bắt buộc)
1. ✅ Add QCheckBox to UI dialog
2. ✅ Save checkbox state in `get_settings()` method
3. ✅ Load checkbox state in `_load_settings()` method  
4. ✅ Verify field exists in `_action_to_dict()` in `tool_manager.py`
5. ✅ Verify field exists in `from_dict()` in `tool_manager.py`

### Runtime Logic
- Trong SystemExecutor, filter `event_notify_times` để chỉ lấy items có `enabled: true`
- Nếu không có mốc nào enabled, action có thể return timeout ngay lập tức