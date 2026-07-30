# Manual Test Plan: Algorithm Inline Parameters

## Test Case 1: Thêm Thuật Toán Threshold

**Mục đích:** Verify thuật toán Binary Threshold được thêm và hoạt động đúng

**Điều kiện tiên quyết:**
- Có teaching image đã được chọn
- Multi-Image Algorithm Testing Dialog đã mở

**Các bước thực hiện:**
1. Mở Multi-Image Algorithm Testing Dialog
2. Click vào Algorithm dropdown
3. Tìm và chọn "Binary Threshold" algorithm
4. Click "Add" để thêm vào list
5. Verify algorithm xuất hiện trong algorithms list
6. Check có parameters: threshold_value và threshold_type

**Kết quả mong đợi:**
- Binary Threshold algorithm có trong dropdown
- Algorithm được add vào list thành công
- Hiển thị parameters inline: threshold_value (0-255), threshold_type (BINARY/BINARY_INV)

**Cài đặt cần kiểm tra:**
- threshold_value: 127 (default)
- threshold_type: 0 (THRESH_BINARY)

---

## Test Case 2: Inline Parameter Editing

**Mục đích:** Verify có thể edit parameters ngay trong listview

**Điều kiện tiên quyết:**
- Đã add ít nhất 1 algorithm có parameters vào list

**Các bước thực hiện:**
1. Add "Upscale 2x" algorithm vào list
2. Verify hiển thị parameter "Scale Factor" với QDoubleSpinBox
3. Thay đổi Scale Factor từ 2.0 thành 3.5
4. Add "Binary Threshold" algorithm vào list
5. Verify hiển thị parameters "Threshold Value" và "Threshold Type"
6. Thay đổi Threshold Value từ 127 thành 100
7. Thay đổi Threshold Type từ BINARY thành BINARY_INV

**Kết quả mong đợi:**
- Mỗi algorithm hiển thị parameters inline
- Parameters có thể edit bằng spinbox/combobox
- Values được update ngay khi thay đổi
- UI tự động điều chỉnh height cho nhiều parameters

**Cài đặt cần kiểm tra:**
- Scale Factor: 1.0-5.0 range, step 0.1
- Threshold Value: 0-255 range, step 1
- Threshold Type: dropdown với BINARY/BINARY_INV options

---

## Test Case 3: Real-time Preview Update

**Mục đích:** Verify preview cập nhật real-time khi thay đổi parameters

**Điều kiện tiên quyết:**
- Có window capture đã load
- Đã add algorithm có parameters

**Các bước thực hiện:**
1. Load 1 window capture image
2. Select window capture trong list
3. Add "Upscale 2x" algorithm
4. Verify preview hiển thị ảnh với upscale 2x
5. Thay đổi Scale Factor thành 3.0
6. Verify preview tự động update với upscale 3x
7. Add "Binary Threshold" algorithm
8. Thay đổi Threshold Value và verify preview update

**Kết quả mong đợi:**
- Preview update ngay khi thay đổi parameter
- Ảnh hiển thị đúng với algorithm và parameters được áp dụng
- Không có lag hoặc freeze khi update

**Cài đặt cần kiểm tra:**
- Preview quality: smooth transformation
- Update speed: < 500ms
- Memory usage: không tăng liên tục

---

## Test Case 4: Parameter Validation

**Mục đích:** Verify parameter validation hoạt động đúng

**Điều kiện tiên quyết:**
- Đã add algorithms có parameters

**Các bước thực hiện:**
1. Add "Upscale 2x" algorithm
2. Try nhập Scale Factor = 10.0 (above max 5.0)
3. Verify value được clamp về 5.0
4. Try nhập Scale Factor = 0.5 (below min 1.0)
5. Verify value được clamp về 1.0
6. Add "Binary Threshold" algorithm
7. Try nhập Threshold Value = 300 (above max 255)
8. Verify value được clamp về 255
9. Try nhập Threshold Value = -10 (below min 0)
10. Verify value được clamp về 0

**Kết quả mong đợi:**
- Values ngoài range được tự động clamp
- Không crash hoặc error khi nhập invalid values
- UI feedback rõ ràng về valid range

**Cài đặt cần kiểm tra:**
- Min/Max enforcement: strict
- Step values: correct increments
- Decimal places: appropriate for parameter type

---

## Test Case 5: Testing với Custom Parameters

**Mục đích:** Verify testing algorithms với custom parameter values

**Điều kiện tiên quyết:**
- Có teaching image và window captures
- Đã add algorithms với custom parameters

