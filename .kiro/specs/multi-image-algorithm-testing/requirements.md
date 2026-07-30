# Requirements Document: Multi-Image Algorithm Testing Dialog

## Introduction

Tạo dialog mới cho phép test nhiều ảnh window capture với teaching image để tìm thuật toán preprocessing tốt nhất cho template matching. Dialog này giúp user dễ dàng thu thập nhiều ảnh từ game, test với các thuật toán khác nhau, và xem kết quả so sánh với threshold.

## Glossary

- **Teaching_Image**: Ảnh mẫu được crop từ window game, dùng để so sánh với window captures
- **Window_Capture**: Ảnh chụp toàn bộ window game để test matching với teaching image
- **Preprocessing_Algorithm**: Thuật toán xử lý ảnh trước khi template matching (upscale, contrast, sharpen, denoise)
- **Match_Score**: Điểm số từ 0.0 đến 1.0 thể hiện độ tương đồng giữa teaching image và window capture
- **Threshold**: Ngưỡng tối thiểu để coi như match thành công (lấy từ action settings)
- **Dialog**: Cửa sổ Multi-Image Algorithm Testing
- **Action**: Object chứa cấu hình của một action trong tool

## Requirements

### Requirement 1: Hiển thị Teaching Image và Window Capture Preview

**User Story:** Là người dùng, tôi muốn xem teaching image và window capture được chọn cạnh nhau, để tôi có thể so sánh trực quan giữa chúng.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị teaching image ở bên trái, tự động load từ action.image_path
2. THE Dialog SHALL hiển thị window capture được chọn ở bên phải
3. THE Dialog SHALL chia preview area thành 2 phần bằng nhau (50/50)
4. THE Dialog SHALL hiển thị ảnh ở kích thước lớn nhất có thể trong preview area
5. WHEN user chọn một window capture trong list, THE Dialog SHALL hiển thị ảnh đó ở preview bên phải
6. WHEN test hoàn thành, THE Dialog SHALL highlight vùng match trên window capture preview

### Requirement 2: Quản lý Window Captures List

**User Story:** Là người dùng, tôi muốn quản lý danh sách window captures (thêm, xóa, chọn), để tôi có thể thu thập và tổ chức ảnh test.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị list tối đa 50 window captures
2. THE Dialog SHALL hiển thị checkbox cho mỗi window capture để chọn test
3. THE Dialog SHALL hiển thị tên file và kết quả match cho mỗi window capture
4. WHEN window capture chưa test, THE Dialog SHALL hiển thị "Not tested yet"
5. WHEN window capture đã test, THE Dialog SHALL hiển thị "Match: X.XX ✅/❌" so với threshold
6. WHEN có window capture có score cao nhất, THE Dialog SHALL đánh dấu "⭐ BEST"
7. THE Dialog SHALL cung cấp nút [📁 Load Images...] để load nhiều ảnh từ local
8. THE Dialog SHALL cung cấp nút [📷 Capture New] để chụp ảnh mới từ window game
9. THE Dialog SHALL cung cấp nút [➖ Remove Selected] để xóa các ảnh đã chọn
10. THE Dialog SHALL tự động lưu window captures vào folder: images/[tool_id]/[action_name]/window_captures/
11. WHEN user click vào một item trong list, THE Dialog SHALL chọn item đó và hiển thị preview

### Requirement 3: Quản lý Preprocessing Algorithms

**User Story:** Là người dùng, tôi muốn quản lý danh sách các thuật toán preprocessing, để tôi có thể test nhiều cấu hình khác nhau.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị dropdown chọn algorithm và nút [➕ Add]
2. THE Dialog SHALL hiển thị list các algorithms đã có
3. THE Dialog SHALL có 7 algorithms mặc định hardcoded:
   - None
   - Upscale 2x
   - Upscale+Contrast
   - Upscale+Contrast+Sharpen
   - Full Pipeline (Upscale+Contrast+Sharpen+Denoise)
   - Upscale 3x
   - Upscale 3x+Contrast+Sharpen
4. THE Dialog SHALL hiển thị nút [⚙️ Settings] và [❌ Delete] cho mỗi algorithm
5. WHEN user click nút Settings, THE Dialog SHALL hiển thị message "Tính năng đang phát triển"
6. WHEN user click nút Delete, THE Dialog SHALL xóa algorithm khỏi list
7. THE Dialog SHALL lưu algorithm list vào action.preprocessing_algorithms

### Requirement 4: Test Window Captures với Algorithm

