# Android Remote Client Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Android cần kết nối tới shared Remote Server của Auto_MU để xem thông tin của một window đã được chọn trong handshake, nhận stream/state khi được Windows admin cấp quyền và gửi message chat theo event order.

**Mục tiêu:**

- Tạo Android client độc lập bằng Kotlin và Jetpack Compose.
- Signaling URL được đóng gói theo build/environment; người dùng chỉ nhập username và password.
- Hỗ trợ Internet mode bằng Central Relay signaling và WebRTC P2P DataChannel.
- Dùng username 9 chữ số để Relay tìm đúng server; không gửi password cho Relay.
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

"Core" là `.kiro/specs/remote-core-feature/requirements.md`; "Relay tech" là
`.kiro/specs/central-relay/technical-requirements.md`.

| Loại   | Tác nhân            | Nội dung nghiệp vụ                                       | Chi tiết kỹ thuật                                 |
|--------|---------------------|----------------------------------------------------------|---------------------------------------------------|
| Input  | Người dùng Android  | Nhập username và password                               | §3.8                                              |
| Input  | Người dùng Android  | Chọn một window ban đầu                                  | `target_select` (§3.7)                            |
| Input  | Người dùng Android  | Mở hoặc đóng viewer                                       | `stream_subscription` (§3.7)                     |
| Input  | Người dùng Android  | Mở hoặc đóng Game State                                  | `game_state_subscription` (§3.7)                 |
| Input  | Người dùng Android  | Gửi chat message                                         | `chat_submit` (§3.7)                              |
| Input  | Người dùng Android  | Yêu cầu danh sách MCP tools                              | `tool_catalog_request` (§3.7)                     |
| Input  | Người dùng Android  | Gọi tool chỉ đọc hoặc thay đổi trạng thái                | `tool_call` (§3.7)                                |
| Input  | Người dùng Android  | Hủy tool call đang chạy                                  | `tool_cancel` (§3.7)                              |
| Input  | Người dùng Android  | Ngắt kết nối hoặc đóng app                                | Peer close (§3.8)                                 |
| Input  | Auto_MU Server      | Xác thực thành công kèm session và permission hiện tại   | §3.8                                              |
| Input  | Auto_MU Server      | Xác thực thất bại (lỗi chung)                            | Relay tech §6.2                                   |
| Input  | Auto_MU Server      | Thiết bị hiện tại đang tạm khóa đăng nhập                | `auth_locked` (Relay tech §6.2, §10)              |
| Input  | Auto_MU Server      | Danh sách window được phép chọn                          | `targets_snapshot` (§3.7)                         |
| Input  | Auto_MU Server      | Danh sách window được phép đã thay đổi                   | `targets_changed` (§3.7)                          |
| Input  | Auto_MU Server      | Permission đã thay đổi                                   | `permission_changed` (§3.7)                       |
| Input  | Auto_MU Server      | Frame ảnh của window đã chọn                             | `frame` + JPEG binary (§3.7)                      |
| Input  | Auto_MU Server      | Game State của window đã chọn                            | `game_state` (§3.7)                               |
| Input  | Auto_MU Server      | Trạng thái xử lý chat, tool event và câu trả lời        | `chat_event`, `tool_event` (§3.7)                 |
| Input  | Auto_MU Server      | Yêu cầu bị từ chối do thiếu quyền                        | `permission_denied` (§3.7)                        |
| Input  | Auto_MU Server      | Window đã chọn không còn khả dụng                         | `target_unavailable` (§3.7)                       |
| Input  | Auto_MU Server      | Session bị thu hồi                                       | `session_revoked` (§3.7)                          |
| Input  | Auto_MU Server      | Tool call hết thời gian                                  | `tool_timeout` (§3.7)                             |
| Input  | Auto_MU Server      | Server dừng hoặc đóng kết nối                             | Peer close (§3.8)                                 |
| Input  | Central Relay       | Thông tin thiết lập kết nối từ server                    | `webrtc_offer/answer`, `ice_*` (Relay tech §4.3)  |
| Input  | Central Relay       | Không tìm thấy máy                                       | `server_unavailable` (Relay tech §10)             |
| Input  | Central Relay       | Máy từ chối kết nối                                      | `signaling_rejected` (Relay tech §10)             |
| Input  | Central Relay       | Máy đang bận với thiết bị khác                            | `server_busy` (Relay tech §10)                    |
| Input  | Central Relay       | Server báo không kết nối trực tiếp được                   | Forward `p2p_failed` (Relay tech §4.3)            |
| Input  | Central Relay       | Hết thời gian thiết lập kết nối                          | `signaling_timeout` (Relay tech §10)              |
| Input  | Central Relay       | Từ chối vì gửi quá nhiều yêu cầu                         | `rate_limited` (Relay tech §10)                   |
| Output | Central Relay       | Yêu cầu kết nối tới máy có username X kèm nhận diện thiết bị | `connection_request`, `client_instance_id` (Relay tech §4.2) |
| Output | Central Relay       | Gửi thông tin thiết lập kết nối cho server                | `webrtc_offer/answer`, `ice_*` (Relay tech §4.3)  |
| Output | Central Relay       | Báo kết nối trực tiếp thành công                          | `p2p_connected` (Relay tech §4.3)                 |
| Output | Central Relay       | Báo kết nối trực tiếp thất bại                            | `p2p_failed` (Relay tech §4.3)                    |
| Output | Central Relay       | Hủy yêu cầu kết nối                                      | `signaling_close` (Relay tech §4.3)               |
| Output | Auto_MU Server      | Gửi password và nhận diện thiết bị qua P2P đã mã hóa     | `auth_request` (§3.7–3.8)                         |
| Output | Auto_MU Server      | Gửi window đã chọn                                      | `target_select` (§3.7)                            |
| Output | Auto_MU Server      | Yêu cầu bắt đầu hoặc dừng nhận frame                      | `stream_subscription` (§3.7)                      |
| Output | Auto_MU Server      | Yêu cầu bắt đầu hoặc dừng nhận Game State                 | `game_state_subscription` (§3.7)                  |
| Output | Auto_MU Server      | Gửi chat message                                         | `chat_submit` (§3.7)                              |
| Output | Auto_MU Server      | Yêu cầu hủy tool call                                    | `tool_cancel` (§3.7)                              |
| Output | Auto_MU Server      | Báo định kỳ vẫn còn kết nối                               | `client_heartbeat` (§3.7–3.8)                     |
| Output | Auto_MU Server      | Đóng kết nối                                             | Peer close (§3.8)                                 |
| Output | Người dùng Android  | Trạng thái kết nối hiện tại                                | UI §4                                             |
| Output | Người dùng Android  | Permission hiện tại                                      | UI §4, §3.5                                       |
| Output | Người dùng Android  | Frame mới nhất của window đã chọn                         | UI §4, §3.7                                       |
| Output | Người dùng Android  | Game State của window đã chọn                            | UI §4, §3.3                                       |
| Output | Người dùng Android  | Chat message và trạng thái xử lý                         | UI §4, §3.4                                       |
| Output | Người dùng Android  | Lỗi xác thực                                             | §3.6                                              |
| Output | Người dùng Android  | Server đang tạm khóa đăng nhập                           | §3.6                                              |
| Output | Người dùng Android  | Không tìm thấy máy                                       | §3.6                                              |
| Output | Người dùng Android  | Máy đang bận với thiết bị khác                            | §3.6                                              |
| Output | Người dùng Android  | Không kết nối trực tiếp được                              | `p2p_unavailable` (§3.6)                          |
| Output | Người dùng Android  | Window đã chọn không còn khả dụng                         | §3.6                                              |
| Output | Người dùng Android  | Mất kết nối hoặc dữ liệu đã cũ                           | §3.6                                              |

