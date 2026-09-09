# Config

## Mục đích

Chứa cấu hình mẫu không có secret. Runtime sẽ đọc các file này và tạo một snapshot bất biến khi bấm Start.

## File

- `app_settings.json`: OCR, model, interval, giới hạn runtime và đường dẫn cấu hình.
- `sample_scenario.json`: scenario prompt, event và allowed tools mẫu.
- `README.md`: mô tả phạm vi cấu hình.

## Quy tắc

- Không lưu API key trong thư mục này.
- File example không được dùng làm nơi ghi runtime state.
- Cấu hình phải được validate trước khi khởi động worker.

← [Quay lại README cha](../README.md)
