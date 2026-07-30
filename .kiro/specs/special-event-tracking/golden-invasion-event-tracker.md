# Golden Invasion Event Tracker - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**
Sự kiện Golden Invasion trong game MU Online diễn ra định kỳ mỗi 3 tiếng, thả ra nhiều quái vật đặc biệt. Người chơi cần biết con nào đã bị tiêu diệt và con nào còn lại để phối hợp săn, nhưng không thể theo dõi màn hình liên tục. Ngoài ra, thông báo tiêu diệt chỉ có giá trị nếu người chơi đang ở đúng server (channel) — nếu channel đã thay đổi thì thông tin không còn liên quan.

**Mục tiêu:**
Tự động theo dõi thông báo quái vật bị tiêu diệt trong sự kiện Golden Invasion qua OCR, kiểm tra tính hợp lệ của thông báo dựa trên channel hiện tại, và gửi thông báo Telegram chuẩn hóa kèm danh sách quái vật còn lại.

**Input/Output:**

| Loại   | Mô tả                                                                 | Ví dụ                                                                                      |
|--------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Input  | Thông báo quái vật bị tiêu diệt (pattern 1)                          | "Kim Thiết Vương đã bị tiêu diệt bởi PlayerX và đồng động tại Lorencia"                   |
| Input  | Thông báo quái vật bị tiêu diệt (pattern 2)                          | "Kim Xạ Vương đã bị tiêu diệt bởi PlayerY tại Noria"                                      |
| Input  | Tên channel hiện tại (Vùng 1)                                        | "CS1", "CS2", ...                                                                          |
| Input  | Thời gian hiện tại của máy                                           | 01:30 → sự kiện bắt đầu                                                                    |
| Output | Thông báo Telegram khi quái vật bị tiêu diệt (channel không đổi)    | "Kim Thiết Vương đã bị tiêu diệt ở SV CS1\nSV CS1 hiện tại còn Kim Xạ Vương, Chiến Binh Vàng, ..." |
| Output | Không gửi gì khi channel đã thay đổi hoặc quái vật đã gửi rồi       | (im lặng)                                                                                  |

**Danh sách tên quái vật theo dõi:**

| STT | Tên quái vật     |
|-----|------------------|
| 1   | Kim Thiết Vương  |
| 2   | Kim Xạ Vương     |
| 3   | Chiến Binh Vàng  |
| 4   | Người Máy Vàng   |
| 5   | Kim Ngư Tinh     |
| 6   | Kim Ngư Vương    |
| 7   | Kim Xạ Thủ       |

**Parameters (Tham số riêng của Golden Invasion):**

> ROI, OCR engine, algorithms và match threshold dùng chung từ Monster Invasion. Xem `monster-invasion-event-tracker.md`.