**Parameters:**

| Tham số                 | Kiểu   | Mô tả                                   | Giá trị mặc định |
|-------------------------|--------|-----------------------------------------|------------------|
| `reconnect_initial`     | long   | Backoff reconnect ban đầu               | `1` giây         |
| `reconnect_max`         | long   | Backoff reconnect tối đa                | `30` giây        |
| `heartbeat_interval`    | long   | Khoảng heartbeat                        | `15` giây        |
| `max_chat_tool_calls`   | int    | Giới hạn tool call của một lượt chat    | `20`             |
| `signaling_url`         | string | Central Relay WSS endpoint              | Build/environment config |
| `stun_urls`             | list   | STUN service dùng cho ICE               | Cấu hình deploy  |
| `p2p_connect_timeout`   | long   | Timeout tạo WebRTC DataChannel          | `20` giây        |
| `auth_timeout`          | long   | Timeout gửi và hoàn tất xác thực        | `10` giây        |
| `frame_chunk_bytes`     | int    | Payload tối đa của một frame chunk      | `16384`          |
| `max_frame_bytes`       | int    | Kích thước JPEG tối đa                  | `8388608`        |

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌──────────────────────┐
│ Nhập username/pass  │
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
Server đang bận? ── Yes → Hiển thị máy đang bận
          ↓ No
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

