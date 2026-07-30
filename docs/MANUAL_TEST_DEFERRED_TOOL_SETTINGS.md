# Manual Test Plan: Deferred Tool Settings

## Test Case 1: Save Settings Without Restart (Loop Tool)

**Mục đích:** Kiểm tra rằng thay đổi setting không restart tool đang chạy

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy (đang ở giữa chu kỳ)

**Các bước thực hiện:**
1. Tạo tool với 3 actions, loop enabled, loop count = 3
2. Start tool
3. Đợi tool chạy đến giữa chu kỳ 1 (ví dụ: đang ở action 2/3)
4. Click nút "Setting"
5. Thay đổi loop count = 5
6. Click OK

**Kết quả mong đợi:**
- Tool KHÔNG bị restart
- Chu kỳ 1 tiếp tục chạy đến hết (action 3/3)
- Chu kỳ 1 kết thúc bình thường
- Chu kỳ 2 bắt đầu
- Tool chạy tổng cộng 5 chu kỳ (không phải 3)

**Cài đặt cần kiểm tra:**
- Loop enabled: True
- Loop count: 3 → 5
- Loop mode: count

---

## Test Case 2: Apply Settings on Next Cycle

**Mục đích:** Kiểm tra rằng setting mới chỉ áp dụng từ chu kỳ tiếp theo

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với loop pre delay = 1s, loop post delay = 1s
2. Start tool
3. Đợi chu kỳ 1 bắt đầu
4. Click "Setting" ngay sau khi chu kỳ 1 bắt đầu
5. Thay đổi loop pre delay = 5s, loop post delay = 5s
6. Click OK
7. Quan sát thời gian delay của chu kỳ 1 và chu kỳ 2

**Kết quả mong đợi:**
- Chu kỳ 1: pre delay = 1s, post delay = 1s (setting cũ)
- Chu kỳ 2: pre delay = 5s, post delay = 5s (setting mới)

**Cài đặt cần kiểm tra:**
- Loop pre delay: 1s → 5s
- Loop post delay: 1s → 5s

---

## Test Case 3: Multiple Settings Changes in Same Cycle

**Mục đích:** Kiểm tra rằng nhiều lần thay đổi setting sẽ lấy giá trị cuối cùng

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với loop count = 3
2. Start tool
3. Trong chu kỳ 1:
   - Click "Setting", đổi loop count = 5, OK
   - Click "Setting", đổi loop count = 7, OK
   - Click "Setting", đổi loop count = 10, OK
4. Đợi chu kỳ 1 kết thúc
5. Đếm tổng số chu kỳ tool chạy

**Kết quả mong đợi:**
- Tool chạy tổng cộng 10 chu kỳ (giá trị cuối cùng)
- Không có thông báo hay confirmation nào

**Cài đặt cần kiểm tra:**
- Loop count: 3 → 5 → 7 → 10

---

## Test Case 4: Settings Change While Tool Paused

**Mục đích:** Kiểm tra rằng setting áp dụng khi tool resume

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với loop count = 3
2. Start tool
3. Đợi chu kỳ 1 hoàn thành
4. Pause tool (giữa chu kỳ 1 và 2)
5. Click "Setting", đổi loop count = 5, OK
6. Resume tool (F5)
7. Đếm tổng số chu kỳ

**Kết quả mong đợi:**
- Tool chạy tổng cộng 5 chu kỳ
- Setting mới áp dụng từ chu kỳ 2 (sau resume)

**Cài đặt cần kiểm tra:**
- Loop count: 3 → 5

---

## Test Case 5: Non-Loop Tool Settings

**Mục đích:** Kiểm tra rằng tool không lặp cũng reload settings đúng

**Điều kiện tiên quyết:**
- Tool có loop disabled
- Tool đã chạy xong

**Các bước thực hiện:**
1. Tạo tool với 2 actions, loop disabled
2. Start tool
3. Đợi tool chạy xong (stop)
4. Click "Setting", thêm 1 action nữa (tổng 3 actions), OK
5. Start tool lại
6. Quan sát số actions được thực thi

**Kết quả mong đợi:**
- Lần chạy thứ 2: tool thực thi 3 actions (không phải 2)

**Cài đặt cần kiểm tra:**
- Actions: 2 → 3
- Loop enabled: False

---

## Test Case 6: Settings Change for Different Setting Types

**Mục đích:** Kiểm tra rằng tất cả loại settings đều reload đúng

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với:
   - Loop count = 3
   - Loop pre delay = 1s
   - Loop post delay = 1s
   - Block input enabled = False
   - User input mode = "ignore"
2. Start tool
3. Trong chu kỳ 1, click "Setting" và thay đổi:
   - Loop count = 5
   - Loop pre delay = 2s
   - Loop post delay = 2s
   - Block input enabled = True
   - Block input duration = 3s
   - User input mode = "pause"
   - Pause duration = 10s
4. Click OK
5. Quan sát chu kỳ 2

**Kết quả mong đợi:**
- Chu kỳ 2 sử dụng tất cả settings mới:
  - Pre delay = 2s
  - Post delay = 2s
  - Input blocking enabled
  - User input detection = pause mode

**Cài đặt cần kiểm tra:**
- Tất cả tool-level settings

---

## Test Case 7: Settings Persistence Across App Restart

**Mục đích:** Kiểm tra rằng settings được save vào JSON file

**Điều kiện tiên quyết:**
- Tool có loop enabled
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với loop count = 3
2. Start tool
3. Trong chu kỳ 1, click "Setting", đổi loop count = 10, OK
4. Stop tool
5. Đóng app
6. Mở app lại
7. Load tool
8. Kiểm tra loop count

**Kết quả mong đợi:**
- Loop count = 10 (đã được save vào JSON)

**Cài đặt cần kiểm tra:**
- Loop count: 3 → 10
- File JSON: tools/[tool_name].json

---

## Test Case 8: Performance - No Lag When Changing Settings

**Mục đích:** Kiểm tra rằng thay đổi settings không gây lag

**Điều kiện tiên quyết:**
- Tool có nhiều actions (>50)
- Tool đang chạy

**Các bước thực hiện:**
1. Tạo tool với 50 actions
2. Start tool
3. Click "Setting"
4. Thay đổi bất kỳ setting nào
5. Click OK
6. Quan sát UI response time

**Kết quả mong đợi:**
- Dialog đóng ngay lập tức (< 100ms)
- Tool tiếp tục chạy mượt mà
- Không có freeze hay lag

**Cài đặt cần kiểm tra:**
- Response time < 100ms
