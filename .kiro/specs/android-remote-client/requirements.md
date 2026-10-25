# Android Remote Client Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Android cần kết nối tới shared Remote Server của Auto_MU để xem thông tin của một window đã được chọn trong handshake, nhận stream/state khi được Windows admin cấp quyền và gửi message chat theo event order.

**Mục tiêu:**

- Tạo Android client độc lập bằng Kotlin và Jetpack Compose.
- Kết nối shared Remote Server qua HTTP/WebSocket.
- Handshake, chọn window active ban đầu và khóa session vào một window.
- Hiển thị quyền hiện tại do Windows admin cấp.
- Chỉ subscribe stream/state khi được cấp quyền và khi remote yêu cầu.
- Hiển thị message remote và trạng thái xử lý theo thứ tự event đến server.
- Không tự triển khai quyền admin hoặc cơ chế remote control trong Android requirements.

**Cấu trúc đề xuất:**

```text
app/
core/model/
core/network/
core/streaming/
core/security/
feature/connection/
feature/game-viewer/
feature/game-state/
feature/ai-chat/
ai/llm/
ai/agent/
ai/tools/
```

**Input/Output:**

| Loại   | Mô tả                                  | Ví dụ                                  |
|--------|----------------------------------------|----------------------------------------|
| Input  | Server endpoint và credential           | `http://192.168.1.10:8765`             |
| Input  | Window selection ban đầu                | `target_window_identity`               |
| Input  | Chat message hoặc stream request       | `send_chat`, `subscribe_stream`        |
| Output | Connection/session state               | `Connecting`, `Authenticated`, `Revoked`|
| Output | Frame, state, message và tool result   | JPEG binary, JSON state, text message  |

**Parameters:**