- Input: Username 9 chữ số và password 6 chữ số hiển thị trong dialog `Remote Server Status` trên Windows khi server
  đang `running`. Signaling URL lấy từ build/environment config, người dùng không nhập.
- Process: Mở signaling connection tới Central Relay, chỉ gửi username để tìm server, trao đổi SDP/ICE
  và thiết lập WebRTC P2P. Request kèm `client_instance_id` 128 bit được tạo một lần cho bản cài. Sau khi `control`
  DataChannel mở, gửi password và cùng `client_instance_id` trực tiếp cho Auto_MU Server.
- Output: Connection state và handshake result.

**Bước 2: Chọn window ban đầu**

- Input: Danh sách window đã được Windows Settings cho phép, gồm title/process/PID/HWND/tab.
- Process: Người dùng chọn một window; gửi identity lên server.
- Output: Session ở trạng thái authenticated; feature permissions có thể vẫn disabled.

**Bước 3: Nhận permission**

- Input: Permission snapshot từ Windows.
- Process: Android chỉ hiển thị permission; không tự nâng quyền. Permission do Windows admin cấp cho session hiện tại.
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
- Process: Backoff reconnect, heartbeat và giữ trạng thái stale; tạo signaling session mới và thương lượng WebRTC lại.
- Nếu reconnect nhận lỗi server bận vì server chưa giải phóng session cũ, tiếp tục backoff cho tới khi server giải
  phóng (tối đa khoảng 45 giây) rồi đăng nhập lại.
- Không chuyển sang TURN hoặc Relay data path khi P2P thất bại.
- Output: Connected, reconnecting, stale hoặc closed.

### 3.2. Edge Cases

- Permission bị Windows admin revoke: hiển thị trạng thái disabled và không gửi request thuộc permission đó.
- Permission bị revoke: UI chuyển disabled và request mới bị từ chối; stream/state/tool/chat chờ xử lý bị dừng theo loại permission.
- Session target stale: dừng viewer/state, không tự chọn window khác.
- Client nhận frame chậm: hiển thị frame mới nhất, bỏ frame cũ.
- Mất mạng: server giữ session cũ tối đa 45 giây kể từ heartbeat cuối; reconnect trong thời gian này nhận lỗi server bận
  và Android tiếp tục backoff, không tạo session trùng.
- Android app bị đóng: đóng peer connection và cancel request local.
- Username không online: hiển thị server unavailable mà không gửi password cho Relay.
- ICE/DataChannel timeout: hiển thị `p2p_unavailable`, cleanup peer connection và cho phép user thử lại.
- Signaling mất sau khi P2P active: giữ session nếu DataChannel vẫn hoạt động.
- Password P2P sai: hiển thị lỗi xác thực chung và đóng peer connection.
- Server trả `auth_locked`: hiển thị thiết bị hiện tại đang tạm khóa đăng nhập, không tự thử lại trước thời hạn.
- Server đang bận với thiết bị khác khi người dùng chủ động kết nối: hiển thị máy đang bận, không tự thử lại và không
  gửi password.
- Server báo không kết nối trực tiếp được: hiển thị `p2p_unavailable` và cleanup peer connection.

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
| Mất kết nối P2P       | Reconnect với backoff                             |
| Tool timeout          | Hiển thị timeout, cho phép cancel                 |
| Server closed         | Đóng session và hiển thị trạng thái disconnected  |
| Server unavailable    | Không gửi password; cho phép nhập lại username    |
| Signaling timeout     | Cleanup signaling session và cho phép thử lại     |
| P2P unavailable       | Đóng peer connection; không fallback              |
| P2P auth failed       | Hiển thị lỗi chung và đóng peer connection        |
| Auth timeout          | Đóng peer connection và cho phép thử lại           |
| Auth locked           | Báo thiết bị bị tạm khóa, không tự thử lại          |
| Server busy           | Kết nối mới: báo máy bận, không tự thử lại; reconnect: tiếp tục backoff |

## 3.7. Hợp đồng dữ liệu realtime

- Mọi JSON control message phải có `type`, `protocol_version`, `remote_session_id` sau xác thực, `request_id` cho
  request/response và timestamp.
- Client gửi `auth_request`, `target_select`, `stream_subscription`, `game_state_subscription`, `chat_submit`,
  `tool_catalog_request`, `tool_call`, `tool_cancel` và `client_heartbeat` theo hành động tương ứng.
