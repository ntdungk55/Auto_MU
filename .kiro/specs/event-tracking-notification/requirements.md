# Event Tracking Notification - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**
Người chơi game thường bỏ lỡ các sự kiện quan trọng xuất hiện trên màn hình vì không thể theo dõi liên tục. Các thông báo sự kiện xuất hiện ngắn và có thể biến mất trước khi người chơi kịp phản ứng.

**Mục tiêu:**
Tạo hệ thống tự động theo dõi thông báo sự kiện trên màn hình game, phát hiện thông báo mới khớp với pattern đã định nghĩa, và gửi cảnh báo qua Telegram sau một khoảng thời gian delay. Mỗi thông báo khác nhau chỉ được gửi 1 lần trong khoảng Reset Interval để tránh spam.

**Input/Output:**

| Loại | Mô tả | Ví dụ |
|------|-------|-------|
| Input | Thông báo sự kiện trên màn hình (OCR từ vùng ROI) | "Boss Rồng sẽ bắt đầu sau 5 phút" |
| Input | OCR Pattern với placeholder | "{event_name} sẽ bắt đầu sau {minutes} phút" |
| Input | Match Threshold (độ khớp) | 85% |
| Input | Delay Threshold (thời gian chờ) | 180 giây |
| Input | Reset Interval (thời gian reset duplicate) | 15 phút |
| Output | Thông báo Telegram | "Sự kiện Boss Rồng vẫn đang diễn ra" |

**Parameters (Tham số):**

