# White Wizard + Red Dragon Event Tracker - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**
Sự kiện White Wizard + Red Dragon trong game MU Online diễn ra theo lịch cố định nhiều lần trong ngày. Mỗi lần xuất hiện 2 Phù Thủy Trắng và 2 Rồng Đỏ (tổng 4 con). Người chơi cần biết con nào đã bị tiêu diệt và còn bao nhiêu con để phối hợp săn, nhưng không thể theo dõi màn hình liên tục.

**Mục tiêu:**
Tự động theo dõi thông báo boss bị tiêu diệt trong sự kiện White Wizard + Red Dragon qua OCR, kiểm tra tính hợp lệ dựa trên channel hiện tại, và gửi thông báo Telegram chuẩn hóa kèm số lượng boss còn lại.

**Input/Output:**

| Loại   | Mô tả                                                                 | Ví dụ                                                                                                    |
|--------|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Input  | Thông báo boss bị tiêu diệt                                          | "Phù Thủy Trắng đã bị tiêu diệt bởi PlayerX và đồng đội tại Lorencia"                                  |
| Input  | Tên channel hiện tại (Vùng 1)                                        | "CS1", "CS2", ...                                                                                        |
| Input  | Thời gian hiện tại của máy                                           | 19:10 → sự kiện bắt đầu                                                                                  |
| Output | Thông báo Telegram khi boss bị tiêu diệt (channel không đổi)        | "Phù Thủy Trắng đã bị tiêu diệt tại Lorencia (SV CS1)\nCòn 1 Phù Thủy Trắng và 2 Rồng Đỏ"            |
| Output | Thông báo Telegram khi hết tất cả boss                              | "...Còn 0 Phù Thủy Trắng và 0 Rồng Đỏ — Đã hết boss!"                                                  |
| Output | Không gửi khi channel đã thay đổi hoặc boss đã gửi đủ số lượng     | (im lặng)                                                                                                |

**Danh sách boss:**

| Boss             | Số lượng tối đa | Tên normalized (để matching) |
|------------------|-----------------|------------------------------|
| Phù Thủy Trắng  | 2               | phu thuy trang               |
| Rồng Đỏ         | 2               | rong do                      |

**Lịch sự kiện (23 mốc trong ngày):**

```
00:10, 01:10, 08:10, 09:10, 10:10, 11:10, 11:40,
12:10, 12:40, 13:10, 14:10, 15:10, 16:10, 17:10,
18:10, 19:10, 19:40, 20:10, 20:40, 21:10, 21:40,
22:10, 23:10
```

**Parameters (Tham số):**

**Parameters (Tham số riêng của White Wizard + Red Dragon):**

> ROI, OCR engine, algorithms và match threshold dùng chung từ Monster Invasion. Xem `monster-invasion-event-tracker.md`.

