# Tests

## Mục đích

Chứa kiểm thử của riêng mini app mẫu.

## File trực tiếp dự kiến

- `README.md`: mô tả chiến lược test và dẫn tới từng cấp test.

## Thư mục con

- [`unit/`](unit/README.md): kiểm tra từng thành phần độc lập.
- [`integration/`](integration/README.md): kiểm tra luồng qua nhiều thành phần và MCP subprocess.

Không mock subject under test; chỉ thay external dependency khi cần kiểm tra logic quyết định.

← [Quay lại README cha](../README.md)