| Tham số                                          | Kiểu    | Mô tả                                                              | Giá trị mặc định |
|--------------------------------------------------|---------|--------------------------------------------------------------------|------------------|
| `monster_invasion_golden_invasion_enabled`       | bool    | Bật/tắt sub-event Golden Invasion                                  | false            |
| `monster_invasion_golden_invasion_server_time`   | str     | Thời điểm bắt đầu sự kiện: "00:40" hoặc "01:30"                   | "01:30"          |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```
┌─────────────────────────────────────────────┐
│  Nhan OCR text tu MonsterInvasionHandler    │
│  (fan-out tu Vung 1 va Vung 2)             │
│  Trang thai ban dau: WAITING               │
└──────────────┬──────────────────────────────┘
               │ Den gio su kien (00:40 hoac 01:30)
               ▼
┌─────────────────────────────────────────────┐
│  Chuyen trang thai: ACTIVE                  │
│  - Snapshot channel_at_start tu Vung 1      │
│  - Reset killed_set = {}                    │
│  - remaining_set = {7 ten quai vat}         │
└──────────────┬──────────────────────────────┘
               │ OCR text lien tuc (fan-out tu Monster Invasion)
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  on_channel_text: cap nhat channel_current                      │
│  on_notify_text: kiem tra pattern thong bao                     │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
       ┌───────┴────────┐
       │ Vùng 2 match   │
       │ pattern?       │
       └───┬────────┬───┘
           │ Có     │ Không
           ▼        ▼
  ┌──────────────┐  ┌──────────┐
  │ Trích xuất   │  │ Bỏ qua   │
  │ tên quái vật │  └──────────┘
  │ + map        │
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────────┐
  │ Tên quái vật có trong danh sách? │
  └──────┬───────────────────────────┘
         │ Có              │ Không
         ▼                 ▼
  ┌────────────┐     ┌──────────┐
  │ Đã gửi     │     │ Bỏ qua   │
  │ rồi?       │     └──────────┘
  └──┬─────┬───┘
     │ Rồi │ Chưa
     ▼     ▼
  ┌──────┐ ┌──────────────────────────────────────┐
  │ Bỏ   │ │ channel_current == channel_at_start? │
  │ qua  │ └──────────┬───────────────────────────┘
  └──────┘            │ Bằng        │ Khác
                      ▼             ▼
             ┌──────────────┐  ┌──────────┐
             │ Gửi Telegram │  │ Bỏ qua   │
             │ + cập nhật   │  └──────────┘
             │ killed_set   │
             │ remaining_set│
             └──────┬───────┘
                    │
                    ▼
          ┌─────────────────────┐
          │ remaining_set rỗng? │
          └──────┬──────────────┘
                 │ Có           │ Không
                 ▼              ▼
          ┌──────────────┐  ┌──────────────────┐
          │ Chuyển sang  │  │ Tiếp tục theo dõi│
          │ WAITING      │  └──────────────────┘
          │ (hết sự kiện)│
          └──────────────┘

Luồng song song: Reset theo lịch
┌──────────────────────────────────────────────────────┐
│ Mỗi 3 tiếng (00:40 hoặc 01:30 tiếp theo):           │
│ → Chuyển ACTIVE, snapshot channel mới, reset sets   │
└──────────────────────────────────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Chờ đến giờ sự kiện**
- Input: Thời gian hiện tại của máy, cấu hình `golden_invasion_server_time`
- Xử lý: Khởi động luôn ở trạng thái WAITING. Tính thời điểm sự kiện tiếp theo (00:40 hoặc 01:30, mỗi 3 tiếng). Khi đến giờ → chuyển ACTIVE
- Output: Trạng thái ACTIVE, sẵn sàng theo dõi

**Bước 2: Khởi tạo trạng thái sự kiện**
- Input: Sự kiện bắt đầu (theo lịch)
- Xử lý:
  - Đọc Vùng 1 → lưu `channel_at_start` (snapshot channel tại thời điểm bắt đầu)
  - Reset `killed_set = set()` (tập quái vật đã bị tiêu diệt)
  - Reset `remaining_set = {7 tên quái vật}` (tập quái vật còn lại)
- Output: Trạng thái sẵn sàng theo dõi

**Bước 3: Đọc liên tục 2 vùng**
- Input: OCR callback từ ScreenScanService
- Xử lý:
  - **Vùng 1 callback**: Cập nhật `channel_current` = text mới nhất từ Vùng 1
  - **Vùng 2 callback**: Kiểm tra pattern thông báo (Bước 4)
- Output: `channel_current` luôn được cập nhật; Vùng 2 xử lý riêng

**Bước 4: Phân tích thông báo Vùng 2**
- Input: Text mới từ Vùng 2
- Xử lý: So khớp với 2 pattern dùng `rapidfuzz.partial_ratio` với ngưỡng `golden_invasion_match_threshold`:
  - Pattern 1: `{TÊN QUÁI VẬT} đã bị tiêu diệt bởi {NGƯỜI CHƠI} và đồng động tại {MAP}`
  - Pattern 2: `{TÊN QUÁI VẬT} đã bị tiêu diệt bởi {NGƯỜI CHƠI} tại {MAP}`
  - Trích xuất: tên quái vật (bỏ qua tên người chơi và map)
- Output: Tên quái vật trích xuất được, hoặc bỏ qua nếu không match

**Bước 5: Kiểm tra hợp lệ**
- Input: Tên quái vật trích xuất, `killed_set`, `channel_current`, `channel_at_start`
- Xử lý theo thứ tự:
  1. Tên quái vật có trong danh sách 7 con? → Không: bỏ qua
  2. Tên quái vật đã có trong `killed_set`? → Rồi: bỏ qua (chống trùng lặp)
  3. `channel_current == channel_at_start`? → Khác: bỏ qua (channel đã thay đổi)
  4. Tất cả pass → tiến hành gửi (Bước 6)
- Output: Quyết định gửi hoặc bỏ qua

**Bước 6: Gửi Telegram và cập nhật trạng thái**
- Input: Tên quái vật hợp lệ, `channel_current`, `remaining_set`
- Xử lý:
  - Thêm tên quái vật vào `killed_set`
  - Xóa tên quái vật khỏi `remaining_set`
  - Tạo message chuẩn hóa và gửi Telegram
  - Nếu `remaining_set` rỗng → chuyển trạng thái WAITING (sự kiện kết thúc sớm)
- Output: Telegram được gửi, trạng thái cập nhật

**Format Telegram:**
```
{TÊN QUÁI VẬT} đã bị tiêu diệt ở SV {channel_current}
SV {channel_current} hiện tại còn {danh sách remaining_set, cách nhau bằng dấu phẩy}
```

Ví dụ:
```
Kim Thiết Vương đã bị tiêu diệt ở SV CS1
SV CS1 hiện tại còn Kim Xạ Vương, Chiến Binh Vàng, Người Máy Vàng, Kim Ngư Tinh, Kim Ngư Vương, Kim Xạ Thủ
```

Khi tất cả đã bị tiêu diệt (remaining_set rỗng), dòng thứ 2:
```
SV CS1 hiện tại còn (không còn con nào)
```

**Bước 7: Reset theo lịch**
- Input: Đến giờ sự kiện tiếp theo (3 tiếng sau)
- Xử lý: Lặp lại từ Bước 2 — snapshot channel mới, reset `killed_set` và `remaining_set`
- Output: Chu kỳ mới bắt đầu

**Bước 8: Lưu cấu hình**
- Input: Người dùng nhấn Lưu trong dialog cài đặt
- Xử lý: Lưu `server_time`, ROI Vùng 1, OCR Vùng 1, ROI Vùng 2, OCR Vùng 2, `match_threshold` vào JSON
- Output: Cấu hình được persist, load lại đúng khi mở app lần sau

---

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Bật app ở bất kỳ thời điểm nào**
- Xử lý: Luôn bắt đầu ở trạng thái WAITING, bất kể sự kiện đang diễn ra hay chưa. Chờ đến lịch giờ sự kiện tiếp theo mới chuyển ACTIVE. Các quái vật bị tiêu diệt trước khi bật app sẽ không được ghi nhận (chấp nhận được).

**Case 2: Channel thay đổi trong lúc sự kiện**
- Xử lý: `channel_current` ≠ `channel_at_start` → bỏ qua tất cả thông báo tiếp theo cho đến khi sự kiện reset (chu kỳ 3 tiếng tiếp theo). Không tự khớp lại khi channel trùng nhau.

**Case 3: Cùng một quái vật xuất hiện nhiều lần trong thông báo**
- Xử lý: `killed_set` đã có tên → bỏ qua (chống trùng lặp trong 3 tiếng)

**Case 4: OCR đọc sai tên quái vật**
- Xử lý: Fuzzy matching với ngưỡng `match_threshold` — nếu không đủ độ tin cậy thì bỏ qua

**Case 5: Tất cả quái vật bị tiêu diệt trước 3 tiếng**
- Xử lý: `remaining_set` rỗng → chuyển WAITING, không gửi thêm. Đợi chu kỳ 3 tiếng tiếp theo.

**Case 6: Vùng 1 không đọc được channel**
- Xử lý: `channel_current` giữ nguyên giá trị cũ nhất. Nếu chưa có giá trị nào (lúc bắt đầu) → `channel_at_start = ""`, mọi thông báo sẽ bị bỏ qua cho đến khi đọc được.

**Case 7: JSON cũ thiếu trường cấu hình**
- Xử lý: Dùng giá trị mặc định (server_time="01:30", match_threshold=70.0, ROI=0, ocr_engine="auto", algorithms=[]) và in log cảnh báo để thông báo trường bị thiếu.

**Case 8: Sự kiện chưa bắt đầu (trạng thái WAITING)**
- Xử lý: Vùng 2 vẫn được đọc nhưng không xử lý pattern — bỏ qua tất cả cho đến khi ACTIVE

---

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: OCR không đọc được text**
- Nguyên nhân: Vùng màn hình bị che, game bị minimize
- Xử lý: Bỏ qua chu kỳ đó, tiếp tục chu kỳ tiếp theo

**Lỗi 2: OCR đọc sai hoặc text mơ hồ**
- Nguyên nhân: Chất lượng ảnh thấp, font game đặc biệt
- Xử lý: Fuzzy matching với ngưỡng tối thiểu, bỏ qua nếu không đủ độ tin cậy

**Lỗi 3: Telegram chưa cấu hình token/chat_id**
- Nguyên nhân: Người dùng chưa thiết lập Telegram
- Xử lý: Bỏ qua việc gửi, log cảnh báo trong app

**Lỗi 4: Telegram API thất bại**
- Nguyên nhân: Mất mạng, token hết hạn
- Xử lý: Thử lại tối đa 3 lần, mỗi lần cách 2 giây

**Lỗi 5: ROI chưa chọn hoặc không hợp lệ**
- Nguyên nhân: Người dùng chưa cấu hình Teaching image cho Vùng 1 hoặc Vùng 2
- Xử lý: Hiển thị cảnh báo trong app, không bắt đầu subscription cho event này

**Lỗi 6: Cập nhật UI từ background thread**
- Nguyên nhân: OCR callback chạy trong scan thread
- Xử lý: Tất cả cập nhật UI phải thực hiện qua Qt signals với QueuedConnection

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
│  ┌─ (collapsed) ──────────────────────────────────────────┐   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ☑ Golden Invasion                                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Server time: ☐ 00:40  ☑ 01:30                         │   │
│  │                                                         │   │
│  │  ── Vùng 1: Channel ──────────────────────────────────  │   │
│  │  Teaching image ROI: (10, 20) → (200, 50)              │   │
│  │  [Select Channel ROI]                                   │   │
│  │  OCR Engine: [EasyOCR              ▼]                   │   │
│  │  [🧪 Test Algorithms - Channel]                         │   │
│  │  Selected Algorithms:                                   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Binary Threshold                                │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  ── Vùng 2: Thông báo ────────────────────────────────  │   │
│  │  Teaching image ROI: (10, 100) → (600, 300)            │   │
│  │  [Select Notify ROI]                                    │   │
│  │  OCR Engine: [EasyOCR              ▼]                   │   │
│  │  [🧪 Test Algorithms - Thông báo]                       │   │
│  │  Selected Algorithms:                                   │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Upscale 3x                                      │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  │                                                         │   │
│  │  Match threshold: [70 ↕] %                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                              [Lưu]  [Hủy]      │
└─────────────────────────────────────────────────────────────────┘
```