| Tham số                                                          | Kiểu    | Mô tả                                                              | Giá trị mặc định |
|------------------------------------------------------------------|---------|--------------------------------------------------------------------|------------------|
| `monster_invasion_white_wizard_red_dragon_enabled`               | bool    | Bật/tắt sub-event White Wizard + Red Dragon                        | false            |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```
┌─────────────────────────────────────────────┐
│  Nhận OCR text từ MonsterInvasionHandler    │
│  (fan-out từ Vùng 1 và Vùng 2)             │
│  Trạng thái ban đầu: WAITING               │
└──────────────┬──────────────────────────────┘
               │ Đến mốc giờ trong lịch 23 mốc
               ▼
┌─────────────────────────────────────────────┐
│  Chuyển trạng thái: ACTIVE                  │
│  - Snapshot channel_at_start từ Vùng 1      │
│  - Reset killed_map = {                     │
│      "phu thuy trang": 0,                   │
│      "rong do": 0                           │
│    }                                        │
│  - Bắt đầu đếm 25 phút reset timer         │
└──────────────┬──────────────────────────────┘
               │ OCR text liên tục (fan-out từ Monster Invasion)
               ▼
┌─────────────────────────────────────────────────────────────────┐
│  on_channel_text: cập nhật channel_current                      │
│  on_notify_text: parse thông báo (KHÔNG cache text)             │
└──────────────┬──────────────────────────────────────────────────┘
               │
               ▼
       ┌───────┴────────┐
       │ on_notify_text │
       │ match pattern? │
       └───┬────────┬───┘
           │ Có     │ Không
           ▼        ▼
  ┌──────────────┐  ┌──────────┐
  │ Trích xuất   │  │ Bỏ qua   │
  │ boss + map   │  └──────────┘
  └──────┬───────┘
         │
         ▼
  ┌──────────────────────────────────┐
  │ Boss có trong danh sách?         │
  └──────┬───────────────────────────┘
         │ Có              │ Không
         ▼                 ▼
  ┌────────────────────┐  ┌──────────┐
  │ killed_map[boss]   │  │ Bỏ qua   │
  │ >= 2?              │  └──────────┘
  └──┬─────────────────┘
     │ Rồi  │ Chưa
     ▼      ▼
  ┌──────┐ ┌──────────────────────────────────────┐
  │ Bỏ   │ │ channel_current == channel_at_start? │
  │ qua  │ └──────────┬───────────────────────────┘
  └──────┘            │ Bằng        │ Khác
                      ▼             ▼
             ┌──────────────┐  ┌──────────┐
             │ Gửi Telegram │  │ Bỏ qua   │
             │ + tăng       │  └──────────┘
             │ killed_map   │
             └──────┬───────┘
                    │
                    ▼
          ┌─────────────────────────┐
          │ Tổng killed == 4?       │
          └──────┬──────────────────┘
                 │ Có           │ Không
                 ▼              ▼
          ┌──────────────┐  ┌──────────────────┐
          │ WAITING      │  │ Tiếp tục theo dõi│
          │ (hết boss)   │  └──────────────────┘
          └──────────────┘

Luồng song song: Reset timer 25 phút
┌──────────────────────────────────────────────────────┐
│ Sau 25 phút kể từ lúc ACTIVE:                        │
│ → Chuyển WAITING, reset killed_map, tính mốc tiếp   │
└──────────────────────────────────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Chờ đến mốc giờ sự kiện**
- Input: Thời gian hiện tại, danh sách 23 mốc giờ
- Xử lý: Luôn bắt đầu ở WAITING. Tìm mốc giờ tiếp theo trong danh sách. Khi đến giờ → chuyển ACTIVE
- Output: Trạng thái ACTIVE

**Bước 2: Khởi tạo trạng thái sự kiện**
- Input: Sự kiện bắt đầu (theo lịch)
- Xử lý:
  - Đọc Vùng 1 → lưu `channel_at_start` (normalize)
  - Reset `killed_map = {"phu thuy trang": 0, "rong do": 0}`
  - Bắt đầu đếm 25 phút reset timer
- Output: Trạng thái sẵn sàng theo dõi

**Bước 3: Đọc liên tục 2 vùng**
- Input: OCR callback từ ScreenScanService
- Xử lý:
  - **Vùng 1 callback**: Cập nhật `channel_current` = normalize(text)
  - **Vùng 2 callback**: Parse thông báo — **không cache text**, xử lý mỗi lần nhận
- Output: `channel_current` luôn được cập nhật; Vùng 2 xử lý riêng

**Bước 4: Parse thông báo Vùng 2**
- Input: Text từ Vùng 2 (normalize trước khi xử lý)
- Xử lý: Match pattern `{boss} da bi tieu diet boi {player} va dong doi tai {map}`
  - Trích xuất: tên boss (normalize), tên map (giữ nguyên từ OCR)
- Output: Boss name + map, hoặc bỏ qua nếu không match

**Bước 5: Kiểm tra hợp lệ**
- Input: Boss name, `killed_map`, `channel_current`, `channel_at_start`
- Xử lý theo thứ tự:
  1. Boss có trong danh sách? → Không: bỏ qua
  2. `killed_map[boss] >= 2`? → Rồi: bỏ qua (dedup)
  3. `channel_current == channel_at_start`? → Khác: bỏ qua
  4. Tất cả pass → gửi (Bước 6)
- Output: Quyết định gửi hoặc bỏ qua

**Bước 6: Gửi Telegram và cập nhật trạng thái**
- Input: Boss name, map, `channel_current`, `killed_map`
- Xử lý:
  - Tăng `killed_map[boss]` lên 1
  - Tính số còn lại: `remaining_white = 2 - killed_map["phu thuy trang"]`, `remaining_red = 2 - killed_map["rong do"]`
  - Tạo message và gửi Telegram (tên boss dùng tiếng Việt có dấu)
  - Nếu tổng killed == 4 → chuyển WAITING
- Output: Telegram được gửi, trạng thái cập nhật

**Format Telegram:**
```
{Tên boss có dấu} đã bị tiêu diệt tại {Map} (SV {channel_current})
Còn {X} Phù Thủy Trắng và {Y} Rồng Đỏ
```

Khi hết tất cả (X=0, Y=0):
```
{Tên boss có dấu} đã bị tiêu diệt tại {Map} (SV {channel_current})
Còn 0 Phù Thủy Trắng và 0 Rồng Đỏ — Đã hết boss!
```

**Bước 7: Reset sau 25 phút**
- Input: Timer 25 phút kể từ lúc ACTIVE
- Xử lý: Chuyển WAITING, reset `killed_map`, tính mốc giờ tiếp theo
- Output: Chu kỳ mới sẵn sàng

**Bước 8: Lưu cấu hình**
- Input: Người dùng nhấn Lưu trong dialog
- Xử lý: Lưu tất cả fields vào JSON
- Output: Cấu hình được persist

---

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Bật app ở bất kỳ thời điểm nào**
- Xử lý: Luôn bắt đầu WAITING, chờ mốc giờ tiếp theo trong lịch

**Case 2: Channel thay đổi trong lúc sự kiện**
- Xử lý: `channel_current != channel_at_start` → bỏ qua tất cả thông báo tiếp theo cho đến khi reset 25 phút. `killed_map` giữ nguyên (không reset)

**Case 3: Cùng 1 con boss xuất hiện nhiều lần trong OCR**
- Xử lý: `killed_map[boss] >= 2` → bỏ qua (dedup theo số lượng tối đa)

**Case 4: OCR đọc sai tên boss**
- Xử lý: Fuzzy matching với ngưỡng `match_threshold` — bỏ qua nếu không đủ độ tin cậy

**Case 5: Hết 4 boss trước 25 phút**
- Xử lý: Chuyển WAITING ngay, không chờ hết 25 phút

**Case 6: Vùng 1 không đọc được channel**
- Xử lý: `channel_current` giữ nguyên giá trị cũ. Nếu chưa có giá trị → `channel_at_start = ""` → mọi thông báo bị bỏ qua

**Case 7: JSON cũ thiếu trường**
- Xử lý: Dùng giá trị mặc định và in log cảnh báo

**Case 8: Nhiều mốc giờ trong cùng 1 giờ (ví dụ 11:10 và 11:40)**
- Xử lý: Tìm mốc tiếp theo theo thứ tự thời gian trong ngày, không bỏ sót

---

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: OCR không đọc được text**
- Nguyên nhân: Vùng màn hình bị che, game bị minimize
- Xử lý: Bỏ qua lần đó, tiếp tục lần tiếp theo

**Lỗi 2: OCR đọc sai hoặc text mơ hồ**
- Nguyên nhân: Chất lượng ảnh thấp, font game đặc biệt
- Xử lý: Fuzzy matching với ngưỡng tối thiểu, bỏ qua nếu không đủ

**Lỗi 3: Telegram chưa cấu hình**
- Nguyên nhân: Người dùng chưa thiết lập token/chat_id
- Xử lý: Bỏ qua việc gửi, log cảnh báo

**Lỗi 4: Telegram API thất bại**
- Nguyên nhân: Mất mạng, token hết hạn
- Xử lý: Thử lại tối đa 3 lần, mỗi lần cách 2 giây

**Lỗi 5: ROI chưa cấu hình**
- Nguyên nhân: Người dùng chưa chọn Teaching image
- Xử lý: Hiển thị cảnh báo, không subscribe

**Lỗi 6: Cập nhật UI từ background thread**
- Nguyên nhân: OCR callback chạy trong scan thread
- Xử lý: Tất cả cập nhật UI qua Qt signals với QueuedConnection

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
│  ☑ White Wizard + Red Dragon                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  ── Vùng 1: Channel ──────────────────────────────────  │   │
│  │  Teaching image ROI: (10, 20) → (200, 50)              │   │
│  │  [Select Channel ROI]                                   │   │
│  │  OCR Engine: [EasyOCR              ▼]                   │   │
│  │  [🧪 Test Algorithms - Channel]                         │   │
│  │  Selected Algorithms: [...]                             │   │
│  │                                                         │   │
│  │  ── Vùng 2: Thông báo ────────────────────────────────  │   │
│  │  Teaching image ROI: (10, 100) → (600, 300)            │   │
│  │  [Select Notify ROI]                                    │   │
│  │  OCR Engine: [EasyOCR              ▼]                   │   │
│  │  [🧪 Test Algorithms - Thông báo]                       │   │
│  │  Selected Algorithms: [...]                             │   │
│  │                                                         │   │
│  │  Match threshold: [70 ↕] %                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                              [Lưu]  [Hủy]      │
└─────────────────────────────────────────────────────────────────┘
```

