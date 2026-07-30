# Imperial Guardian Event Tracker - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**
Người chơi cần theo dõi sự kiện Imperial Guardian trong game MU Online nhưng không thể ngồi nhìn màn hình liên tục. Sự kiện mở/đóng theo khung giờ không cố định, phụ thuộc vào thời điểm người chơi tham gia.

**Mục tiêu:**
Tự động đọc thông báo sự kiện từ màn hình qua OCR, theo dõi trạng thái sự kiện, và gửi thông báo Telegram kịp thời khi sự kiện mở, đóng, hoặc không có người tham gia.

**Input/Output:**

| Loại   | Mô tả                                       | Ví dụ                                                                        |
|--------|---------------------------------------------|------------------------------------------------------------------------------|
| Input  | Thông báo sự kiện mở                        | "Sự kiện Imperial Guardian đã bắt đầu"                                       |
| Input  | Thông báo có người vào (sự kiện sắp đóng)   | "Sự kiện Imperial Guardian sẽ bắt đầu sau 30 phút"                           |
| Input  | Giờ hiện tại của máy                        | 14:35 → khung giờ 12h–18h → mở lại sau 30 phút                              |
| Output | Thông báo Telegram: sự kiện mở              | "Sự kiện Imperial Guardian đã bắt đầu"                                       |
| Output | Thông báo Telegram: sự kiện đóng            | "Sự kiện Imperial Guardian đã đóng, mở sau 30 phút"                          |
| Output | Thông báo Telegram: không có người          | "Sự kiện Imperial Guardian đang không có người tham gia sau 10 phút"         |

**Parameters (Tham số):**

| Tham số                                          | Kiểu      | Mô tả                                                    | Giá trị mặc định  |
|--------------------------------------------------|-----------|----------------------------------------------------------|-------------------|
| `imperial_guardian_no_player_alert_delay` (Y)    | số nguyên | Số phút sau khi mở mà không có người → gửi cảnh báo      | 10 phút           |
| `imperial_guardian_teaching_corner_x1`           | int       | ROI riêng – tọa độ x1 của Teaching image                 | 0                 |
| `imperial_guardian_teaching_corner_y1`           | int       | ROI riêng – tọa độ y1 của Teaching image                 | 0                 |
| `imperial_guardian_teaching_corner_x2`           | int       | ROI riêng – tọa độ x2 của Teaching image                 | 0                 |
| `imperial_guardian_teaching_corner_y2`           | int       | ROI riêng – tọa độ y2 của Teaching image                 | 0                 |
| `imperial_guardian_ocr_engine`                   | str       | OCR engine để đọc thông báo sự kiện                      | "auto"            |
| `imperial_guardian_match_threshold`              | float     | Ngưỡng fuzzy matching cả câu (0-100), dùng rapidfuzz partial_ratio | 70.0    |
| `imperial_guardian_ocr_algorithms`               | list      | Preprocessing algorithms cho OCR ROI (giống mode Đọc dữ liệu) | []           |

**Rule tính thời gian mở lại:**

