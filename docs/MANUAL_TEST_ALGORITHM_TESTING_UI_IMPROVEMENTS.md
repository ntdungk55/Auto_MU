# Manual Test Plan: Algorithm Testing UI Improvements

## Mục đích
Test các cải tiến UI cho Multi-Image Algorithm Testing Dialog:
1. Dialog có thể maximize toàn màn hình
2. Scroll behavior mượt mà hơn cho các ListView
3. Algorithms được transfer về Action Settings khi đóng dialog

---

## Test Case 1: Dialog Maximize Capability
**Mục đích:** Verify dialog có thể maximize và resize

**Điều kiện tiên quyết:**
- Có tool với action IMAGE_DETECT hoặc MOUSE_CLICK
- Action đã có teaching image

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action IMAGE_DETECT hoặc MOUSE_CLICK
3. Click "Cài đặt" để mở action settings dialog
4. Click "🧪 Test Algorithms" để mở Multi-Image Algorithm Testing Dialog
5. Thử resize dialog bằng cách kéo góc
6. Click nút maximize trên title bar
7. Thử minimize và restore lại

**Kết quả mong đợi:**
- Dialog có thể resize freely
- Maximize button hoạt động, dialog chiếm toàn màn hình
- Minimize/restore hoạt động bình thường
- UI components vẫn hiển thị đúng khi resize

---

## Test Case 2: Smooth Scrolling for Window Captures List
**Mục đích:** Verify scroll behavior mượt mà cho captures list

**Điều kiện tiên quyết:**
- Dialog Multi-Image Algorithm Testing đã mở
- Có ít nhất 10 window captures trong list

**Các bước thực hiện:**
1. Load nhiều images hoặc capture nhiều screenshots để có > 10 items
2. Thử scroll bằng mouse wheel trong captures list
3. Thử scroll bằng scroll bar
4. Thử drag scroll bar thumb

**Kết quả mong đợi:**
- Scroll bằng mouse wheel: mỗi lần scroll chỉ di chuyển 5 pixels (mượt mà)
- Scroll bar hoạt động mượt mà, không nhảy cóc
- Page scroll (click vào scroll bar track) di chuyển 50 pixels

**Cài đặt cần kiểm tra:**
- ScrollMode: ScrollPerPixel
- SingleStep: 5 pixels
- PageStep: 50 pixels

---

## Test Case 3: Smooth Scrolling for Algorithms List
**Mục đích:** Verify scroll behavior mượt mà cho algorithms list

**Điều kiện tiên quyết:**
- Dialog Multi-Image Algorithm Testing đã mở
- Có ít nhất 8 algorithms trong list

**Các bước thực hiện:**
1. Add nhiều algorithms vào list (ít nhất 8 algorithms)
2. Thử scroll bằng mouse wheel trong algorithms list
3. Thử scroll bằng scroll bar
4. Expand/collapse parameter settings của các algorithms

**Kết quả mong đợi:**
- Scroll bằng mouse wheel: mỗi lần scroll chỉ di chuyển 3 pixels (rất mượt)
- Scroll bar hoạt động mượt mà
- Page scroll di chuyển 30 pixels
- Parameter widgets expand/collapse không làm scroll jump

**Cài đặt cần kiểm tra:**
- ScrollMode: ScrollPerPixel
- SingleStep: 3 pixels
- PageStep: 30 pixels

---

## Test Case 4: Algorithm Transfer to Image Detect Settings
**Mục đích:** Verify algorithms được transfer về Image Detect Settings khi đóng dialog

**Điều kiện tiên quyết:**
- Có tool với action IMAGE_DETECT
- Action đã có teaching image

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action IMAGE_DETECT
3. Click "Cài đặt" để mở Image Detect Settings Dialog
4. Scroll xuống section "⚙️ Template Matching Preprocessing"
5. Verify list algorithms hiện tại (có thể empty)
6. Click "⚙️ Cấu hình Template Matching Algorithms"
7. Trong Multi-Image Algorithm Testing Dialog:
   - Add 2-3 algorithms (ví dụ: Upscale 2x, Enhance Contrast, Sharpen)
   - Configure parameters nếu cần
8. Click "✅ OK" để đóng dialog
9. Verify popup message "Đã áp dụng X algorithms vào Action Settings!"
10. Quay lại Image Detect Settings Dialog
11. Check section "⚙️ Template Matching Preprocessing"

