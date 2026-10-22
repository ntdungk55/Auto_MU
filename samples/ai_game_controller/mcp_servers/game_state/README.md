# Game State MCP Server

## Mục đích

Đây là process sở hữu OCR worker và state repository. Scenario Engine và AI truy cập game state thông qua MCP thay vì chia sẻ trực tiếp object Python giữa các process.

## File dự kiến

- `server.py`: entry point MCP server và quản lý vòng đời OCR worker.
- `tools.py`: khai báo các MCP tools đọc game state và event.
- `game_state_service.py`: chạy chu kỳ capture, ROI, preprocess, OCR và cập nhật state.
- `event_detector.py`: so sánh state cũ/mới, tạo event và áp dụng debounce/cooldown.
- `state_repository.py`: lưu snapshot mới nhất và hàng đợi event trong process server.
- `window_source.py`: tìm và chụp đồng thời cửa sổ MU 800x600, không focus.
- `roi_batch_builder.py`: đọc ROI, cắt ảnh, scale, grayscale và threshold.
- `openvino_recognizer.py`: recognizer-only inference, không chạy CRAFT.
- `device_scheduler.py`: chia batch CPU/Intel GPU và fallback khi cần.
- `config_loader.py`: đọc và validate ROI/OCR configuration.
- `README.md`: mô tả server và các file của nó.

## MCP tools dự kiến

- `get_selected_game_state`
- `get_game_state`
- `get_game_main_info`
- `get_latest_game_event`

## Ranh giới

- OCR worker chỉ tồn tại trong process server này.
- Server không tự gọi AI.
- Server không trực tiếp quyết định action điều khiển game.

← [Quay lại README cha](../README.md)
