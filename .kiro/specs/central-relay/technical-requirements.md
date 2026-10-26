# Central Relay Technical Requirements

## 1. MỤC TIÊU KỸ THUẬT

Central Relay là signaling service công khai giúp Auto_MU Server và remote client tìm đúng nhau để thiết lập
WebRTC P2P. Relay không nằm trên data path sau handshake và không triển khai TURN hoặc application data relay.

### 1.1. Ranh giới thành phần

| Thành phần        | Trách nhiệm kỹ thuật                                                                 |
|-------------------|--------------------------------------------------------------------------------------|
| Auto_MU Agent     | Giữ signaling connection, đăng ký username và tạo WebRTC peer connection              |
| Remote Client     | Tìm server theo username và tạo WebRTC peer connection                                |
| Central Relay     | Xác thực agent, quản lý registry và chuyển signaling theo signaling session          |
| STUN service      | Cung cấp server-reflexive candidate để ICE thử NAT traversal                         |
| WebRTC DataChannel| Truyền password và toàn bộ dữ liệu ứng dụng trực tiếp giữa hai peer                  |

### 1.2. Nguyên tắc bắt buộc

1. Relay phải có public HTTPS/WSS endpoint; Cloudflare là tùy chọn triển khai, không phải yêu cầu protocol.
2. Agent và client đều chủ động mở outbound connection tới Relay.
3. Relay chỉ lưu username, connection identity và signaling metadata cần thiết.
4. Relay không được nhận password hoặc application payload.
5. WebRTC chỉ dùng direct ICE candidates; không cấu hình TURN candidate.
6. P2P thất bại phải kết thúc bằng lỗi; không fallback qua Relay.
7. Mỗi server chỉ có tối đa một client đang thiết lập hoặc đã kết nối; request khác bị từ chối bằng `server_busy`.

## 2. KIẾN TRÚC

```text
                      signaling only
┌────────────────┐       HTTPS/WSS       ┌──────────────────┐
│ Auto_MU Agent  │◀─────────────────────▶│ Central Relay    │
└───────┬────────┘                       │ username registry│
        │                                │ signaling rooms  │
        │ WebRTC P2P                     └─────────▲────────┘
        │ DataChannel                              │ HTTPS/WSS
        │                                          │ signaling only
        ▼                                          ▼
┌────────────────┐                         ┌──────────────────┐
│ Direct encrypted│                        │ Remote Client    │
│ application data│◀──────────────────────▶│                  │
└────────────────┘                         └──────────────────┘
```

STUN hỗ trợ candidate discovery nhưng không mang application data. Central Relay có thể được expose trực tiếp
bằng public VPS/domain hoặc đặt sau Cloudflare; hành vi signaling không phụ thuộc lựa chọn này.

## 3. IDENTITY VÀ REGISTRY

### 3.1. Agent identity

- Mỗi bản cài Auto_MU phải có `installation_id` và `agent_token` riêng.
- `agent_token` xác thực agent với Relay và không liên quan remote password.
- Không được nhúng một shared agent token cố định cho mọi installation.
- Relay phải bind `installation_id` với `agent_token` tại enrollment và không được tin `installation_id` chỉ vì agent
  tự khai trong payload.
- `agent_token` phải ngẫu nhiên, có thể revoke/rotate và được lưu bằng Windows DPAPI; quy trình phát hành, rotate và
  recovery cụ thể phải được chốt trong design.

### 3.2. Server run

- Mỗi lần Remote Server bật tạo `server_run_id`, username 9 chữ số và password 6 chữ số mới tại Auto_MU Server.
- Username và password phải được tạo bằng CSPRNG và không chứa dữ liệu nhận diện máy.
- Agent đăng ký `server_run_id` và username với Relay nhưng không gửi password.
- Relay phải bảo đảm username duy nhất trong online registry.
- Registry record tối thiểu gồm `username`, `server_run_id`, `agent_connection_id`, protocol version và expiry.
- Username là locator công khai với người được chia sẻ, không phải bí mật và không cấp remote permission.
- Khi agent disconnect hoặc heartbeat timeout, Relay phải xóa registry record.

