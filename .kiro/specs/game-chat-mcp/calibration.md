# Kết quả thử trực tiếp trên NTD3006

Ngày thử: 2026-09-17. User yêu cầu chuyển sang NTD3006 và tiếp tục sau khi cấp quyền Administrator.

## Kết quả

Đã gửi đúng một lần câu `Xin anh em nhường bãi` từ NTD3006. Ảnh sau Enter có cả dòng chat `NTD3006: Xin anh em nhường bãi` và bong bóng chat phía trên nhân vật. Đây là kiểm thử trực tiếp bằng script chẩn đoán, chưa phải một MCP tool đã triển khai.

## Môi trường

- Cửa sổ: `MU GamethuVN - Season 21 (Golden - NTD3006)`.
- PID 13492, HWND 66958; chỉ là định danh của phiên thử, không dùng làm hằng số trong tool.
- Client 800x600; phiên shell xác nhận `Administrator: True` sau khi tiếp tục.
- Khảo sát trước đó là NTD3001 nhưng cùng PID/HWND. Điều này xác nhận phải kiểm tra cả tên nhân vật trước từng bước, không chỉ kiểm tra HWND tồn tại.
- Script tạm: `build/runtime/game_chat_ntd3006/probe.py`; ảnh/JSON cùng thư mục, được gitignore theo `build/`.

## Các bước và bằng chứng

| Bước                               | Kết quả quan sát                                                           |
|------------------------------------|----------------------------------------------------------------------------|
| Enter bằng helper trước nâng quyền | API báo thành công nhưng ảnh chưa cho thấy khung nhập mở                   |
| Focus trực tiếp sau nâng quyền     | Có lần SetForegroundWindow bị Windows từ chối                              |
| Focus bằng AttachThreadInput       | Thành công, detach trong finally; xác nhận foreground đúng HWND            |
| Enter scan-code giữ 100 ms         | Mở khung chat, thấy Normal / View Command List / Enter chat content        |
| Nhập Unicode                       | Câu có dấu hiển thị; chuỗi gõ thử cũ vẫn còn nên cần xóa trước             |
| Ctrl+A rồi Backspace               | Không xóa được nội dung trong phiên thử; chụp lại màn hình vẫn thấy text   |
| End → Shift+Home → Backspace       | Xóa sạch; ô hiện placeholder Enter chat content                            |
| Nhập lại riêng câu mẫu             | Hiển thị Xin anh em nhường bãi                                             |
| Enter gửi giữ 100 ms, một lần      | Khung nhập đóng; câu mẫu xuất hiện trong chat history và phía trên NTD3006 |

Các phím End/Home được gửi với extended-key flag. Thời gian 100 ms là giá trị đã thử thành công, chưa kết luận đây là thời gian tối thiểu cần thiết. Kết quả helper trước nâng quyền không đủ để quy nguyên nhân duy nhất cho quyền hoặc thời gian giữ phím.

## OCR và trạng thái trống

- Khi trống, ô chat hiển thị placeholder `Enter chat content`; OCR không rỗng. Nhận diện EMPTY phải phân biệt placeholder với text người dùng, dựa thêm vào màu/template.
- EasyOCR mặc định ở crop rộng đọc sai dấu/ký tự cuối khi caret hiện: ví dụ `băỉl` thay vì `bãi`; không được tự sửa bằng fuzzy match.
- Crop thử `x=16..319, y=560..580`, padding đen 6 pixel, scale 4 (INTER_CUBIC), trên hai frame không có caret cho kết quả chính xác `Xin anh em nhường bãi`, confidence khoảng 0.6081 và 0.6095.
- Có detection nhiễu `1` với confidence khoảng 0.028 ở ngoài dòng text; cần loại theo vị trí dòng và confidence, không ghép mọi detection.
- Mẫu trống đọc đúng placeholder với confidence khoảng 0.9952 trong lần thử crop đầu.
- JSON chi tiết: `ocr_results.json`, `ocr_variants.json`. Hai frame đúng: `text_frame_1.png`, `text_frame_2.png`.
- Hai kết quả đúng trên một câu chỉ chứng minh khả thi ở tình huống thử; chưa đủ chốt threshold tổng quát, hỗ trợ mọi chuỗi hoặc command.

## Ảnh quan trọng

- `admin_open_held.png`: Enter mở khung chat.
- `unicode_first.png`: ô chat chứa text thử cũ và câu mẫu, chưa gửi.
- `cleared_ctrl_a.png`, `clear_screen_1.png`: text vẫn còn sau Ctrl+A → Backspace.
- `cleared_shift_home.png`: End → Shift+Home → Backspace xóa sạch.
- `unicode_clean.png`, `text_frame_1.png`, `text_frame_2.png`: chỉ còn đúng câu mẫu.
- `submitted_once.png`: bằng chứng câu chat đã xuất hiện sau một lần Enter gửi.

## Điều chỉnh thiết kế và giới hạn

- Target hiện tại chuyển sang NTD3006 theo yêu cầu thử của user; giữ pin title/PID/HWND để phát hiện đổi nhân vật.
- Dùng End → Shift+Home → Backspace làm tổ hợp xóa đã kiểm chứng, không chọn Ctrl+A làm mặc định.
- Giữ literal Unicode input; tránh gõ text bằng hotkey/scan-code parser có thể bị bộ gõ tiếng Việt biến đổi.
- Bổ sung focus bằng AttachThreadInput có detach và xác nhận foreground, không dùng click vào nội dung game để lấy focus.
- Nhận diện EMPTY theo placeholder riêng; xử lý caret và detection nhiễu trước khi so sánh nguyên văn text.
- Chưa kiểm thử command cụ thể, độ dài tối đa, toàn bộ Unicode, các độ phân giải khác hoặc một MCP call end-to-end.
- Không còn text thử trong ô nhập sau lần gửi thành công. Không gửi các chuỗi thử cũ và không tự gửi lại câu mẫu.