| Tham số | Kiểu | Mô tả | Giá trị mặc định |
|---------|------|-------|------------------|
| OCR Pattern | Text | Mẫu text để nhận diện thông báo (có placeholder) | "{event_name} sẽ bắt đầu sau {minutes} phút" |
| Match Threshold | Số (0-100%) | Độ khớp tối thiểu giữa OCR và pattern | 100% |
| Delay Threshold | Số (giây) | Thời gian chờ trước khi gửi Telegram | 0 giây |
| Reset Interval | Số (phút) | Khoảng thời gian reset duplicate (0 = không reset) | 15 phút |
| Telegram Message | Text | Nội dung thông báo gửi Telegram (có placeholder) | "Sự kiện {event_name} vẫn đang diễn ra" |
| ROI Coordinates | Tọa độ (x, y, w, h) | Vùng màn hình để đọc thông báo (từ Teaching image) | (Tự động từ Teaching) |
| OCR Preprocessing | Danh sách thuật toán | Các thuật toán tiền xử lý ảnh trước OCR | (Tùy chọn) |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```
┌─────────────────────────────────┐
│  Bắt đầu: Chế độ Event Tracking │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│  Bước 1: Đọc OCR từ vùng ROI    │
└────────────┬────────────────────┘
             │
             ▼
        ┌────┴─────┐
        │ Có text  │
        │ khớp     │
        │ pattern? │
        └─┬─────┬──┘
          │     │
       YES│     │NO (quay lại Bước 1)
          │     │
          ▼     └──────────────────┐
┌─────────────────────────────┐   │
│ Bước 2: Trích xuất biến     │   │
│ ({event_name}, {minutes})   │   │
└────────────┬────────────────┘   │
             │                     │
             ▼                     │
        ┌────┴─────┐               │
        │ Thông báo│               │
        │ này đã   │               │
        │ gửi rồi? │               │
        └─┬─────┬──┘               │
          │     │                  │
       YES│     │NO                │
          │     │                  │
          │     ▼                  │
          │  ┌──────────────────┐ │
          │  │ Bước 3: Chờ      │ │
          │  │ delay_threshold  │ │
          │  └────────┬─────────┘ │
          │           │            │
          │           ▼            │
          │  ┌──────────────────┐ │
          │  │ Bước 4: Gửi      │ │
          │  │ Telegram         │ │
          │  └────────┬─────────┘ │
          │           │            │
          │           ▼            │
          │  ┌──────────────────┐ │
          │  │ Bước 5: Lưu vào  │ │
          │  │ danh sách đã gửi │ │
          │  └────────┬─────────┘ │
          │           │            │
          └───────┬───┘            │
                  │                │
                  ▼                ▼
           ┌──────────────────────────┐
           │ Quay lại Bước 1          │
           └──────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Đọc OCR từ vùng ROI**
- Input: Vùng ROI từ Teaching image (teaching_corner_x1, y1, x2, y2), OCR preprocessing algorithms (tùy chọn)
- Process: 
  - Sử dụng ROI coordinates từ Teaching image (đã được crop khi tạo teaching image)
  - Capture screenshot từ vùng ROI
  - Áp dụng preprocessing algorithms nếu có (upscale, contrast, sharpen, denoise)
  - Đọc text bằng OCR engine (WinRT hoặc Tesseract)
  - Parse từng dòng text riêng biệt (nếu multi-line)
- Output: Text OCR (có thể nhiều dòng)

**Bước 2: Trích xuất biến từ pattern**
- Input: Text OCR, OCR Pattern với placeholder
- Process:
  - Convert OCR Pattern thành regex (thay {event_name} → (.+?), {minutes} → (\d+))
  - So khớp từng dòng text với regex
  - Nếu Match Threshold < 100%, sử dụng fuzzy matching
  - Trích xuất giá trị từ các placeholder
- Output: Dictionary với các giá trị đã trích xuất (ví dụ: {"event_name": "Boss Rồng", "minutes": "5"})

**Bước 3: Kiểm tra duplicate**
- Input: Thông báo đã trích xuất, danh sách thông báo đã gửi, Reset Interval
- Process:
  - So sánh text thông báo với danh sách đã gửi (exact string comparison)
  - Nếu tìm thấy duplicate:
    - Kiểm tra thời gian: (now - last_sent_time)
    - Nếu Reset Interval = 0 → Bỏ qua mãi mãi
    - Nếu Reset Interval > 0 và chưa đủ thời gian → Bỏ qua tạm thời
    - Nếu Reset Interval > 0 và đã quá thời gian → Coi như thông báo mới
  - Nếu không tìm thấy duplicate → Tiếp tục Bước 3
- Output: Decision (skip hoặc continue)

**Bước 3: Chờ delay_threshold**
- Input: Delay Threshold (giây)
- Process:
  - Nếu Delay Threshold = 0 → Bỏ qua bước này
  - Nếu Delay Threshold > 0 → Sleep delay_threshold giây
- Output: None (chỉ chờ)

**Bước 4: Gửi Telegram**
- Input: Telegram Message template, các giá trị đã trích xuất, Telegram Bot Token, Chat ID
- Process:
  - Thay thế các placeholder trong Telegram Message bằng giá trị đã trích xuất
  - Gửi message qua Telegram API
  - Nếu fail → Retry 3 lần với delay 1 giây giữa các lần
  - Nếu vẫn fail sau 3 lần → Log error và bỏ qua
- Output: Success hoặc Failure

**Bước 5: Lưu vào danh sách đã gửi**
- Input: Thông báo đã gửi thành công, timestamp hiện tại
- Process:
  - Lưu text thông báo và timestamp vào danh sách đã gửi (in-memory)
  - Danh sách này không persist qua các lần chạy tool
- Output: Danh sách đã gửi được cập nhật

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: OCR trả về nhiều dòng text**
- Xử lý: Parse từng dòng riêng biệt, nếu BẤT KỲ dòng nào khớp pattern → Chấp nhận

**Case 2: OCR không đọc được text (trả về rỗng)**
- Xử lý: Log warning, bỏ qua và quay lại Bước 1

**Case 3: Text OCR không khớp pattern**
- Xử lý: Bỏ qua và quay lại Bước 1

**Case 4: Delay Threshold = 0**
- Xử lý: Gửi Telegram ngay lập tức, không chờ

**Case 5: Reset Interval = 0**
- Xử lý: Mỗi thông báo chỉ gửi 1 lần duy nhất, không bao giờ gửi lại

**Case 6: Gửi Telegram thất bại sau 3 lần retry**
- Xử lý: Log error, bỏ qua thông báo này, KHÔNG lưu vào danh sách đã gửi

**Case 7: Match Threshold < 100%**
- Xử lý: Sử dụng fuzzy matching, chấp nhận text OCR khớp một phần với pattern
**Case 8: ROI chưa được teaching (Teaching image chưa có)**
- Xử lý: Hiển thị lỗi validation khi save, không cho chạy action
- Xử lý: Hiển thị lỗi validation khi save, không cho chạy action

**Case 9: Telegram chưa được cấu hình**
- Xử lý: Hiển thị lỗi validation khi save, không cho chạy action

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: OCR engine không khả dụng**
- Nguyên nhân: WinRT và Tesseract đều không hoạt động
- Xử lý: Log error, hiển thị thông báo lỗi cho user, dừng action

**Lỗi 2: Không thể capture screenshot**
- Nguyên nhân: Window không tồn tại, quyền truy cập bị từ chối
- Xử lý: Log error, retry 3 lần, nếu vẫn fail → dừng action

**Lỗi 3: Telegram API trả về lỗi**
- Nguyên nhân: Bot Token sai, Chat ID sai, mất kết nối internet
- Xử lý: Log error, retry 3 lần với delay 1 giây, nếu vẫn fail → bỏ qua thông báo này

**Lỗi 4: Không thể parse giá trị từ text OCR**
- Nguyên nhân: Text OCR không khớp pattern, regex không match
- Xử lý: Log debug message, bỏ qua và quay lại Bước 1

**Lỗi 5: Reset Interval < 0**
- Nguyên nhân: User nhập giá trị âm
- Xử lý: Hiển thị lỗi validation trong UI, không cho save

**Lỗi 6: OCR Pattern hoặc Telegram Message trống**
- Nguyên nhân: User không nhập giá trị
- Xử lý: Hiển thị lỗi validation trong UI, không cho save

---

## 4. PHÁC THẢO UI (nếu có)
```
┌─────────────────────────────────────────────────────────────┐
│  Passive Read Settings                                [X]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  🔄 Chế độ hoạt động                                        │
│  Chế độ: [Đọc dữ liệu ▼]                                   │
│          [Phát hiện hình ảnh]                               │
│          [Event Tracking]  ← CHẾ ĐỘ MỚI                    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│  KHI CHỌN "Event Tracking":                                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔍 Pattern Matching                                 │   │
│  │                                                      │   │
│  │  OCR Pattern:                                        │   │
│  │  [{event_name} sẽ bắt đầu sau {minutes} phút      ] │   │
│  │                                                      │   │
│  │  Match Threshold: [100] %                           │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 📱 Notification Settings                            │   │
│  │                                                      │   │
│  │  Delay Threshold: [180] seconds                     │   │
│  │                                                      │   │
│  │  Reset Interval: [15] minutes (0 = never reset)    │   │
│  │                                                      │   │
│  │  Telegram Message:                                   │   │
│  │  [Sự kiện {event_name} vẫn đang diễn ra          ] │   │
│  │                                                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  📍 ROI: Sử dụng vùng từ Teaching image                    │
│                                                              │
│                                    [Save]  [Cancel]         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Mô tả các thành phần:**