| Khung giờ người vào | Thời gian mở lại |
|---------------------|------------------|
| 0h – 7h             | 60 phút          |
| 7h – 12h            | 45 phút          |
| 12h – 18h           | 30 phút          |
| 18h – 20h           | 20 phút          |
| 20h – 24h           | 15 phút          |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```
┌─────────────────────────┐
│  Khởi động app          │
│  Trạng thái: WAITING    │
│  (chưa biết sự kiện     │
│   đang open hay closed) │
└──────────┬──────────────┘
           │ OCR callback (event-driven, không có chu kỳ cố định)
           ▼
    ┌──────┴──────────────────────────────────────────────┐
    │ Nhận text từ OCR → dedup: trùng text cũ? → bỏ qua  │
    │ Không trùng → cập nhật cached text → xử lý         │
    └──────┬──────────────────────────────────────────────┘
           │
           ▼
    ┌──────┴──────┐
    │ Phân loại   │
    │ thông báo   │
    └──┬───────┬──┘
       │       │
       ▼       ▼
  "đã bắt   "sẽ bắt đầu
   đầu"      sau X phút"
       │       │
       ▼       ▼
  ┌────┴───┐  ┌──────────────────────────────┐
  │Trạng   │  │ Chỉ xử lý nếu đang OPEN      │
  │thái    │  │ X >= thời gian mở lại theo   │
  │hiện tại│  │ rule khung giờ?              │
  └──┬─────┘  └──┬──────────────┬────────────┘
     │           │ Có           │ Không
     │           ▼              ▼
     │      ┌────────┐    ┌──────────┐
     │      │CLOSED  │    │ Bỏ qua   │
     │      └────┬───┘    └──────────┘
     │           │
     ▼           ▼
  ┌──────────────────────────────────────────┐
  │ WAITING hoặc CLOSED → OPEN               │
  │ - Ghi thời điểm mở (open_time)           │
  │ - Reset no_player_alert_sent = False     │
  │ - Gửi Telegram "đã bắt đầu"             │
  │ - Bắt đầu theo dõi timer Y phút         │
  └──────────────────────────────────────────┘
           │
           ▼
  ┌──────────────────────────────────────────┐
  │ OPEN → CLOSED (khi X >= rule)            │
  │ - Gửi Telegram "đã đóng, mở sau X phút" │
  └──────────────────────────────────────────┘

Luồng song song khi đang OPEN (kiểm tra mỗi khi nhận OCR callback):
┌──────────────────────────────────────────────────────┐
│ Nếu (now - open_time) > Y phút                       │
│ VÀ chưa gửi cảnh báo (no_player_alert_sent = False)  │
│ VÀ trạng thái vẫn OPEN                               │
│ → Gửi Telegram "không có người tham gia sau Y phút"  │
│ → Đánh dấu no_player_alert_sent = True               │
└──────────────────────────────────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Khởi động**
- Input: App được bật lên
- Xử lý: Đặt trạng thái = WAITING (chưa biết sự kiện đang open hay closed), cached_text = None
- Output: Hệ thống sẵn sàng nhận OCR callback

**Bước 2: Nhận và dedup OCR text**
- Input: OCR callback trả về text từ vùng màn hình đã cấu hình
- Xử lý:
  - **Luôn chạy trước**: Kiểm tra no-player alert timer (Bước 5) — độc lập với dedup
  - Nếu text trùng với cached_text → dừng xử lý pattern matching (bỏ qua Bước 3, 4a, 4b)
  - Nếu text khác → cập nhật cached_text = text mới → tiếp tục Bước 3
- Output: Text mới để xử lý pattern, hoặc chỉ chạy timer check

**Bước 3: Phân loại thông báo**
- Input: Text mới từ Bước 2
- Xử lý: So khớp với các pattern dùng `rapidfuzz.partial_ratio` với ngưỡng `imperial_guardian_match_threshold`:
  - Match "đã bắt đầu" → xử lý Bước 4a
  - Match "sẽ bắt đầu sau X phút" → xử lý Bước 4b
  - Không match → bỏ qua
- Output: Loại thông báo và giá trị X (nếu có)

**Bước 4a: Xử lý "đã bắt đầu"**
- Input: Trạng thái hiện tại (WAITING hoặc CLOSED)
- Xử lý:
  - Nếu đang WAITING hoặc CLOSED → chuyển sang OPEN, ghi open_time, reset no_player_alert_sent = False, gửi Telegram "đã bắt đầu"
  - Nếu đang OPEN → bỏ qua (dedup, thực tế không xảy ra)
- Output: Trạng thái OPEN, Telegram được gửi

**Bước 4b: Xử lý "sẽ bắt đầu sau X phút"**
- Input: Trạng thái hiện tại, giá trị X phút
- Xử lý:
  - Nếu đang WAITING → bỏ qua (chưa biết sự kiện đang ở đâu)
  - Nếu đang OPEN:
    - X >= thời gian mở lại theo rule khung giờ hiện tại → chuyển sang CLOSED, gửi Telegram "đã đóng, mở sau X phút"
    - X < thời gian mở lại → bỏ qua (countdown gần giờ mở, không phải mốc đóng)
  - Nếu đang CLOSED → bỏ qua
- Output: Trạng thái CLOSED (nếu điều kiện thỏa), Telegram được gửi

**Bước 5: Kiểm tra cảnh báo không có người**
- Input: Mỗi lần nhận OCR callback, kiểm tra nếu đang OPEN
- Xử lý: Nếu (now - open_time) > Y phút VÀ no_player_alert_sent = False VÀ trạng thái vẫn OPEN → gửi Telegram "không có người tham gia sau Y phút", đánh dấu no_player_alert_sent = True
- Output: Telegram cảnh báo gửi 1 lần duy nhất cho mỗi lần OPEN

**Bước 6: Lưu cấu hình**
- Input: Người dùng nhấn Lưu trong dialog cài đặt
- Xử lý: Lưu Y (thời gian cảnh báo), OCR engine, match threshold, OCR algorithms và ROI vào file JSON của tool
- Output: Cấu hình được persist, load lại đúng khi mở app lần sau

---

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Bật app khi không có sự kiện**
- Xử lý: Giữ trạng thái WAITING, không gửi thông báo cho đến khi nhận "đã bắt đầu"

**Case 2: Bật app khi sự kiện đang diễn ra**
- Xử lý: Giữ trạng thái WAITING cho đến khi nhận thông báo tiếp theo. Nếu nhận "sẽ bắt đầu sau X phút" → bỏ qua (vì chưa biết context). Nếu nhận "đã bắt đầu" → chuyển OPEN bình thường.

**Case 3: OCR nhận cùng text nhiều lần liên tiếp**
- Xử lý: Dedup theo cached_text — chỉ xử lý khi text thay đổi, bỏ qua nếu trùng

**Case 4: Thông báo countdown nhỏ (X < rule khung giờ)**
- Xử lý: Bỏ qua — đây là countdown gần giờ mở lại, không phải mốc đóng chuẩn

**Case 5: Sự kiện mở nhưng không có ai vào**
- Xử lý: Duy trì trạng thái OPEN, gửi cảnh báo sau Y phút nếu chưa nhận "sẽ bắt đầu sau X phút"

**Case 6: File JSON cũ không có trường cấu hình**
- Xử lý: Dùng giá trị mặc định Y = 10 phút

---

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: OCR không đọc được text**
- Nguyên nhân: Vùng màn hình bị che, game bị minimize
- Xử lý: Bỏ qua chu kỳ đó, tiếp tục chu kỳ tiếp theo

**Lỗi 2: OCR đọc sai hoặc text mơ hồ**
- Nguyên nhân: Chất lượng ảnh thấp, font game đặc biệt
- Xử lý: Fuzzy matching với ngưỡng tối thiểu, bỏ qua nếu không đủ độ tin cậy

**Lỗi 3: Telegram chưa cấu hình token/chat id**
- Nguyên nhân: Người dùng chưa thiết lập Telegram
- Xử lý: Bỏ qua việc gửi, log cảnh báo trong app

**Lỗi 4: Telegram API thất bại**
- Nguyên nhân: Mất mạng, token hết hạn
- Xử lý: Thử lại tối đa 3 lần, mỗi lần cách 2 giây

**Lỗi 5: ROI chưa chọn hoặc không hợp lệ**
- Nguyên nhân: Người dùng chưa cấu hình vùng màn hình
- Xử lý: Hiển thị cảnh báo trong app, không bắt đầu theo dõi

---

## 4. PERSISTENCE RULES

Khi thêm cấu hình mới, phải đảm bảo đủ các bước:

| Bước | Mô tả                                                        | Trường liên quan                                                              |
|------|--------------------------------------------------------------|-------------------------------------------------------------------------------|
| 1    | Thêm trường vào dialog cài đặt                               | SpinBox `imperial_guardian_no_player_alert_delay`, ComboBox `imperial_guardian_ocr_engine`, SpinBox `imperial_guardian_match_threshold` (0-100, default 70), Button "🧪 Test Algorithms", List algorithms, Teaching image widget |
| 2    | Lưu vào object trong hàm get_settings()                      | `imperial_guardian_no_player_alert_delay`, `imperial_guardian_ocr_engine`, `imperial_guardian_match_threshold`, `imperial_guardian_ocr_algorithms`, `imperial_guardian_teaching_corner_x1/y1/x2/y2` |
| 3    | Load từ object trong hàm _load_settings()                    | `imperial_guardian_no_player_alert_delay`, `imperial_guardian_ocr_engine`, `imperial_guardian_match_threshold`, `imperial_guardian_ocr_algorithms`, `imperial_guardian_teaching_corner_x1/y1/x2/y2` |
| 4    | Thêm trường vào hàm _action_to_dict() trong tool_manager     | `imperial_guardian_no_player_alert_delay`, `imperial_guardian_ocr_engine`, `imperial_guardian_match_threshold`, `imperial_guardian_ocr_algorithms`, `imperial_guardian_teaching_corner_x1/y1/x2/y2` |
| 5    | Thêm trường vào hàm from_dict() trong tool_manager           | `imperial_guardian_no_player_alert_delay` (default 10), `imperial_guardian_ocr_engine` (default "auto"), `imperial_guardian_match_threshold` (default 70.0), `imperial_guardian_ocr_algorithms` (default []), ROI fields (default 0) |
| 6    | ROI lưu riêng theo event, không dùng chung với action        | `imperial_guardian_teaching_corner_x1/y1/x2/y2`                               |
| 7    | Test: Lưu → đóng app → mở lại → kiểm tra giá trị còn đúng   | Giá trị Y, OCR engine, match_threshold, ocr_algorithms và ROI phải giữ nguyên |
