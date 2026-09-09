# UI

## Mục đích

Chứa giao diện PyQt và binding tới controller. UI không chứa OCR, business rule hoặc logic gọi MCP trực tiếp.

## File dự kiến

- `main_window.py` — `MainWindow`: cửa sổ nhập target/scenario và cung cấp Start/Stop controls.
- `README.md`: mô tả phạm vi của UI.

## Quy tắc thread

- Background worker chỉ emit signal.
- Widget chỉ được cập nhật trong UI thread qua queued signal.
- UI gọi `process_controller`, không gọi OCR hoặc MCP implementation trực tiếp.

← [Quay lại README cha](../README.md)