| Thành phần                        | Loại widget      | Mô tả                                                              |
|-----------------------------------|------------------|--------------------------------------------------------------------|
| Checkbox "Golden Invasion"        | QCheckBox        | Bật/tắt event                                                      |
| Server time                       | 2x QRadioButton  | Chọn 00:40 hoặc 01:30, mặc định 01:30                             |
| Select Channel ROI                | QPushButton      | Mở ImageCaptureDialog để chọn ROI Vùng 1                          |
| OCR Engine Vùng 1                 | QComboBox        | Auto/WinRT/Tesseract/EasyOCR/VietOCR                               |
| Test Algorithms - Channel         | QPushButton      | Mở MultiImageAlgorithmTestingDialog với ROI Vùng 1                |
| Selected Algorithms Vùng 1        | QListWidget      | Hiển thị algorithms đã chọn cho Vùng 1 (read-only)                |
| Select Notify ROI                 | QPushButton      | Mở ImageCaptureDialog để chọn ROI Vùng 2                          |
| OCR Engine Vùng 2                 | QComboBox        | Auto/WinRT/Tesseract/EasyOCR/VietOCR                               |
| Test Algorithms - Thông báo       | QPushButton      | Mở MultiImageAlgorithmTestingDialog với ROI Vùng 2                |
| Selected Algorithms Vùng 2        | QListWidget      | Hiển thị algorithms đã chọn cho Vùng 2 (read-only)                |
| Match threshold                   | QSpinBox         | Range 0-100, default 70, suffix "%"                                |