**Kết quả mong đợi:**
- Popup message hiển thị số algorithms đã transfer
- Template Matching Preprocessing section hiển thị đúng algorithms đã add
- Algorithms được save vào action.template_matching_algorithms
- Khi save action và reload, algorithms vẫn persist

---

## Test Case 5: Algorithm Transfer to Mouse Click Settings
**Mục đích:** Verify algorithms được transfer về Mouse Click Settings khi đóng dialog

**Điều kiện tiên quyết:**
- Có tool với action MOUSE_CLICK
- Action đã có teaching image

**Các bước thực hiện:**
1. Mở Tool Editor
2. Chọn action MOUSE_CLICK
3. Click "Cài đặt" để mở Mouse Click Settings Dialog
4. Scroll xuống section "⚙️ Template Matching Preprocessing"
5. Verify list algorithms hiện tại (có thể empty)
6. Click "⚙️ Cấu hình Template Matching Algorithms"
7. Trong Multi-Image Algorithm Testing Dialog:
   - Add 2-3 algorithms khác với Test Case 4
   - Configure parameters khác nhau
8. Click "✅ OK" để đóng dialog
9. Verify popup message
10. Check Template Matching Preprocessing section

**Kết quả mong đợi:**
- Tương tự Test Case 4 nhưng cho Mouse Click Settings
- Algorithms được save riêng biệt cho từng action

---

## Test Case 6: No Algorithm Transfer When Cancel
**Mục đích:** Verify algorithms KHÔNG được transfer khi cancel dialog

**Điều kiện tiên quyết:**
- Có action với existing algorithms trong Template Matching Preprocessing

**Các bước thực hiện:**
1. Mở action settings dialog có existing algorithms
2. Note down số algorithms hiện tại
3. Click "⚙️ Cấu hình Template Matching Algorithms"
4. Add thêm 2-3 algorithms mới
5. Click "❌ Close" thay vì "✅ OK"
6. Quay lại action settings dialog
7. Check Template Matching Preprocessing section

**Kết quả mong đợi:**
- KHÔNG có popup message
- Template Matching Preprocessing section vẫn giữ nguyên algorithms cũ
- Algorithms mới KHÔNG được save

---

## Test Case 7: Algorithm Transfer with No Parent
**Mục đích:** Verify dialog hoạt động bình thường khi không có parent dialog

**Điều kiện tiên quyết:**
- Có thể mở dialog trực tiếp (qua debug hoặc test)

**Các bước thực hiện:**
1. Mở Multi-Image Algorithm Testing Dialog mà không qua action settings
2. Add algorithms
3. Click "✅ OK"

**Kết quả mong đợi:**
- Dialog không crash
- Algorithms được save vào action.preprocessing_algorithms
- Không có popup message (vì không có parent)

---

## Test Case 8: UI Responsiveness When Maximized
**Mục đích:** Verify UI components scale properly khi maximize

**Điều kiện tiên quyết:**
- Dialog Multi-Image Algorithm Testing đã mở

**Các bước thực hiện:**
1. Maximize dialog
2. Check tất cả UI components:
   - Teaching image preview
   - Window capture preview
   - Captures list
   - Algorithms list
   - Buttons
   - Progress bar
3. Thử resize dialog về kích thước nhỏ hơn
4. Check UI components vẫn accessible

**Kết quả mong đợi:**
- Preview areas scale properly và maintain aspect ratio
- Lists không quá rộng (có max width)
- Buttons giữ nguyên size, không stretch
- Scroll bars xuất hiện khi cần
- Tất cả components vẫn accessible ở mọi size

---

## Lưu ý quan trọng

### Performance
- Dialog phải mở nhanh ngay cả khi maximize
- Scroll phải mượt mà không lag
- Algorithm transfer phải instant

### Usability
- User có thể dễ dàng thấy nhiều window captures cùng lúc khi maximize
- Scroll behavior phải predictable và comfortable
- Success message phải rõ ràng về số algorithms đã transfer

### Data Integrity
- Algorithms phải được save đúng format
- Không được mất data khi resize/maximize
- Cancel phải thực sự cancel, không save gì cả

### Error Handling
- Dialog không crash khi parent bị close trước
- Graceful handling khi không có parent
- Proper cleanup khi dialog close