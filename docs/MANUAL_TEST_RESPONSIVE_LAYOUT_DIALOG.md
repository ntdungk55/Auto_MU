# Manual Test Plan: Responsive Layout cho Multi-Image Algorithm Testing Dialog

## Test Case 1: Dialog Resize Behavior

**Mục đích:** Kiểm tra chỉ có Window Capture preview được dãn ra khi resize dialog

**Điều kiện tiên quyết:**
- Có action với teaching image hợp lệ
- Dialog được mở thành công

**Các bước thực hiện:**
1. Mở Multi-Image Algorithm Testing Dialog
2. Quan sát layout ban đầu (1400x900)
3. Kéo góc dialog để tăng width lên 1600px
4. Quan sát sự thay đổi của các components
5. Kéo góc dialog để tăng height lên 1000px
6. Quan sát sự thay đổi của các components

**Kết quả mong đợi:**
- Window Capture preview (bên phải) tự động dãn ra theo kích thước dialog
- Teaching Image preview giữ nguyên max width 400px
- Window Captures List giữ nguyên max height 200px
- Algorithms List giữ nguyên max height 120px
- Buttons giữ nguyên fixed/minimum widths
- ComboBoxes giữ nguyên minimum width 200px

## Test Case 2: Minimum Size Constraints

**Mục đích:** Kiểm tra dialog không thể resize nhỏ hơn minimum size

**Điều kiện tiên quyết:**
- Dialog được mở thành công

**Các bước thực hiện:**
1. Mở dialog
2. Thử kéo dialog nhỏ hơn 1200x800
3. Quan sát behavior

**Kết quả mong đợi:**
- Dialog không thể resize nhỏ hơn 1200x800
- Layout vẫn hiển thị đúng ở minimum size

## Test Case 3: Splitter Behavior

**Mục đích:** Kiểm tra splitter giữa Teaching và Window Capture preview

**Điều kiện tiên quyết:**
- Dialog được mở với teaching image

**Các bước thực hiện:**
1. Mở dialog
2. Kéo splitter bar giữa Teaching và Window Capture preview
3. Quan sát tỷ lệ thay đổi
4. Resize dialog và quan sát splitter

**Kết quả mong đợi:**
- Có thể điều chỉnh tỷ lệ giữa Teaching và Window Capture
- Teaching view không vượt quá max width 400px
- Splitter hoạt động smooth

## Test Case 4: Component Fixed Sizes

**Mục đích:** Kiểm tra các components giữ nguyên kích thước khi resize

**Điều kiện tiên quyết:**
- Dialog được mở thành công

**Các bước thực hiện:**
1. Mở dialog
2. Đo kích thước các buttons, combo boxes, lists
3. Resize dialog to 1600x1000
4. Đo lại kích thước các components

**Kết quả mong đợi:**
- Load Images button: min width 120px
- Capture New button: min width 120px  
- Test Checked Images button: min width 150px
- Stop button: fixed width 80px
- Algorithm combo: min width 200px
- Test algorithm combo: min width 200px
- OK/Close buttons: fixed width 80px

## Test Case 5: Layout Stability

**Mục đích:** Kiểm tra layout không bị vỡ khi resize extreme

**Điều kiện tiên quyết:**
- Dialog được mở thành công

**Các bước thực hiện:**
1. Mở dialog
2. Resize to maximum screen size
3. Resize to minimum size (1200x800)
4. Resize to very wide (2000x800)
5. Resize to very tall (1200x1200)

**Kết quả mong đợi:**
- Layout không bị vỡ ở bất kỳ kích thước nào
- Tất cả components vẫn visible và accessible
- Window Capture preview luôn chiếm phần lớn không gian available
- Scroll bars xuất hiện khi cần thiết

## Cài đặt cần kiểm tra:

- **Dialog minimum size**: 1200x800
- **Dialog default size**: 1400x900
- **Teaching view max width**: 400px
- **Captures list max height**: 200px
- **Algorithms list max height**: 120px
- **Preview splitter stretch**: 5 (high priority)
- **Other components stretch**: 0 (fixed size)

## Lưu ý:

- Test trên nhiều độ phân giải màn hình khác nhau
- Kiểm tra cả landscape và portrait orientations
- Đảm bảo UI vẫn usable ở minimum size
- Kiểm tra performance khi resize liên tục