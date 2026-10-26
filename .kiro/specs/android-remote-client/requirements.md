# Android Remote Client Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Android cần kết nối tới shared Remote Server của Auto_MU để xem thông tin của một window đã được chọn trong handshake, nhận stream/state khi được Windows admin cấp quyền và gửi message chat theo event order.

**Mục tiêu:**

- Tạo Android client độc lập bằng Kotlin và Jetpack Compose.
- Kết nối shared Remote Server qua HTTP/WebSocket.
- Hỗ trợ Internet mode bằng Central Relay signaling và WebRTC P2P DataChannel.
- Dùng username để Relay tìm đúng server; không gửi password cho Relay.
- Gửi password trực tiếp cho Auto_MU sau khi WebRTC DataChannel mã hóa đã mở.
- Truyền chat, frame, game state và remote command trực tiếp với Auto_MU, không qua Central Relay.
- Internet mode là P2P-only; kết nối thất bại nếu ICE không tìm được đường trực tiếp.
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

| Loại   | Mô tả                                    | Ví dụ                                     |
|--------|------------------------------------------|-------------------------------------------|
| Input  | Server endpoint và credential            | `http://192.168.1.10:8765`                |
| Input  | Signaling endpoint và username           | `wss://relay.example.com`, `1234`         |
| Input  | WebRTC signaling                         | Offer, answer, ICE candidate              |
| Input  | Window selection ban đầu                 | `target_window_identity`                  |
| Input  | Chat message hoặc stream request         | `send_chat`, `subscribe_stream`           |
| Output | Connection/session state                 | `Connecting`, `Authenticated`, `Revoked`  |
| Output | Frame, state, message và tool result     | JPEG binary, JSON state, text message     |
| Output | Trạng thái P2P                           | `Connecting`, `Connected`, `Failed`       |

**Parameters:**

| Tham số                 | Kiểu   | Mô tả                                   | Giá trị mặc định |
|-------------------------|--------|-----------------------------------------|------------------|
| `connect_timeout`       | long   | Timeout kết nối                         | `10` giây        |
| `reconnect_initial`     | long   | Backoff reconnect ban đầu               | `1` giây         |
| `reconnect_max`         | long   | Backoff reconnect tối đa                | `30` giây        |
| `heartbeat_interval`    | long   | Khoảng heartbeat                        | `15` giây        |
| `max_chat_tool_calls`   | int    | Giới hạn tool call của một lượt chat    | `20`             |
| `signaling_url`         | string | Central Relay WSS endpoint              | Cấu hình deploy  |
| `stun_urls`             | list   | STUN service dùng cho ICE               | Cấu hình deploy  |
| `p2p_connect_timeout`   | long   | Timeout tạo WebRTC DataChannel          | `20` giây        |

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

## 2.1. LUỒNG INTERNET P2P

```text
Nhập username/password
          ↓
Kết nối Central Relay
          ↓
Tìm server theo username
          ↓
Trao đổi SDP + ICE qua Relay
          ↓
WebRTC DataChannel connected?
     No ──┴── Yes
     ↓         ↓
Hiển thị      Gửi password trực tiếp
P2P failed         ↓
               Server xác thực
                    ↓
               Nhận remote session
                    ↓
               Dữ liệu đi P2P
```

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Kết nối**

- Input: Endpoint, username 4 chữ số và password 4 chữ số hiển thị trong dialog `Remote Server Status` trên Windows khi server đang `running`.
- Process LAN: Mở HTTP/WebSocket connection trực tiếp tới shared Remote Server.
- Process Internet: Mở signaling connection tới Central Relay, chỉ gửi username để tìm server, trao đổi SDP/ICE
  và thiết lập WebRTC P2P. Sau khi `control` DataChannel mở, gửi password trực tiếp cho Auto_MU Server.
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
- Process LAN: Backoff reconnect, heartbeat và giữ trạng thái stale.
- Process Internet: Tạo signaling session mới và thương lượng WebRTC lại; không chuyển sang TURN, Relay data path
  hoặc LAN mode khi P2P thất bại.
- Output: Connected, reconnecting, stale hoặc closed.

### 3.2. Edge Cases

- Permission bị Windows admin revoke: hiển thị trạng thái disabled và không gửi request thuộc permission đó.
- Permission bị revoke: UI chuyển disabled và request mới bị từ chối; stream/state/tool/chat chờ xử lý bị dừng theo loại permission.
- Session target stale: dừng viewer/state, không tự chọn window khác.
- Client nhận frame chậm: hiển thị frame mới nhất, bỏ frame cũ.
- Mất mạng: không tạo duplicate session nếu reconnect thành công.
- Android app bị đóng: đóng WebSocket và cancel request local.
- Username không online: hiển thị server unavailable mà không gửi password cho Relay.
- ICE/DataChannel timeout: hiển thị `p2p_unavailable`, cleanup peer connection và cho phép user thử lại.
- Signaling mất sau khi P2P active: giữ session nếu DataChannel vẫn hoạt động.
- Password P2P sai: hiển thị lỗi xác thực chung và đóng peer connection.

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

