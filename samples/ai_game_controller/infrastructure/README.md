# Infrastructure

## Mục đích

Chứa implementation cụ thể cho các interface mà application yêu cầu.

## File dự kiến

- `game_state_reader.py` — `GameStateReader`: chụp game window và phát hành OCR snapshot chuẩn hóa.
- `game_state_store.py` — `GameStateStore`: lưu state mới nhất của từng target theo cách thread-safe.
- `process_selector.py` — `ProcessSelector`: liệt kê và validate process/window game trên Windows.
- `window_capture.py` — `GameWindowCapture`: chụp client area của game window.
- `tesseract_recognizer.py` — `TesseractRecognizer`: OCR text ROI cho teaching JSON hiện tại.
- `scenario_repository.py` — `ScenarioRepository`: lưu scenario JSON runtime theo từng target.
- `openvino_recognizer.py` — `OpenVINORecognizer`: recognizer-only OCR trên CPU/Intel GPU.
- `mcp_gateway.py` — `MCPGateway`: discover và gọi tool qua MCP client hiện có.
- `ai_agent_factory.py` — `AIAgentFactory`: tạo AI agent theo provider/model.
- `settings_store.py` — `SettingsStore`: lưu/đọc settings và scenario dạng JSON.
- `jsonl_event_log.py` — `JsonlEventLog`: ghi event, AI decision, MCP call và lỗi.
- `README.md`: mô tả phạm vi của infrastructure.

## Quy tắc phụ thuộc

- Implement interface được định nghĩa bởi application.
- Không đặt business rule trong adapter.
- API key phải lấy từ biến môi trường hoặc secret store, không ghi vào JSON hay log.

← [Quay lại README cha](../README.md)