### 3.3. Signaling session

- Mỗi client request hợp lệ tạo một `signaling_session_id` ngẫu nhiên.
- Session chỉ chứa đúng một agent connection và một client connection.
- Signaling session có timeout và bị cleanup khi một peer disconnect.
- `signaling_session_id` không phải remote session token và không cấp quyền điều khiển Auto_MU.
- Mỗi bản cài client tạo một `client_instance_id` ngẫu nhiên 128 bit, lưu bền vững và gửi trong mọi
  `connection_request`; ID này dùng để áp dụng lockout theo thiết bị, không phải authentication credential.
- `client_instance_id` do client khai có thể bị thay đổi, vì vậy không được dùng thay password hoặc thay rate limit
  theo source IP.

## 4. SIGNALING ENDPOINTS

### 4.1. Agent signaling connection

```text
WSS /v1/signaling/agents
Authorization: Bearer {agent_token}
```

Agent registration:

```json
{
  "type": "server_register",
  "protocol_version": 1,
  "installation_id": "opaque-installation-id",
  "server_run_id": "opaque-server-run-id",
  "username": "123456789",
  "capabilities": ["data_channel", "chat", "frame", "game_state"]
}
```

Relay response:

```json
{
  "type": "server_registered",
  "server_run_id": "opaque-server-run-id",
  "heartbeat_interval_seconds": 15
}
```

- Nếu username đang được dùng, Relay trả `username_conflict`; agent phải tạo username mới, cập nhật UI và đăng ký lại.
- Relay không được có field password trong registration schema.
- Một agent connection có thể nhận nhiều `connection_request`, nhưng chỉ chấp nhận khi không có client nào đang thiết
  lập hoặc đã kết nối; ngược lại agent gửi `connection_reject` với `reason: busy`.

### 4.2. Client signaling connection

```text
WSS /v1/signaling/clients
```

Client request:

```json
{
  "type": "connection_request",
  "protocol_version": 1,
  "username": "123456789",
  "client_instance_id": "base64url-128-bit-random-value",
  "device_name": "My Android Phone"
}
```

- Relay tra username trong online registry.
- Nếu không có mapping active, Relay trả `server_unavailable` chung.
- Nếu có mapping, Relay tạo signaling session và gửi `incoming_connection` kèm `client_instance_id` tới đúng agent.
- Password không được xuất hiện trong request này.

### 4.3. WebRTC signaling messages

| Message type          | Hướng                  | Mục đích                                         |
|-----------------------|------------------------|--------------------------------------------------|
| `connection_request`  | Client → Relay         | Yêu cầu tìm server theo username                 |
| `incoming_connection` | Relay → Agent          | Thông báo client muốn thiết lập P2P              |
| `connection_accept`   | Agent → Relay          | Chấp nhận bắt đầu signaling                      |
| `connection_reject`   | Agent → Relay          | Từ chối trước khi tạo P2P; `reason: busy` khi đang bận |
| `webrtc_offer`        | Peer → Relay → Peer    | Chuyển SDP offer                                 |
| `webrtc_answer`       | Peer → Relay → Peer    | Chuyển SDP answer                                |
| `ice_candidate`       | Peer → Relay → Peer    | Chuyển Trickle ICE candidate                     |
| `ice_complete`        | Peer → Relay → Peer    | Báo đã thu thập hết candidate                    |
| `p2p_connected`       | Peer → Relay           | Báo DataChannel đã mở                            |
| `p2p_failed`          | Peer → Relay → Peer    | Báo không tìm được đường trực tiếp cho cả hai phía  |
| `signaling_close`     | Peer/Relay → Peer      | Kết thúc signaling session                       |

Mọi signaling message sau `connection_request` phải có:

```json
{
  "type": "webrtc_offer",
  "protocol_version": 1,
  "signaling_session_id": "opaque-signaling-id",
  "message_id": "opaque-message-id",
  "payload": {}
}
```

