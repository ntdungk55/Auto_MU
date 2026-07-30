# Requirements: Special Event Tracking Mode

---

## 1. SPEC (Đặc tả)

**Vấn đề:**
Hệ thống hiện tại có mode `event_tracking` trong READ_PASSIVE action, nhưng chỉ hỗ trợ một loại event cố định. Khi muốn thêm event mới, cần sửa code trực tiếp. Người dùng không thể bật/tắt từng event riêng lẻ, và mỗi event có settings riêng biệt cần được quản lý độc lập.

**Mục tiêu:**
Thêm mode mới `special_event_tracking` vào READ_PASSIVE action, cho phép người dùng chọn và cấu hình từng special event qua danh sách checkbox có thể mở rộng (collapsible). Mỗi event được bật/tắt độc lập, có settings riêng, và giải phóng subscription khỏi ScreenScanService khi bị tắt. Mode `event_tracking` cũ được giữ nguyên, không bị ảnh hưởng.

**Danh sách Special Events:**

| Event                    | File Requirements                                                                              | Trạng thái |
|--------------------------|------------------------------------------------------------------------------------------------|------------|
| Imperial Guardian        | `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`                       | Active     |
| Monster Invasion         | `.kiro/specs/special-event-tracking/monster-invasion-event-tracker.md`                        | Active     |
| ↳ Golden Invasion        | `.kiro/specs/special-event-tracking/golden-invasion-event-tracker.md`                         | Active     |
| ↳ White Wizard + Red Dragon | `.kiro/specs/special-event-tracking/white-wizard-red-dragon-event-tracker.md`              | Active     |

> Mỗi event mới thêm vào phải có file requirements riêng và được đăng ký vào bảng trên.

**Input/Output (framework):**

| Loại   | Mô tả                                                        | Ví dụ                                                       |
|--------|--------------------------------------------------------------|-------------------------------------------------------------|
| Input  | Người dùng tick checkbox event trong dialog                  | Tick "☑ Imperial Guardian" → expand section settings       |
| Input  | Người dùng untick checkbox event                             | Untick → collapse section, dừng tracking                   |
| Input  | Người dùng nhấn Lưu                                          | Lưu trạng thái enabled/disabled và settings của từng event |
| Output | ScreenScanService subscription được tạo/hủy theo trạng thái | Subscribe khi enable, unsubscribe khi disable               |
| Output | Settings được persist vào JSON                               | `{event_id}_enabled`, `{event_id}_*` settings              |

**Parameters (framework):**

| Tham số                           | Kiểu  | Mô tả                                                              | Giá trị mặc định |
|-----------------------------------|-------|--------------------------------------------------------------------|------------------|
| `{event_id}_enabled`              | bool  | Bật/tắt theo dõi event                                             | false            |
| `{event_id}_no_player_alert_delay`| int   | Số phút sau khi OPEN mà không có người → gửi cảnh báo              | 10               |
| `{event_id}_teaching_corner_x1`   | int   | ROI riêng của event – tọa độ x1 của Teaching image                | 0                |
| `{event_id}_teaching_corner_y1`   | int   | ROI riêng của event – tọa độ y1 của Teaching image                | 0                |
| `{event_id}_teaching_corner_x2`   | int   | ROI riêng của event – tọa độ x2 của Teaching image                | 0                |
| `{event_id}_teaching_corner_y2`   | int   | ROI riêng của event – tọa độ y2 của Teaching image                | 0                |
| `{event_id}_ocr_engine`           | str   | OCR engine để đọc thông báo sự kiện                                | "auto"           |
| `{event_id}_match_threshold`      | float | Ngưỡng fuzzy matching cả câu (0-100), dùng rapidfuzz partial_ratio | 70.0             |
| `{event_id}_ocr_algorithms`       | list  | Preprocessing algorithms cho OCR ROI                               | []               |

> Mỗi event có Teaching image riêng, không dùng chung với action. Các tham số nghiệp vụ riêng của từng event được định nghĩa trong file requirements của event đó.

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

### 2.1. Luồng UI – Bật/tắt event

```
┌──────────────────────────────────────┐
│  Mở PassiveReadSettingsDialog        │
│  Chọn mode: Special Event Tracking   │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Hiển thị danh sách special events   │
│  ☐ Imperial Guardian                 │
│  ☐ [Event tương lai...]              │
└──────────────┬───────────────────────┘
               │
       ┌───────┴────────┐
       │ Người dùng     │
       │ tick checkbox? │
       └───┬────────┬───┘
           │ Tick   │ Untick
           ▼        ▼
  ┌──────────────┐  ┌──────────────────────────┐
  │ Expand       │  │ Collapse section settings │
  │ section      │  │ Đánh dấu event = disabled │
  │ settings     │  └──────────────────────────┘
  └──────┬───────┘
         │
         ▼
┌──────────────────────────────────────┐
│  Người dùng nhấn Lưu                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Lưu settings vào JSON               │
│  (enabled flag + params từng event)  │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  Áp dụng thay đổi subscription       │
│  - Event enabled → subscribe         │
│  - Event disabled → unsubscribe      │
└──────────────────────────────────────┘
```