- Server trả `auth_result`, `targets_snapshot`, `targets_changed`, `permission_snapshot`, `permission_changed`,
  `chat_event`, `tool_event`, `tool_timeout`, `permission_denied`, `target_unavailable` và `session_revoked`.
- Mỗi frame bắt đầu bằng metadata `type=frame_start`, `frame_id`, `sequence`, `timestamp`, `mime=image/jpeg`,
  `total_size`, `chunk_count`; các binary chunk mang `frame_id`, `chunk_index` và payload tối đa 16 KiB.
- Tổng JPEG không được vượt 8 MiB. Frame thiếu chunk, sai kích thước hoặc cũ hơn sequence mới nhất phải bị drop.
- State gồm JSON `type=game_state`, `sequence`, `timestamp`, `target_hwnd`, `data`.
- Android phải bỏ frame cũ khi sequence thấp hơn frame mới nhất.
- Android phải xử lý `targets_changed`, `session_revoked`, `target_unavailable`, `permission_denied` và peer close.
- Android phải theo dõi DataChannel backpressure, chỉ giữ dữ liệu của frame mới nhất và không để queue tăng vô hạn.

## 3.8. Hợp đồng Internet WebRTC

- Android mở outbound WSS tới Central Relay và gửi `connection_request` chứa username, `client_instance_id` cùng
  metadata client; `client_instance_id` là locator ổn định của bản cài, không phải credential.
- Android không gửi password, chat, frame request hoặc application payload cho Central Relay.
- Android nhận/gửi SDP offer, SDP answer và Trickle ICE candidate trong đúng `signaling_session_id`.
- WebRTC ICE sử dụng STUN và không cấu hình TURN URL hoặc relay candidate.
- Android chỉ gửi `p2p_connected` khi peer connection connected và `control` DataChannel open; signaling chỉ hoàn tất
  sau khi cả hai peer cùng báo trạng thái này.
- Android gửi `auth_request` gồm password và `client_instance_id` trực tiếp qua `control` DataChannel trong 10 giây;
  Auto_MU Server tự xác thực và trả remote session.
- `control` DataChannel phải reliable/ordered cho auth, session, permission, chat, game state và command.
- `stream` DataChannel dùng cho JPEG frame; client ưu tiên frame mới và bỏ frame cũ khi bị chậm.
- Sau xác thực, Android gửi `client_heartbeat` mỗi 15 giây độc lập với chat/tool; mất kết nối 45 giây làm server đóng
  session và client chuyển sang reconnect.
- Mọi P2P message phải có `protocol_version` và session/request identity phù hợp.
- ICE/DataChannel fail hoặc timeout trả `p2p_unavailable`; không fallback qua Central Relay hoặc TURN.
- Signaling connection có thể đóng sau khi P2P active mà không làm DataChannel bị đóng.
- Android phải cleanup peer connection khi user disconnect, server revoke, password sai hoặc app bị đóng.
- WebRTC implementation Android phải tương thích SDP/ICE/DTLS/SCTP DataChannel với Windows implementation và iOS.

## 4. PHÁC THẢO UI

```text
┌──────────────────────────────────┐
│ Remote Connection                │
├──────────────────────────────────┤
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
- [ ] Mỗi bản cài có `client_instance_id` 128 bit ổn định; ID không thay thế password.
- [ ] Sau 5 lần sai password, chỉ thiết bị hiện tại bị khóa 300 giây.
- [ ] Heartbeat gửi mỗi 15 giây sau xác thực và chạy độc lập với chat/tool.
- [ ] Frame được ghép theo `frame_id/chunk_index`, giới hạn 16 KiB mỗi chunk và 8 MiB mỗi JPEG.
- [ ] Android trao đổi SDP/ICE trong đúng signaling session.
- [ ] Chat, frame, state và command đi trực tiếp qua WebRTC P2P.
- [ ] Client không cấu hình TURN hoặc Relay data fallback.
- [ ] P2P thất bại hiển thị `p2p_unavailable` và cho phép user chủ động thử lại.
- [ ] Server đang có thiết bị khác thì Android hiển thị máy đang bận và không gửi password.
- [ ] Signaling disconnect không tự đóng P2P session đang active.
- [ ] Android WebRTC interoperable với Windows và iOS theo cùng protocol version.

## 6. Ngoài phạm vi

- Không mô tả hoặc triển khai remote control UI.
- Không triển khai quyền admin trên Android.
- Không triển khai QR/pairing/device identity hoàn chỉnh.
- Không triển khai Central Relay service hoặc Cloudflare Tunnel trong Android app.
- Không triển khai TURN hoặc bất kỳ data relay fallback nào.
