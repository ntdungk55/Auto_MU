# Manual Test Plan: User Input Detection

## Mục đích
Test tính năng phát hiện thao tác người dùng khi tool đang chạy.

---

## Test Case 1: Chế độ "Vẫn chạy" (Ignore)

**Mục đích:** Kiểm tra tool tiếp tục chạy khi người dùng thao tác

**Điều kiện tiên quyết:**
- Có tool với ít nhất 2 actions (ví dụ: WAIT 5s + KEYBOARD)
- Đã chọn target window

**Các bước thực hiện:**
1. Mở Tool Settings
2. Trong phần "Khi người dùng thao tác chuột/bàn phím", chọn "Vẫn chạy (bỏ qua)"
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Trong khi tool đang chạy, click chuột vào target window
6. Quan sát log

**Kết quả mong đợi:**
- Tool tiếp tục chạy bình thường
- Không có log "[UserInput]" xuất hiện (vì mode = ignore)

---

## Test Case 2: Chế độ "Tạm dừng" (Pause)

**Mục đích:** Kiểm tra tool tạm dừng khi người dùng thao tác

**Điều kiện tiên quyết:**
- Có tool với action WAIT 10s hoặc lâu hơn
- Đã chọn target window

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Tạm dừng" và đặt thời gian = 5 giây
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Trong khi tool đang chạy, click chuột vào target window
6. Quan sát log và trạng thái tool

**Kết quả mong đợi:**
- Log hiển thị: "[UserInput] Detected mouse input from user"
- Log hiển thị: "[UserInput] Pausing for 5s"
- Tool tạm dừng
- Sau 5 giây, log hiển thị: "[UserInput] Resuming after pause"
- Tool tiếp tục chạy từ step đang dừng

---

## Test Case 3: Chế độ "Dừng hẳn" (Stop)

**Mục đích:** Kiểm tra tool dừng hoàn toàn khi người dùng thao tác

**Điều kiện tiên quyết:**
- Có tool với action WAIT 10s hoặc lâu hơn
- Đã chọn target window

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Dừng hẳn"
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Trong khi tool đang chạy, click chuột vào target window
6. Quan sát log và trạng thái tool

**Kết quả mong đợi:**
- Log hiển thị: "[UserInput] Detected mouse input from user"
- Log hiển thị: "[UserInput] Stopping tool due to user input"
- Tool dừng hoàn toàn (status = Stopped)
- Nhấn F5 sẽ chạy lại từ đầu

---

## Test Case 4: Keyboard Input Detection

**Mục đích:** Kiểm tra phát hiện thao tác bàn phím

**Điều kiện tiên quyết:**
- Có tool với action WAIT 10s
- Đã chọn target window
- Target window đang được focus

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Dừng hẳn"
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Focus vào target window
6. Nhấn một phím bất kỳ (ví dụ: Space)
7. Quan sát log

**Kết quả mong đợi:**
- Log hiển thị: "[UserInput] Detected keyboard input from user"
- Tool dừng

---

## Test Case 5: Tool Actions Không Trigger Detection

**Mục đích:** Kiểm tra tool click/keyboard không bị nhận nhầm là user input

**Điều kiện tiên quyết:**
- Có tool với action MOUSE_CLICK hoặc KEYBOARD
- Đã chọn target window

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Dừng hẳn"
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Để tool tự thực hiện click/keyboard
6. Quan sát log

**Kết quả mong đợi:**
- Tool thực hiện click/keyboard thành công
- KHÔNG có log "[UserInput] Detected..." xuất hiện
- Tool tiếp tục chạy bình thường

---

## Test Case 6: Settings Persistence

**Mục đích:** Kiểm tra settings được lưu và load đúng

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Tạm dừng" với thời gian = 10 giây
3. Nhấn OK để lưu
4. Đóng ứng dụng hoàn toàn
5. Mở lại ứng dụng
6. Mở Tool Settings của tool đó

**Kết quả mong đợi:**
- Radio button "Tạm dừng" được chọn
- SpinBox hiển thị 10 giây

---

## Test Case 7: Click Ngoài Target Window

**Mục đích:** Kiểm tra click ngoài target window không trigger detection

**Các bước thực hiện:**
1. Mở Tool Settings
2. Chọn "Dừng hẳn"
3. Nhấn OK để lưu
4. Chạy tool (F5)
5. Click chuột vào một window khác (không phải target window)
6. Quan sát log

**Kết quả mong đợi:**
- KHÔNG có log "[UserInput]" xuất hiện
- Tool tiếp tục chạy bình thường

---

## Lưu ý
- Cần cài đặt thư viện `pynput` để tính năng hoạt động
- Nếu pynput không khả dụng, log sẽ hiển thị: "[UserInput] pynput not available, detection disabled"
- Tính năng chỉ hoạt động khi mode không phải "ignore"