| Thành phần                              | Loại widget      | Mô tả                                                              |
|-----------------------------------------|------------------|--------------------------------------------------------------------|
| Checkbox "White Wizard + Red Dragon"    | QCheckBox        | Bật/tắt event                                                      |
| Select Channel ROI                      | QPushButton      | Mở ImageCaptureDialog để chọn ROI Vùng 1                          |
| OCR Engine Vùng 1                       | QComboBox        | Auto/WinRT/Tesseract/EasyOCR/VietOCR                               |
| Test Algorithms - Channel               | QPushButton      | Mở MultiImageAlgorithmTestingDialog với ROI Vùng 1                |
| Selected Algorithms Vùng 1              | QListWidget      | Hiển thị algorithms đã chọn (read-only)                            |
| Select Notify ROI                       | QPushButton      | Mở ImageCaptureDialog để chọn ROI Vùng 2                          |
| OCR Engine Vùng 2                       | QComboBox        | Auto/WinRT/Tesseract/EasyOCR/VietOCR                               |
| Test Algorithms - Thông báo             | QPushButton      | Mở MultiImageAlgorithmTestingDialog với ROI Vùng 2                |
| Selected Algorithms Vùng 2              | QListWidget      | Hiển thị algorithms đã chọn (read-only)                            |
| Match threshold                         | QSpinBox         | Range 0-100, default 70, suffix "%"                                |