- Mỗi peer chỉ gửi `p2p_connected` sau khi WebRTC connection connected và `control` DataChannel đã open.
- Relay chỉ đánh dấu signaling thành công sau khi nhận `p2p_connected` từ cả hai peer của cùng session; báo cáo từ
  một phía không đồng nghĩa phía còn lại đã sẵn sàng.
- Nếu nhận `p2p_failed`, Relay forward cho peer còn kết nối rồi cleanup session. Nếu peer kia đã disconnect, Relay
  chỉ cleanup; `p2p_failed` và `signaling_close` phải idempotent.

## 5. ROUTING INVARIANTS

- Relay chỉ forward message giữa hai connection thuộc cùng `signaling_session_id`.
- Client không được thay username hoặc agent đích sau khi session được tạo.
- Agent không được gửi signaling cho session không thuộc connection hiện tại.
- Relay phải kiểm tra type, kích thước và state hợp lệ trước khi forward.
- Relay không được sửa SDP/ICE payload ngoài validation/normalization bắt buộc đã ghi trong protocol version.
- Relay không broadcast signaling hoặc server registry.
- Relay không proxy WebRTC DataChannel packet.

## 6. WEBRTC P2P CONTRACT

### 6.1. ICE/STUN

- Agent và client phải dùng ICE với ít nhất một STUN service được cấu hình.
- Cấu hình ICE không được chứa TURN URL hoặc relay candidate.
- Trickle ICE candidate phải được chuyển qua signaling session.
- Kết nối chỉ được coi là thành công khi WebRTC connection connected và DataChannel mở.
- Nếu ICE state chuyển sang failed hoặc timeout, hai phía trả `p2p_unavailable` và cleanup.

### 6.2. DataChannels

Hai peer phải tạo tối thiểu hai channel:

| Channel   | Chế độ                    | Dữ liệu                                                |
|-----------|---------------------------|--------------------------------------------------------|
| `control` | Reliable, ordered         | Password handshake, session, chat, state và permission |
| `stream`  | Ưu tiên dữ liệu mới       | JPEG frame và frame metadata                           |

- Client gửi `auth_request` gồm `request_id`, `client_instance_id` và password trên `control` sau khi channel open;
  `client_instance_id` phải khớp giá trị đã bind vào signaling session.
- Auto_MU Server tự xác thực password bằng constant-time comparison.
- Handshake đúng thì server tạo `remote_session_id`, session token và permission snapshot.
- Handshake sai thì server trả lỗi chung và đóng peer connection.
- Auto_MU đếm lỗi riêng theo `(server_run_id, client_instance_id)`. Sau 5 lần sai liên tiếp, chỉ thiết bị đó nhận
  `auth_locked` trong 300 giây; server không khóa username hoặc các thiết bị khác.
- Xác thực thành công, hết thời gian khóa hoặc server restart phải reset bộ đếm của thiết bị tương ứng.
- Sau khi authenticated, client gửi `client_heartbeat` mỗi 15 giây trên `control`; server xử lý heartbeat độc lập với
  chat/tool và giải phóng session khi không nhận heartbeat trong 45 giây.
- Chat, frame, game state, tool call và command chỉ được gửi qua P2P DataChannel.
- Mỗi P2P connection tương ứng một remote client session.
- Frame JPEG phải dùng application framing gồm `frame_id`, `sequence`, `timestamp`, `total_size`, `chunk_index` và
  `chunk_count`. Mỗi chunk tối đa 16 KiB, tổng một frame tối đa 8 MiB; frame vượt giới hạn hoặc thiếu chunk bị drop.
- Server chỉ giữ frame mới nhất, theo dõi DataChannel backpressure và không tiếp tục enqueue khi queue đã có một frame.

### 6.3. Không có fallback

- Không triển khai TURN.
- Không dùng Central Relay làm WebSocket data relay.
- UI phải hiển thị rõ `p2p_unavailable` và cho phép người dùng chủ động thử lại.
- Direct P2P có thể làm hai peer nhìn thấy public IP của nhau; đây là đặc tính được chấp nhận.