### 2.2. Luồng runtime

```
┌─────────────────────────┐
│  special_event_tracking │
│  mode được kích hoạt    │
└──────────┬──────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│  Với mỗi event được enabled:               │
│  → Tạo OCRSubscription                     │
│  → Subscribe vào ScreenScanService         │
│  → Identity: special_event:{action_id}:{event_id} │
└──────────┬─────────────────────────────────┘
           │ OCR callback
           ▼
┌──────────────────────────────────────┐
│  Delegate xử lý cho handler          │
│  của từng event (xem file riêng)     │
└──────────────────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Người dùng chọn mode Special Event Tracking**
- Input: Mở PassiveReadSettingsDialog, chọn "Special Event Tracking"
- Xử lý: Hiển thị danh sách special events dạng checkbox
- Output: Danh sách events với trạng thái đã lưu trước đó

**Bước 2: Người dùng tick/untick checkbox event**
- Input: Người dùng tick hoặc untick checkbox của một event
- Xử lý:
  - Tick → expand collapsible section settings bên dưới checkbox
  - Untick → collapse section settings, đánh dấu event = disabled
- Output: UI phản ánh trạng thái mới ngay lập tức

**Bước 3: Người dùng nhấn Lưu**
- Input: Người dùng nhấn nút "Lưu" trong dialog
- Xử lý:
  - Thu thập trạng thái enabled/disabled của từng event
  - Thu thập settings của từng event (ROI, params nghiệp vụ)
  - Persist vào action object qua `get_settings()` → `_action_to_dict()`
- Output: Settings được lưu vào JSON, dialog đóng

**Bước 4: Áp dụng subscription khi action chạy**
- Input: PassiveReader khởi động với mode `special_event_tracking`
- Xử lý:
  - Với mỗi event có `enabled = true`: tạo OCRSubscription với identity `special_event:{action_id}:{event_id}` và subscribe vào ScreenScanService
  - Với mỗi event có `enabled = false`: không subscribe (hoặc unsubscribe nếu đang chạy)
  - Mỗi event có subscription_id riêng để có thể unsubscribe độc lập
- Output: Chỉ các event được bật mới có subscription active

**Bước 5: OCR callback**
- Input: OCR text từ ScreenScanService callback
- Xử lý: Delegate cho handler riêng của từng event
- Output: Chi tiết xử lý xem file requirements của event đó

### 3.2. Edge Cases

**Case 1:** Không có event nào được tick → mode chạy nhưng không có subscription

**Case 2:** Tick event nhưng chưa cấu hình ROI → cảnh báo trong app, không subscribe

**Case 3:** Thay đổi settings khi action đang chạy → PassiveReader cập nhật subscription sau khi Lưu

**Case 4:** Thêm event mới → cần thêm checkbox trong UI, file requirements riêng, handler riêng, và đăng ký subscription trong `_setup_special_event_subscriptions()`. Không cần sửa shared flow nhưng vẫn cần UI/runtime registration tường minh cho từng event.

**Case 5:** JSON cũ thiếu `{event_id}_enabled` → default `false`

**Case 6:** Mode `event_tracking` cũ vẫn chọn → không bị ảnh hưởng

### 3.3. Error Handling

**Lỗi 1: OCR không đọc được text**
- Nguyên nhân: Vùng màn hình bị che, game bị minimize
- Xử lý: Bỏ qua chu kỳ đó, tiếp tục chu kỳ tiếp theo

**Lỗi 2: Telegram chưa cấu hình**
- Nguyên nhân: Người dùng chưa thiết lập token/chat_id
- Xử lý: Bỏ qua việc gửi, log cảnh báo trong app

**Lỗi 3: Telegram API thất bại**
- Nguyên nhân: Mất mạng, token hết hạn
- Xử lý: Retry tối đa 3 lần, mỗi lần cách 2 giây; bỏ qua nếu vẫn thất bại

**Lỗi 4: ROI không hợp lệ**
- Nguyên nhân: Người dùng chưa cấu hình Teaching image cho event
- Xử lý: Hiển thị cảnh báo trong app, không bắt đầu subscription cho event đó

**Lỗi 5: Unsubscribe event chưa subscribe**
- Nguyên nhân: Event bị disabled từ đầu, chưa từng subscribe
- Xử lý: Bỏ qua silently (ScreenScanService.unsubscribe xử lý trường hợp này)

**Lỗi 6: Cập nhật UI từ background thread**
- Nguyên nhân: OCR callback chạy trong scan thread, không phải UI thread
- Xử lý: Tất cả cập nhật UI phải thực hiện qua Qt signals với QueuedConnection, không gọi QWidget methods trực tiếp từ background thread

---

## 4. PHÁC THẢO UI

```
┌─────────────────────────────────────────────────────────────────┐
│  Cài đặt Passive Read Action                                 [X] │
├─────────────────────────────────────────────────────────────────┤
│  Chế độ: [Special Event Tracking          ▼]                    │
├─────────────────────────────────────────────────────────────────┤
│  🎯 Special Events                                              │
│                                                                 │
│  ☑ Imperial Guardian                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  No-player alert delay (minutes): [10 ↕]               │   │
│  │  OCR Engine: [EasyOCR              ▼]                   │   │
│  │  Match threshold: [70 ↕] %                              │   │
│  │                                                         │   │
│  │  Teaching image ROI: (10, 20) → (200, 100)             │   │
│  │  [Select Teaching Image]                                │   │
│  │                                                         │   │
│  │  [🧪 Test Algorithms]                                   │   │
│  │  Selected Algorithms:                                   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Binary Threshold                                │   │   │
│  │  │ Upscale 3x                                      │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ☐ [Event tương lai...]                                        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                              [Lưu]  [Hủy]      │
└─────────────────────────────────────────────────────────────────┘
```

| Thành phần                     | Loại widget      | Mô tả                                                        |
|--------------------------------|------------------|--------------------------------------------------------------|
| Dropdown "Chế độ"              | QComboBox        | Thêm item "Special Event Tracking"                           |
| Checkbox event                 | QCheckBox        | Bật/tắt từng event                                           |
| Section settings (collapsible) | QWidget ẩn/hiện  | Expand khi tick, collapse khi untick                         |
| No-player alert delay          | QSpinBox         | Range 1-120, default 10, suffix " phút"                      |
| OCR Engine                     | QComboBox        | Auto/WinRT/Tesseract/EasyOCR/VietOCR                         |
| Match threshold                | QSpinBox         | Range 0-100, default 70, suffix "%"                          |
| Teaching image ROI             | QPushButton      | Mở ImageCaptureDialog để chọn ROI                            |
| Test Algorithms                | QPushButton      | Mở MultiImageAlgorithmTestingDialog với ROI của event        |
| Selected Algorithms            | QListWidget      | Hiển thị algorithms đã chọn (read-only)                      |

---

## 5. PERSISTENCE RULES

| Bước | Mô tả                                                       | Trường liên quan                                                                                                                    |
|------|-------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Thêm checkbox + collapsible section vào dialog              | `{event_id}_checkbox`, `{event_id}_widget`                                                                                          |
| 2    | Lưu vào action object trong `get_settings()`                | `{event_id}_enabled`, `{event_id}_no_player_alert_delay`, `{event_id}_ocr_engine`, `{event_id}_match_threshold`, `{event_id}_ocr_algorithms`, ROI riêng, params riêng   |
| 3    | Load từ action object trong `_load_settings()`              | `{event_id}_enabled`, `{event_id}_no_player_alert_delay`, `{event_id}_ocr_engine`, `{event_id}_match_threshold`, `{event_id}_ocr_algorithms`, ROI riêng, params riêng   |
| 4    | Thêm trường vào `_action_to_dict()` trong `tool_manager.py` | `{event_id}_enabled`, `{event_id}_no_player_alert_delay`, `{event_id}_ocr_engine`, `{event_id}_match_threshold`, `{event_id}_ocr_algorithms`, ROI, params riêng         |
| 5    | Thêm trường vào `from_dict()` trong `tool_manager.py`       | default: enabled=false, no_player_alert_delay=10, ocr_engine="auto", match_threshold=70.0, ocr_algorithms=[], ROI=0                                                     |
| 6    | ROI lưu riêng theo event_id, không dùng chung với action    | `{event_id}_teaching_corner_x1/y1/x2/y2`                                                                                           |
| 7    | Test: Lưu → đóng app → mở lại → kiểm tra giá trị còn đúng  | enabled flag, no_player_alert_delay, ocr_engine, match_threshold, ocr_algorithms, ROI, params phải giữ nguyên                                              |

> Chi tiết persistence của từng event xem trong file requirements riêng của event đó.
