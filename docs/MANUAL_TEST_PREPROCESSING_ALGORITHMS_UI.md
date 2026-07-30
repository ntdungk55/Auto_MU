# Manual Test Plan: Preprocessing Algorithms UI

## Test Case 1: Template Matching Algorithms Configuration

**Mục đích:** Kiểm tra việc cấu hình preprocessing algorithms cho template matching

**Điều kiện tiên quyết:**
- App đã khởi động
- Có ít nhất 1 tool với IMAGE_DETECT action
- Multi-Image Algorithm Testing Dialog hoạt động bình thường

**Các bước thực hiện:**
1. Mở Tool Editor Window
2. Chọn một tool có IMAGE_DETECT action
3. Double-click vào IMAGE_DETECT action để mở Image Detect Settings Dialog
4. Kiểm tra Template Matching Preprocessing section xuất hiện
5. Kiểm tra ListView hiển thị "Không có thuật toán" (nếu chưa có algorithms)
6. Click button "⚙️ Cấu hình Template Matching Algorithms"
7. Multi-Image Algorithm Testing Dialog mở ra
8. Thêm một số algorithms (ví dụ: Upscale 2x, Enhance Contrast)
9. Click button "📤 Apply to Template Matching"
10. Đóng Multi-Image Testing Dialog
11. Kiểm tra ListView trong Image Detect Settings Dialog đã cập nhật
12. Click OK để save settings
13. Đóng và mở lại Image Detect Settings Dialog
14. Kiểm tra algorithms vẫn được hiển thị

**Kết quả mong đợi:**
- Template Matching Preprocessing section xuất hiện sau Teaching Image section
- ListView hiển thị "Không có thuật toán" khi empty
- Button "⚙️ Cấu hình Template Matching Algorithms" hoạt động
- Multi-Image Testing Dialog mở được
- Apply to Template Matching button hoạt động
- ListView cập nhật hiển thị algorithms với format "Algorithm_Name (param1: value1, param2: value2)"
- Data persistence hoạt động (algorithms vẫn có sau khi đóng/mở lại)

**Cài đặt cần kiểm tra:**
- template_matching_algorithms field trong action
- ListView height tối đa 120px
- Scroll bar xuất hiện khi cần

---

## Test Case 2: OCR Algorithms Configuration

**Mục đích:** Kiểm tra việc cấu hình preprocessing algorithms cho OCR mode

**Điều kiện tiên quyết:**
- App đã khởi động
- Có ít nhất 1 tool với READ_PASSIVE action
- Multi-Image Algorithm Testing Dialog hoạt động bình thường

**Các bước thực hiện:**
1. Mở Tool Editor Window
2. Chọn một tool có READ_PASSIVE action
3. Double-click vào READ_PASSIVE action để mở Passive Read Settings Dialog
4. Chọn passive mode = "Đọc dữ liệu" (index 0)
5. Kiểm tra OCR Preprocessing section xuất hiện trong left column
6. Kiểm tra ListView hiển thị "Không có thuật toán" (nếu chưa có algorithms)
7. Click button "⚙️ Cấu hình OCR Algorithms"
8. Multi-Image Algorithm Testing Dialog mở ra
9. Thêm một số algorithms (ví dụ: Enhance Contrast, Sharpen)
10. Click button "📤 Apply to OCR Mode"
11. Đóng Multi-Image Testing Dialog
12. Kiểm tra ListView trong Passive Read Settings Dialog đã cập nhật
13. Thay đổi passive mode sang "Phát hiện hình ảnh" (index 1)
14. Kiểm tra OCR Preprocessing section bị ẩn
15. Thay đổi lại về "Đọc dữ liệu" (index 0)
16. Kiểm tra OCR Preprocessing section hiện lại với algorithms
17. Click OK để save settings
18. Đóng và mở lại Passive Read Settings Dialog
19. Kiểm tra algorithms vẫn được hiển thị

**Kết quả mong đợi:**
- OCR Preprocessing section xuất hiện trong left column khi mode = "Đọc dữ liệu"
- OCR Preprocessing section bị ẩn khi mode = "Phát hiện hình ảnh"
- ListView hiển thị "Không có thuật toán" khi empty
- Button "⚙️ Cấu hình OCR Algorithms" hoạt động
- Multi-Image Testing Dialog mở được
- Apply to OCR Mode button hoạt động
- ListView cập nhật hiển thị algorithms với format "Algorithm_Name (param1: value1, param2: value2)"
- Data persistence hoạt động (algorithms vẫn có sau khi đóng/mở lại)

**Cài đặt cần kiểm tra:**
- ocr_algorithms field trong action
- ListView height tối đa 120px
- Visibility logic dựa trên passive mode

---

## Test Case 3: Algorithm Display Format

**Mục đích:** Kiểm tra format hiển thị algorithms trong ListView

**Điều kiện tiên quyết:**
- Đã có algorithms được configure từ Test Case 1 hoặc 2

**Các bước thực hiện:**
1. Mở Image Detect Settings Dialog có template_matching_algorithms
2. Kiểm tra format hiển thị trong ListView:
   - Algorithm có parameters: "Upscale 2x (Scale Factor: 2.0)"
   - Algorithm không có parameters: "Grayscale Only"
   - Multiple parameters: "Complex Algorithm (param1: value1, param2: value2)"
3. Mở Passive Read Settings Dialog có ocr_algorithms
4. Kiểm tra format hiển thị tương tự
5. Thêm nhiều algorithms để test scroll behavior
6. Kiểm tra scroll bar xuất hiện khi ListView height > 120px