| Tham số                 | Kiểu   | Mô tả                                  | Giá trị mặc định |
|------------------------|--------|----------------------------------------|------------------|
| `connect_timeout`      | long   | Timeout kết nối                        | `10` giây        |
| `reconnect_initial`    | long   | Backoff reconnect ban đầu              | `1` giây         |
| `reconnect_max`        | long   | Backoff reconnect tối đa               | `30` giây        |
| `heartbeat_interval`   | long   | Khoảng heartbeat                       | `15` giây        |
| `max_chat_tool_calls`  | int    | Giới hạn tool call của một lượt chat   | `20`             |

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌──────────────────────┐
│ Nhập endpoint/token  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Connect + handshake  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Chọn active window   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Nhận permission state│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Hiển thị permissions  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Request stream/state  │
│ hoặc gửi chat         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Reconnect/close       │
└──────────────────────┘
```

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Kết nối**

- Input: Endpoint, username 4 chữ số và password 4 chữ số hiển thị trong dialog `Remote Server Status` trên Windows khi server đang `running`.
- Process: Mở HTTP/WebSocket connection tới shared Remote Server.
- Output: Connection state và handshake result.

**Bước 2: Chọn window ban đầu**

- Input: Danh sách window đã được Windows Settings cho phép, gồm title/process/PID/HWND/tab.
- Process: Người dùng chọn một window; gửi identity lên server.
- Output: Session ở trạng thái authenticated; feature permissions có thể vẫn disabled.

**Bước 3: Nhận permission**

- Input: Permission snapshot từ Windows.
- Process: Android chỉ hiển thị permission; không tự nâng quyền. Permissions áp dụng global cho tất cả remote client.
- Output: UI enable/disable chức năng tương ứng.

**Bước 4: Nhận stream/state**

- Input: User yêu cầu viewer/state và permission tương ứng.
- Process: Gửi subscription request; decode JPEG binary và cập nhật JSON state.
- Output: Viewer/state của đúng window đã binding.

**Bước 5: Gửi chat**

- Input: Message từ remote user.
- Process: Gửi event đến server; event nào đến server trước được xử lý trước.
- Output: Message status, tool event hoặc final response.

**Bước 6: Reconnect**

- Input: Socket disconnect, app background hoặc server unavailable.
- Process: Backoff reconnect, heartbeat và giữ trạng thái stale.
- Output: Connected, reconnecting, stale hoặc closed.

### 3.2. Edge Cases

- Permission bị Windows admin revoke: hiển thị trạng thái disabled và không gửi request thuộc permission đó.
- Permission bị revoke: UI chuyển disabled và request mới bị từ chối; stream/state/tool/chat chờ xử lý bị dừng theo loại permission.
- Session target stale: dừng viewer/state, không tự chọn window khác.
- Client nhận frame chậm: hiển thị frame mới nhất, bỏ frame cũ.
- Mất mạng: không tạo duplicate session nếu reconnect thành công.
- Android app bị đóng: đóng WebSocket và cancel request local.

### 3.3. Game State

- State phải giữ nguyên field name do Windows API công bố.
- Field chưa xác định phải hiển thị `null` hoặc `unknown`, không tự suy đoán.
- State phải có timestamp, sequence/frame id và target identity.
- UI phải phân biệt `connected`, `stale`, `target_unavailable` và `permission_denied`.

### 3.4. Chat và AI Agent

- Android có thể có AI abstraction và tool executor theo permission được cấp.
- Android không có quyền admin.
- Android không tự thay đổi target sau handshake.
- Message/event gửi lên server theo thứ tự người dùng tạo; server là nơi quyết định FIFO cuối cùng.
- Các lần tool call phải chịu quota, timeout và cancellation do server cung cấp.

### 3.5. Permission effect

- `view_stream` bị tắt: Android dừng viewer ngay.
- `view_game_state` bị tắt: Android dừng cập nhật state ngay.
- `send_chat` bị tắt: message đang chờ bị xóa; message đã hiển thị không bị xóa; lượt AI đang chạy không bị hủy.
- `discover_tools` bị tắt: xóa tool catalog.
- `call_readonly_tools` hoặc `call_mutating_tools` bị tắt: request tương ứng bị từ chối hoặc hủy theo server.
- Remote server bị user Stop: đóng session, credentials cũ không dùng lại được và không reconnect cho tới khi user chủ động kết nối lại với credentials mới.

### 3.6. Xử lý lỗi

| Lỗi                    | Hành vi Android                                  |
|-----------------------|--------------------------------------------------|
| Auth/handshake fail   | Hiển thị lỗi, cho phép thử lại                    |
| Permission denied     | Disable chức năng tương ứng                      |
| Target unavailable    | Dừng viewer/state/tool request                    |
| WebSocket timeout     | Reconnect với backoff                             |
| Tool timeout          | Hiển thị timeout, cho phép cancel                 |
| Server closed         | Đóng session và hiển thị trạng thái disconnected  |

## 4. PHÁC THẢO UI

```text
┌──────────────────────────────────┐
│ Remote Connection                │
├──────────────────────────────────┤
│ Endpoint: [                    ]  │
│ Username: [                    ]  │
│ Password: [                    ]  │
│ [Connect]                         │
│ Status: Authenticated; permissions enabled  │
│ Target: Game.exe / PID 1234      │
├──────────────────────────────────┤
│ Permissions                       │
│ Stream: [Enabled] State: [On]    │
│ Chat:   [Enabled] Tools: [On]    │
├──────────────────────────────────┤
│ Game Viewer / Game State / Chat   │
└──────────────────────────────────┘
```

## 5. Acceptance Criteria

- [ ] Android kết nối được shared server.
- [ ] Handshake cho phép chọn một active window ban đầu.
- [ ] Sau handshake chỉ hiển thị dữ liệu của window đã binding.
- [ ] Permission mặc định hiển thị enabled và thay đổi sang disabled khi Windows admin revoke.
- [ ] Permission thay đổi từ Windows được phản ánh trên Android.
- [ ] Stream chỉ bắt đầu khi remote yêu cầu và có quyền.
- [ ] JPEG nhận dạng binary, state nhận dạng JSON.
- [ ] Mất mạng có heartbeat, backoff và trạng thái stale.
- [ ] Remote chat được gửi tới server theo event order.
- [ ] Android không tự đổi target hoặc tự nâng quyền.

## 6. Ngoài phạm vi

- Không mô tả hoặc triển khai remote control UI.
- Không triển khai quyền admin trên Android.
- Không triển khai QR/pairing/device identity hoàn chỉnh.
- Không triển khai Cloudflare Tunnel, relay hoặc WebRTC.
