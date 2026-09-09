# AI Game Controller sample

## Mục tiêu

Mini app mẫu đọc trạng thái game, phát hiện event, gửi scenario prompt cho AI và cho phép AI sử dụng MCP tools để đọc hoặc điều khiển game.

```text
┌───────────────────────────┐
│            USER           │
│ - Chọn process/window     │
│ - Nhập scenario prompt    │
│ - Start / Stop            │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│      SCENARIO ENGINE      │
│ Quản lý toàn bộ vòng đời  │
└───────┬───────────┬───────┘
        │           ▲
        ▼           │ event
┌──────────────┐    │    ┌──────────────────┐
│ GAME STATE   │────┴────│  EVENT DETECTOR  │
│ READER       │         │ state → event    │
│ OCR 800×600  │         └──────────────────┘
└──────┬───────┘
       ▼
┌───────────────────────────┐
│      GAME STATE STORE     │
│ State mới nhất từng game  │
└───────────────────────────┘
```

Khi có event:

```text
Scenario prompt + Event + GameState
                ↓
         PROMPT BUILDER
                ↓
            AI AGENT
                ↓ tool calls
       EXECUTION POLICY
                ↓
          MCP CLIENT
                ↓
          MCP SERVERS
                ↓
              GAME
                ↓
       Đọc GameState xác minh
```

MCP Server không tự gọi AI. Scenario Engine nhận event rồi chủ động gửi prompt cho AI; AI chỉ truy cập game thông qua MCP tools.

## File trực tiếp của thư mục này

- `main.py`: composition root `create_ai_process_controller()` cho feature controller, không tạo app hoặc UI riêng.
- `README.md`: giới thiệu tổng thể và dẫn tới tài liệu của từng thư mục con.

Feature hiện dừng tại controller/state pipeline và scenario persistence; EventDetector chưa có rule emit event, AI runtime và UI integration chưa được triển khai.

## Thư mục con

- [`domain/`](domain/README.md): model và quy tắc nghiệp vụ thuần.
- [`application/`](application/README.md): use case và điều phối scenario.
- [`infrastructure/`](infrastructure/README.md): adapter cho AI, MCP, settings và log.
- [`mcp_servers/`](mcp_servers/README.md): các MCP server thuộc riêng sample.
- [`ui/`](ui/README.md): giao diện PyQt.
- [`prompts/`](prompts/README.md): prompt được tách khỏi code.
- [`config/`](config/README.md): cấu hình mẫu không chứa secret.
- [`tests/`](tests/README.md): unit test và integration test.
- [`logs/`](logs/README.md): dữ liệu JSONL sinh ra khi chạy.

Mỗi thư mục con tự mô tả chi tiết các file thuộc phạm vi của nó; tài liệu này không lặp lại các chi tiết đó.