**Các bước thực hiện:**
1. Load 3-5 window capture images
2. Add "Upscale 2x" algorithm, set Scale Factor = 2.5
3. Add "Binary Threshold" algorithm, set Threshold Value = 150
4. Check tất cả window captures
5. Click "Test Checked Images"
6. Verify test chạy với custom parameter values
7. Check test results hiển thị scores
8. Verify best score được mark với ⭐

**Kết quả mong đợi:**
- Test sử dụng current parameter values
- Results hiển thị algorithm configs được sử dụng
- Best match được highlight
- Test có thể complete without errors

**Cài đặt cần kiểm tra:**
- Test accuracy: reasonable scores (0.0-1.0)
- Performance: complete trong reasonable time
- Results persistence: lưu được khi click OK

---

## Test Case 6: UI Responsive Layout

**Mục đích:** Verify UI tự động điều chỉnh với nhiều parameters

**Điều kiện tiên quyết:**
- Dialog đã mở với default size

**Các bước thực hiện:**
1. Add "Grayscale Only" algorithm (no parameters)
2. Note list item height
3. Add "Full Pipeline" algorithm (nhiều parameters)
4. Verify list item height tăng để chứa parameters
5. Add 5-6 algorithms khác nhau
6. Verify algorithms list có scrollbar khi cần
7. Resize dialog window
8. Verify layout responsive và không bị cắt

**Kết quả mong đợi:**
- List items tự động adjust height
- Scrollbar xuất hiện khi cần thiết
- Parameters không bị cắt hoặc overlap
- Layout responsive với window resize

**Cài đặt cần kiểm tra:**
- Minimum dialog size: 1200x800
- Maximum list height: reasonable limit
- Parameter widget spacing: adequate

---

## Test Case 7: Data Persistence

**Mục đích:** Verify algorithm parameters được save/load đúng

**Điều kiện tiên quyết:**
- Có tool với action đã setup

**Các bước thực hiện:**
1. Add multiple algorithms với custom parameters
2. Set các parameter values khác default
3. Click "OK" để save
4. Close và reopen Multi-Image Algorithm Testing Dialog
5. Verify algorithms và parameters được restore
6. Save tool to JSON
7. Load tool from JSON
8. Verify algorithm parameters persist

**Kết quả mong đợi:**
- Parameters được save khi click OK
- Parameters được restore khi reopen dialog
- Tool JSON chứa algorithm parameter data
- Load tool restore đúng parameter values

**Cài đặt cần kiểm tra:**
- JSON format: valid và readable
- Backward compatibility: old tools vẫn load được
- Default values: used khi không có saved parameters

---

## Test Case 8: Performance với Nhiều Algorithms

**Mục đích:** Verify performance khi có nhiều algorithms với parameters

**Điều kiện tiên quyết:**
- System có reasonable specs

**Các bước thực hiện:**
1. Add 10+ algorithms vào list
2. Set custom parameters cho tất cả
3. Load 20+ window captures
4. Run test với tất cả algorithms
5. Monitor memory usage và CPU
6. Verify UI responsiveness
7. Check test completion time

**Kết quả mong đợi:**
- UI không freeze với nhiều algorithms
- Memory usage reasonable (< 1GB)
- Test completion trong acceptable time
- No memory leaks sau multiple tests

**Cài đặt cần kiểm tra:**
- Memory usage: stable, no continuous growth
- CPU usage: reasonable during testing
- UI responsiveness: smooth interactions
- Test accuracy: consistent results

---

## Edge Cases và Error Handling

### Edge Case 1: Algorithm không có Parameters
- Add "Grayscale Only" algorithm
- Verify chỉ hiển thị name, không có parameter widgets
- Verify vẫn test được bình thường

### Edge Case 2: Invalid Parameter Values
- Try paste invalid text vào parameter fields
- Verify graceful handling và fallback to valid values

### Edge Case 3: Rapid Parameter Changes
- Rapidly change parameters nhiều lần
- Verify UI không crash và preview updates correctly

### Edge Case 4: Large Parameter Values
- Test với maximum allowed parameter values
- Verify processing không crash với extreme values

---

## Acceptance Criteria Summary

✅ Binary Threshold algorithm được thêm với đúng parameters
✅ Tất cả algorithms hiển thị parameters inline
✅ Parameters có thể edit ngay trong listview
✅ Real-time preview updates khi thay đổi parameters
✅ Parameter validation với min/max/step values
✅ UI responsive với dynamic height adjustment
✅ Testing hoạt động với custom parameter values
✅ Data persistence save/load parameters correctly
✅ Backward compatibility với existing tools
✅ Performance acceptable với nhiều algorithms