---

## 5. PERSISTENCE RULES

| Bước | Mô tả                                                        | Trường liên quan                                                                                                                                                                                                                                 |
|------|--------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Thêm checkbox + collapsible section vào dialog               | `white_wizard_red_dragon_checkbox`, `white_wizard_red_dragon_widget`                                                                                                                                                                             |
| 2    | Lưu vào action object trong `get_settings()`                 | Tất cả 16 fields `white_wizard_red_dragon_*`                                                                                                                                                                                                     |
| 3    | Load từ action object trong `_load_settings()`               | Tất cả 16 fields                                                                                                                                                                                                                                 |
| 4    | Thêm trường vào `_action_to_dict()` trong `tool_manager.py`  | Tất cả 16 fields                                                                                                                                                                                                                                 |
| 5    | Thêm trường vào `from_dict()` trong `tool_manager.py`        | default: enabled=false, match_threshold=70.0, ocr_engine="auto", algorithms=[], ROI=0, teaching_image_path=""                                                                                                                                    |
| 6    | ROI lưu riêng theo vùng, không dùng chung với action         | `white_wizard_red_dragon_channel_roi_*`, `white_wizard_red_dragon_notify_roi_*`                                                                                                                                                                  |
| 7    | Test: Lưu → đóng app → mở lại → kiểm tra giá trị còn đúng   | Tất cả fields phải giữ nguyên                                                                                                                                                                                                                    |