**User Story:** Là người dùng, tôi muốn test các window captures đã chọn với một algorithm cụ thể, để tôi biết algorithm nào cho kết quả tốt nhất.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị dropdown để chọn algorithm cần test
2. THE Dialog SHALL hiển thị nút [🧪 Test Checked Images] để bắt đầu test
3. THE Dialog SHALL hiển thị nút [⏸️ Stop] để dừng test đang chạy
4. THE Dialog SHALL hiển thị progress bar với phần trăm hoàn thành
5. THE Dialog SHALL hiển thị text "Testing: [filename] with [algorithm]... (X/Y)"
6. THE Dialog SHALL hiển thị threshold từ action settings
7. WHEN user click Test, THE Dialog SHALL test tất cả window captures có checkbox được tích
8. WHEN test hoàn thành, THE Dialog SHALL cập nhật match score vào list
9. WHEN test hoàn thành, THE Dialog SHALL so sánh score với threshold và hiển thị ✅/❌
10. WHEN test hoàn thành, THE Dialog SHALL tìm và đánh dấu ảnh có score cao nhất với ⭐
11. THE Dialog SHALL lưu test results vào action.window_capture_results

### Requirement 5: Lưu và Đóng Dialog

**User Story:** Là người dùng, tôi muốn có tùy chọn lưu hoặc không lưu thay đổi khi đóng dialog, để tôi có thể hủy bỏ nếu không hài lòng với kết quả.

#### Acceptance Criteria

1. THE Dialog SHALL hiển thị nút [✅ OK] ở cuối dialog
2. THE Dialog SHALL hiển thị nút [❌ Close] ở cuối dialog
3. WHEN user click OK, THE Dialog SHALL lưu tất cả thay đổi vào action:
   - action.window_capture_paths (list các đường dẫn ảnh)
   - action.window_capture_results (dict {path: score})
   - action.preprocessing_algorithms (list các algorithm configs)
4. WHEN user click OK, THE Dialog SHALL đóng dialog và return accepted
5. WHEN user click Close, THE Dialog SHALL đóng dialog mà không lưu gì và return rejected
6. WHEN user click X (close button), THE Dialog SHALL hoạt động giống như click Close

### Requirement 6: Auto-save Window Captures

**User Story:** Là người dùng, tôi muốn window captures được tự động lưu vào folder riêng của action, để tôi không mất dữ liệu khi thay đổi teaching image.

#### Acceptance Criteria

1. THE Dialog SHALL tự động tạo folder: images/[tool_id]/[action_name]/window_captures/
2. WHEN user load images từ local, THE Dialog SHALL copy ảnh vào folder trên
3. WHEN user capture new image, THE Dialog SHALL lưu ảnh vào folder trên
4. THE Dialog SHALL đặt tên file theo format: capture_XXX.png (XXX là số thứ tự)
5. THE Dialog SHALL hiển thị text "Auto-saved to: images/[tool_id]/[action_name]/window_captures/"

### Requirement 7: Load Teaching Image từ Action

**User Story:** Là người dùng, tôi muốn teaching image được tự động load từ action settings, để tôi không phải chọn lại.

#### Acceptance Criteria

1. WHEN dialog được mở, THE Dialog SHALL tự động load teaching image từ action.image_path
2. WHEN action.image_path không tồn tại, THE Dialog SHALL hiển thị warning và disable các nút test
3. THE Dialog SHALL hiển thị label "📷 Teaching Image (from action.image_path)"

### Requirement 8: Data Persistence

**User Story:** Là developer, tôi muốn đảm bảo tất cả dữ liệu được lưu đúng vào action object, để dữ liệu không bị mất khi save tool.

#### Acceptance Criteria

1. THE Dialog SHALL lưu window_capture_paths vào action khi click OK
2. THE Dialog SHALL lưu window_capture_results vào action khi click OK
3. THE Dialog SHALL lưu preprocessing_algorithms vào action khi click OK
4. THE System SHALL serialize các fields trên trong tool_manager.py (_action_to_dict)
5. THE System SHALL deserialize các fields trên trong tool_manager.py (from_dict)
6. WHEN user save tool → close app → reopen, THE System SHALL load lại đúng dữ liệu

### Requirement 9: Thread-Safe UI Updates

**User Story:** Là developer, tôi muốn UI updates được thực hiện thread-safe, để tránh crash khi test đang chạy.

#### Acceptance Criteria

1. THE Dialog SHALL dùng signals với QueuedConnection cho tất cả UI updates từ background thread
2. THE Dialog SHALL emit signal khi test progress thay đổi
3. THE Dialog SHALL emit signal khi test hoàn thành
4. THE Dialog SHALL emit signal khi test gặp lỗi
5. THE Dialog SHALL xử lý signals trong UI thread để update widgets

### Requirement 10: Template Matching với Preprocessing

**User Story:** Là người dùng, tôi muốn test sử dụng đúng thuật toán preprocessing đã chọn, để kết quả phản ánh chính xác hiệu quả của thuật toán.

#### Acceptance Criteria

1. WHEN test một window capture, THE System SHALL apply preprocessing algorithm đã chọn lên teaching image
2. THE System SHALL convert cả teaching và window capture sang grayscale
3. THE System SHALL sử dụng cv2.matchTemplate với method TM_CCOEFF_NORMED
4. WHEN action có multiscale_enabled, THE System SHALL test với nhiều scales
5. THE System SHALL return match score từ 0.0 đến 1.0