## 7. STATE MACHINES

### 7.1. Server registry

```text
offline → authenticating → registering → online → offline
```

### 7.2. Signaling session

```text
requested → accepted → exchanging → peer_1_ready → both_ready → closed
                       └──────────→ p2p_failed ───────────────→ closed
```

### 7.3. Auto_MU client slot và P2P authentication

```text
available → reserved → authenticating → active → releasing → available
                │             │             │
                └── timeout ──┴── reject ───┴── close/timeout
```

- Relay quản lý hai state machine đầu nhưng không quản lý password state.
- Auto_MU Server và client quản lý P2P authentication/session state.
- Auto_MU phải cấp slot bằng thao tác atomic `available → reserved`; chỉ request thắng thao tác này được gửi
  `connection_accept`, request còn lại nhận `server_busy`.
- Slot chuyển sang `authenticating` khi `control` DataChannel open và chỉ chuyển `active` sau `auth_result=success`.
- Mọi đường fail, timeout, revoke, peer close hoặc server stop phải đi qua `releasing`; cleanup và release phải idempotent.

## 8. TIMEOUT, HEARTBEAT VÀ CLEANUP

| Tham số                     | Giá trị mặc định | Mốc bắt đầu và hành vi                                             |
|-----------------------------|------------------|--------------------------------------------------------------------|
| Agent heartbeat interval    | 15 giây          | Từ khi agent online; duy trì registry                              |
| Agent offline timeout       | 45 giây          | Từ heartbeat agent cuối; xóa username mapping                      |
| Signaling session timeout   | 30 giây          | Từ khi Relay tạo session; cleanup nếu chưa `both_ready`            |
| P2P connect timeout         | 20 giây          | Từ `connection_accept`; fail nếu `control` chưa open               |
| Authentication timeout      | 10 giây          | Từ khi `control` open; release slot nếu chưa xác thực              |
| Client heartbeat interval   | 15 giây          | Từ khi session active; gửi độc lập với chat/tool                   |
| Client heartbeat timeout    | 45 giây          | Từ heartbeat client cuối; close session và release slot            |
| Registry reconnect backoff  | 1–30 giây        | Agent tự reconnect signaling                                       |
| Per-device auth lockout     | 300 giây         | Khóa riêng `client_instance_id` sau 5 lần sai liên tiếp            |

- Khi nhiều deadline cùng có thể áp dụng, deadline hết trước phải thắng và cleanup còn lại phải idempotent.
- `signaling_session_timeout` quản lý Relay; P2P/auth/client-heartbeat timeout quản lý Auto_MU và client.

- Agent signaling disconnect làm server không nhận connection mới.
- Signaling disconnect không được chủ động đóng P2P session đã active.
- Relay restart làm mất registry/signaling session; agent phải đăng ký lại username của server run hiện tại.
- Relay không lưu command để replay sau reconnect.

## 9. BẢO MẬT VÀ RIÊNG TƯ

- Mọi signaling connection phải dùng TLS (`wss://`).
- Relay phải xác thực agent trước khi cho đăng ký username.
- Relay phải rate-limit `connection_request` tối đa 10 request/phút cho mỗi source IP để hạn chế dò username.
- Relay phải rate-limit `server_register` tối đa 5 lần/phút theo installation đã xác thực, không theo
  `installation_id` tự khai trong payload.
- Relay không được log SDP nguyên bản nếu SDP chứa địa chỉ mạng không cần thiết cho vận hành.
- Relay không được nhận/log password, remote session token hoặc application payload.
- Error response không được xác nhận một username từng tồn tại trong quá khứ.
- WebRTC DTLS bảo vệ DataChannel; password chỉ truyền bên trong kênh đã mã hóa.
- Fingerprint từ SDP phải được ràng buộc với signaling session để tránh tráo peer giữa các session.

## 10. ERROR CONTRACT