| Lỗi                   | Hành vi Android                                   |
|-----------------------|---------------------------------------------------|
| Auth/handshake fail   | Hiển thị lỗi, cho phép thử lại                    |
| Permission denied     | Disable chức năng tương ứng                       |
| Target unavailable    | Dừng viewer/state/tool request                    |
| WebSocket timeout     | Reconnect với backoff                             |
| Tool timeout          | Hiển thị timeout, cho phép cancel                 |
| Server closed         | Đóng session và hiển thị trạng thái disconnected  |
| Server unavailable    | Không gửi password; cho phép nhập lại username    |
| Signaling timeout     | Cleanup signaling session và cho phép thử lại     |
| P2P unavailable       | Đóng peer connection; không fallback              |
| P2P auth failed       | Hiển thị lỗi chung và đóng peer connection        |

## 3.7. Hợp đồng LAN WebSocket

- Sau `POST /handshake` và `POST /sessions/{session_id}/target`, Android mở `ws://<LAN_IP>:8765/sessions/{session_id}/stream`.
- WebSocket gửi header `Authorization: Bearer {session_id}`.
- Mỗi frame ảnh gồm một JSON metadata `type=frame`, `sequence`, `timestamp`, `mime=image/jpeg`, `size`, sau đó là một binary JPEG frame.
- State gồm JSON `type=game_state`, `sequence`, `timestamp`, `target_hwnd`, `data`.
- Android phải bỏ frame cũ khi sequence thấp hơn frame mới nhất.
- Android phải xử lý `targets_changed`, `session_revoked`, `target_unavailable`, `permission_denied` và WebSocket close.
- Chat hiện dùng HTTP `/sessions/{session_id}/messages`; realtime chat event chỉ được coi là hoàn thành khi server bổ sung message event trên WebSocket.

## 3.8. Hợp đồng Internet WebRTC

- Android mở outbound WSS tới Central Relay và gửi `connection_request` chỉ chứa username cùng metadata client.
- Android không gửi password, chat, frame request hoặc application payload cho Central Relay.
- Android nhận/gửi SDP offer, SDP answer và Trickle ICE candidate trong đúng `signaling_session_id`.
- WebRTC ICE sử dụng STUN và không cấu hình TURN URL hoặc relay candidate.
- Kết nối chỉ thành công khi peer connection connected và `control` DataChannel ở trạng thái open.
- Android gửi password trực tiếp qua `control` DataChannel; Auto_MU Server tự xác thực và trả remote session.
- `control` DataChannel phải reliable/ordered cho auth, session, permission, chat, game state và command.
- `stream` DataChannel dùng cho JPEG frame; client ưu tiên frame mới và bỏ frame cũ khi bị chậm.
- Mọi P2P message phải có `protocol_version` và session/request identity phù hợp.
- ICE/DataChannel fail hoặc timeout trả `p2p_unavailable`; không fallback qua Central Relay, TURN hoặc LAN mode.
- Signaling connection có thể đóng sau khi P2P active mà không làm DataChannel bị đóng.
- Android phải cleanup peer connection khi user disconnect, server revoke, password sai hoặc app bị đóng.
- WebRTC implementation Android phải tương thích SDP/ICE/DTLS/SCTP DataChannel với Windows implementation và iOS.

## 4. PHÁC THẢO UI

```text
┌──────────────────────────────────┐
│ Remote Connection                │
├──────────────────────────────────┤
│ Mode: [LAN / Internet P2P]       │
│ Signaling: [                   ]  │
│ Username: [                    ]  │
│ Password: [                    ]  │
│ [Connect]                         │
│ Status: Finding / P2P / Authenticated       │
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
- [ ] Internet client tìm đúng Auto_MU Server qua username và Central Relay signaling.
- [ ] Password không được gửi tới Central Relay mà chỉ gửi sau khi DataChannel mã hóa mở.
- [ ] Android trao đổi SDP/ICE trong đúng signaling session.
- [ ] Chat, frame, state và command đi trực tiếp qua WebRTC P2P.
- [ ] Client không cấu hình TURN hoặc Relay data fallback.
- [ ] P2P thất bại hiển thị `p2p_unavailable` và cho phép user chủ động thử lại.
- [ ] Signaling disconnect không tự đóng P2P session đang active.
- [ ] Android WebRTC interoperable với Windows và iOS theo cùng protocol version.

## 6. Ngoài phạm vi

- Không mô tả hoặc triển khai remote control UI.
- Không triển khai quyền admin trên Android.
- Không triển khai QR/pairing/device identity hoàn chỉnh.
- Không triển khai Central Relay service hoặc Cloudflare Tunnel trong Android app.
- Không triển khai TURN hoặc bất kỳ data relay fallback nào.