**Kết quả mong đợi:**
- Algorithms với parameters hiển thị format "Name (param1: value1, param2: value2)"
- Algorithms không có parameters hiển thị chỉ "Name"
- Multiple parameters được phân tách bởi dấu phẩy
- ListView có scroll bar khi cần
- Mỗi algorithm trên một dòng riêng

**Cài đặt cần kiểm tra:**
- format_algorithm_display() function hoạt động đúng
- update_algorithms_display() function hoạt động đúng
- ListView scroll behavior

---

## Test Case 4: Multi-Image Testing Dialog Integration

**Mục đích:** Kiểm tra integration với Multi-Image Algorithm Testing Dialog

**Điều kiện tiên quyết:**
- Multi-Image Algorithm Testing Dialog hoạt động bình thường
- Có window target để test algorithms

**Các bước thực hiện:**
1. Mở Multi-Image Algorithm Testing Dialog từ Image Detect Settings
2. Kiểm tra có 2 Apply buttons: "📤 Apply to Template Matching" và "📤 Apply to OCR Mode"
3. Thêm algorithms vào danh sách
4. Click "📤 Apply to Template Matching"
5. Kiểm tra thông báo success xuất hiện
6. Đóng dialog và kiểm tra algorithms đã được apply
7. Mở Multi-Image Algorithm Testing Dialog từ Passive Read Settings
8. Thêm algorithms khác vào danh sách
9. Click "📤 Apply to OCR Mode"
10. Kiểm tra thông báo success xuất hiện
11. Đóng dialog và kiểm tra algorithms đã được apply
12. Kiểm tra 2 loại algorithms (template_matching vs ocr) độc lập với nhau

**Kết quả mong đợi:**
- Apply buttons xuất hiện trong Multi-Image Testing Dialog
- Apply to Template Matching chỉ ảnh hưởng template_matching_algorithms
- Apply to OCR Mode chỉ ảnh hưởng ocr_algorithms
- Success messages hiển thị khi apply thành công
- 2 loại algorithms hoàn toàn độc lập

**Cài đặt cần kiểm tra:**
- _apply_to_template_matching() method
- _apply_to_ocr_mode() method
- _get_current_algorithms() method
- Algorithm data integrity

---

## Test Case 5: Data Persistence End-to-End

**Mục đích:** Kiểm tra data persistence hoàn chỉnh từ UI đến JSON file

**Điều kiện tiên quyết:**
- Đã configure algorithms từ các test cases trước

**Các bước thực hiện:**
1. Configure template_matching_algorithms cho một IMAGE_DETECT action
2. Configure ocr_algorithms cho một READ_PASSIVE action
3. Save tool (Ctrl+S trong Tool Editor)
4. Đóng Tool Editor Window
5. Đóng hoàn toàn app
6. Mở lại app
7. Load tool vừa save
8. Mở Image Detect Settings Dialog
9. Kiểm tra template_matching_algorithms vẫn hiển thị đúng
10. Mở Passive Read Settings Dialog
11. Kiểm tra ocr_algorithms vẫn hiển thị đúng
12. Kiểm tra JSON file trong tools/ folder
13. Verify template_matching_algorithms và ocr_algorithms fields có trong JSON

**Kết quả mong đợi:**
- Algorithms configuration được lưu khi save tool
- Algorithms configuration được load khi mở tool
- JSON file chứa template_matching_algorithms và ocr_algorithms fields
- Data integrity được maintain qua save/load cycle
- Backward compatibility với tools không có algorithms fields

**Cài đặt cần kiểm tra:**
- ToolManager._action_to_dict() method
- ToolManager.from_dict() method
- JSON serialization/deserialization
- Backward compatibility

---

## Test Case 6: Error Handling và Edge Cases

**Mục đích:** Kiểm tra xử lý lỗi và các trường hợp đặc biệt

**Điều kiện tiên quyết:**
- App hoạt động bình thường

**Các bước thực hiện:**
1. Mở settings dialog khi chưa có algorithms
2. Kiểm tra hiển thị "Không có thuật toán"
3. Try apply empty algorithms list từ Multi-Image Testing Dialog
4. Kiểm tra xử lý graceful
5. Configure algorithms rồi clear hết
6. Kiểm tra ListView quay về "Không có thuật toán"
7. Test với algorithms có invalid parameters structure
8. Kiểm tra validation hoạt động
9. Test với very long algorithm names
10. Kiểm tra UI layout không bị break

**Kết quả mong đợi:**
- "Không có thuật toán" hiển thị khi empty
- Empty algorithms list được xử lý đúng
- Invalid algorithms được validate và reject
- UI layout stable với long names
- No crashes hoặc exceptions

**Cài đặt cần kiểm tra:**
- validate_algorithm() function
- validate_algorithms_list() function
- Error handling trong UI
- Edge case handling

---

## Acceptance Criteria Summary

Tất cả test cases phải pass để feature được accept:

✅ Template Matching Algorithms UI hoạt động đúng
✅ OCR Algorithms UI hoạt động đúng với visibility logic
✅ Algorithm display format chính xác
✅ Multi-Image Testing Dialog integration hoạt động
✅ Data persistence end-to-end hoạt động
✅ Error handling và edge cases được xử lý

## Performance Notes

- ListView với 120px height không gây lag
- Scroll behavior smooth với nhiều algorithms
- Dialog open/close performance không bị ảnh hưởng
- JSON serialization/deserialization không chậm