| Error code             | Phạm vi             | Ý nghĩa                                              |
|------------------------|----------------------|-----------------------------------------------------|
| `invalid_agent`        | Agent registration   | Agent identity không hợp lệ                         |
| `username_conflict`    | Agent registration   | Username đang thuộc server online khác              |
| `server_unavailable`   | Client request       | Không có server active cho username                 |
| `signaling_rejected`   | Signaling            | Agent từ chối yêu cầu                               |
| `server_busy`          | Signaling            | Server đang thiết lập hoặc đã kết nối với client khác |
| `signaling_timeout`    | Signaling            | Không hoàn tất offer/answer/ICE đúng hạn            |
| `invalid_signaling`    | Signaling            | Message hoặc state không hợp lệ                     |
| `rate_limited`         | Registration/request | Vượt giới hạn request                               |
| `p2p_unavailable`      | Peer connection      | ICE/DataChannel không tạo được đường trực tiếp      |
| `auth_timeout`         | P2P authentication   | Thiết bị không gửi/xong xác thực trong 10 giây     |
| `auth_locked`          | P2P authentication   | Thiết bị hiện tại bị khóa sau nhiều lần sai        |

## 11. ACCEPTANCE CRITERIA

- [ ] Hai server ở hai mạng khác nhau đăng ký username đồng thời mà không xung đột.
- [ ] Client cung cấp username được ghép đúng agent connection.
- [ ] Username có đúng 9 chữ số, password có đúng 6 chữ số; password không bao giờ gửi lên Relay.
- [ ] Relay chuyển đúng SDP offer, answer và ICE candidate theo signaling session.
- [ ] Relay từ chối cross-session signaling và không công khai registry.
- [ ] Password không xuất hiện trong signaling schema hoặc Relay log.
- [ ] Windows/Android/iOS WebRTC implementation có thể dùng cùng protocol version.
- [ ] Sau DataChannel open, server/client tự handshake password và tạo remote session.
- [ ] `client_instance_id` ổn định theo bản cài client, được bind vào signaling session và không thay thế password.
- [ ] Application payload không đi qua Relay.
- [ ] ICE thất bại trả `p2p_unavailable`, Relay forward `p2p_failed` cho phía còn lại, không sinh TURN/Relay candidate.
- [ ] Request tới server đang bận nhận `server_busy` và signaling session bị đóng ngay.
- [ ] Request thứ 11 trong một phút từ cùng IP nhận `rate_limited`.
- [ ] `server_register` thứ 6 trong một phút từ cùng installation nhận `rate_limited`.
- [ ] Relay disconnect không đóng P2P session đang active.
- [ ] Server disconnect xóa username mapping và signaling session chưa hoàn tất.
- [ ] Chỉ thiết bị có cùng `client_instance_id` bị `auth_locked` sau 5 lần sai; thiết bị khác không bị khóa theo.
- [ ] Slot được reserve atomically và được release khi signaling/P2P/auth timeout, xác thực sai, peer close hoặc revoke.
- [ ] `p2p_connected` chỉ hoàn tất signaling sau khi cả hai peer báo `control` DataChannel đã open.
- [ ] Client gửi heartbeat mỗi 15 giây; thiếu heartbeat 45 giây đóng session và giải phóng slot.
- [ ] Frame lớn được chia chunk tối đa 16 KiB, tổng không quá 8 MiB và không làm queue vượt một frame.

## 12. ĐIỂM PHẢI CHỐT TRONG DESIGN

1. Cơ chế enrollment, phát hành, rotate, revoke và recovery `agent_token` cho mỗi installation.
2. STUN service sử dụng trong production và chính sách thay thế khi STUN unavailable.
3. WebRTC implementation cụ thể: Windows/Python, Android và iOS.
4. Wire encoding cụ thể cho frame chunk và ngưỡng DataChannel backpressure theo từng nền tảng.
5. Cách tích hợp asyncio network worker với PyQt mà không update UI ngoài UI thread.
6. Chính sách rate limit và thời gian lưu audit metadata.