---

## 5. PERSISTENCE RULES

| Bước | Mô tả                                                        | Trường liên quan                                                                                                                                                                                                                                 |
|------|--------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Thêm checkbox + collapsible section vào dialog               | `golden_invasion_checkbox`, `golden_invasion_widget`                                                                                                                                                                                             |
| 2    | Lưu vào action object trong `get_settings()`                 | `golden_invasion_enabled`, `golden_invasion_server_time`, `golden_invasion_channel_roi_x1/y1/x2/y2`, `golden_invasion_channel_ocr_engine`, `golden_invasion_channel_ocr_algorithms`, `golden_invasion_notify_roi_x1/y1/x2/y2`, `golden_invasion_notify_ocr_engine`, `golden_invasion_notify_ocr_algorithms`, `golden_invasion_match_threshold` |
| 3    | Load từ action object trong `_load_settings()`               | Tất cả trường trên                                                                                                                                                                                                                               |
| 4    | Thêm trường vào `_action_to_dict()` trong `tool_manager.py`  | Tất cả trường trên                                                                                                                                                                                                                               |
| 5    | Thêm trường vào `from_dict()` trong `tool_manager.py`        | default: enabled=false, server_time="01:30", match_threshold=70.0, ocr_engine="auto", algorithms=[], ROI=0                                                                                                                                       |
| 6    | ROI lưu riêng theo vùng, không dùng chung với action         | `golden_invasion_channel_roi_x1/y1/x2/y2`, `golden_invasion_notify_roi_x1/y1/x2/y2`                                                                                                                                                             |
| 7    | Test: Lưu → đóng app → mở lại → kiểm tra giá trị còn đúng   | server_time, match_threshold, cả 2 ROI, cả 2 ocr_engine, cả 2 ocr_algorithms phải giữ nguyên                                                                                                                                                    |