- **Chế độ dropdown**: Chọn 1 trong 3 chế độ:
  - "Đọc dữ liệu" (mode 1 - hiện tại)
  - "Phát hiện hình ảnh" (mode 2 - hiện tại)
  - "Event Tracking" (mode 3 - MỚI)
- **OCR Pattern input**: Nhập pattern với placeholder để nhận diện thông báo
- **Match Threshold spinbox**: Điều chỉnh độ khớp (0-100%)
- **Delay Threshold spinbox**: Thời gian chờ trước khi gửi Telegram (giây)
- **Reset Interval spinbox**: Khoảng thời gian reset duplicate (phút, 0 = không reset)
- **Telegram Message input**: Nhập template message gửi Telegram
- **ROI note**: Thông báo rằng ROI được lấy từ Teaching image (không cần button Set ROI riêng)
- **Save button**: Lưu settings và validate
- **Cancel button**: Đóng dialog không lưu

**Lưu ý:** 
- Khi chọn "Event Tracking", chỉ hiển thị các settings liên quan đến Event Tracking
- ROI được lấy tự động từ Teaching image (teaching_corner_x1, y1, x2, y2)
- Không cần button "Set ROI" riêng vì Teaching image section đã có chức năng crop ROI
- **Cancel button**: Đóng dialog không lưu

**Lưu ý:** 
- Teaching image section và Selected Algorithms list hiển thị cho TẤT CẢ modes (common)
- Khi chọn "Event Tracking", chỉ hiển thị Event Tracking Settings (ROI, Pattern, Thresholds, Telegram Message)
- OCR algorithms được cấu hình qua button "🧪 Test Algorithms" trong Teaching section, áp dụng cho tất cả modes
ok