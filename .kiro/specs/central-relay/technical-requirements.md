# Central Relay Technical Requirements

## 1. MỤC TIÊU KỸ THUẬT

Central Relay là signaling service công khai giúp Auto_MU Server và remote client tìm đúng nhau để thiết lập
WebRTC P2P. Relay không nằm trên data path sau handshake và không triển khai TURN hoặc application data relay.

### 1.1. Ranh giới thành phần

| Thành phần        | Trách nhiệm kỹ thuật                                                                 |
|-------------------|--------------------------------------------------------------------------------------|
| Auto_MU Agent     | Giữ signaling connection, đăng ký rendezvous ID và tạo WebRTC peer connection         |
| Remote Client     | Tìm server theo rendezvous ID và tạo WebRTC peer connection                           |
| Central Relay     | Xác thực agent, quản lý registry và chuyển signaling theo signaling session          |
| STUN service      | Cung cấp server-reflexive candidate để ICE thử NAT traversal                         |
| WebRTC DataChannel| Truyền password và toàn bộ dữ liệu ứng dụng trực tiếp giữa hai peer                  |

### 1.2. Nguyên tắc bắt buộc

1. Relay phải có public HTTPS/WSS endpoint; Cloudflare là tùy chọn triển khai, không phải yêu cầu protocol.
2. Agent và client đều chủ động mở outbound connection tới Relay.
3. Relay chỉ lưu rendezvous ID, connection identity và signaling metadata cần thiết.
4. Relay không được nhận password hoặc application payload.
5. WebRTC chỉ dùng direct ICE candidates; không cấu hình TURN candidate.
6. P2P thất bại phải kết thúc bằng lỗi; không fallback qua Relay.
7. Một agent signaling connection phải phục vụ nhiều signaling session/client đồng thời.

## 2. KIẾN TRÚC

```text
                      signaling only
┌────────────────┐       HTTPS/WSS       ┌──────────────────┐
│ Auto_MU Agent  │◀─────────────────────▶│ Central Relay    │
└───────┬────────┘                       │ rendezvous registry│
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
- Cơ chế enrollment và lưu `agent_token` phải được chốt trong design; trên Windows ưu tiên DPAPI.

### 3.2. Server run

- Mỗi lần Remote Server bật tạo `server_run_id`, `rendezvous_id`, username và password mới tại Auto_MU Server.
- `rendezvous_id` phải được tạo bằng CSPRNG với entropy ít nhất 128 bit và không chứa dữ liệu nhận diện máy.
- Agent đăng ký `server_run_id` và `rendezvous_id` với Relay nhưng không gửi username/password.
- Relay phải bảo đảm rendezvous ID duy nhất trong online registry.
- Registry record tối thiểu gồm `rendezvous_id`, `server_run_id`, `agent_connection_id`, protocol version và expiry.
- `rendezvous_id` là locator, không phải authentication credential và không cấp remote permission.
- Khi agent disconnect hoặc heartbeat timeout, Relay phải xóa registry record.

### 3.3. Signaling session

- Mỗi client request hợp lệ tạo một `signaling_session_id` ngẫu nhiên.
- Session chỉ chứa đúng một agent connection và một client connection.
- Signaling session có timeout và bị cleanup khi một peer disconnect.
- `signaling_session_id` không phải remote session token và không cấp quyền điều khiển Auto_MU.

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
  "rendezvous_id": "base64url-128-bit-random-value",
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

- Nếu rendezvous ID đang được dùng, Relay trả `rendezvous_conflict`; agent phải tạo ID mới và đăng ký lại.
- Relay không được có field username/password trong registration schema.
- Một agent connection có thể nhận nhiều `connection_request` đồng thời.

### 4.2. Client signaling connection

```text
WSS /v1/signaling/clients
```

Client request:

```json
{
  "type": "connection_request",
  "protocol_version": 1,
  "rendezvous_id": "base64url-128-bit-random-value",
  "device_name": "My Android Phone"
}
```

- Relay tra rendezvous ID trong online registry.
- Nếu không có mapping active, Relay trả `server_unavailable` chung.
- Nếu có mapping, Relay tạo signaling session và gửi `incoming_connection` tới đúng agent.
- Password không được xuất hiện trong request này.

### 4.3. WebRTC signaling messages

| Message type          | Hướng                  | Mục đích                                         |
|-----------------------|------------------------|--------------------------------------------------|
| `connection_request`  | Client → Relay         | Yêu cầu tìm server theo rendezvous ID            |
| `incoming_connection` | Relay → Agent          | Thông báo client muốn thiết lập P2P              |
| `connection_accept`   | Agent → Relay          | Chấp nhận bắt đầu signaling                      |
| `connection_reject`   | Agent → Relay          | Từ chối trước khi tạo P2P                        |
| `webrtc_offer`        | Peer → Relay → Peer    | Chuyển SDP offer                                 |
| `webrtc_answer`       | Peer → Relay → Peer    | Chuyển SDP answer                                |
| `ice_candidate`       | Peer → Relay → Peer    | Chuyển Trickle ICE candidate                     |
| `ice_complete`        | Peer → Relay → Peer    | Báo đã thu thập hết candidate                    |
| `p2p_connected`       | Peer → Relay           | Báo DataChannel đã mở                            |
| `p2p_failed`          | Peer → Relay           | Báo không tìm được đường trực tiếp               |
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

## 5. ROUTING INVARIANTS

- Relay chỉ forward message giữa hai connection thuộc cùng `signaling_session_id`.
- Client không được thay rendezvous ID hoặc agent đích sau khi session được tạo.
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

- Password chỉ được gửi trên `control` sau khi channel ở trạng thái open.
- Auto_MU Server tự xác thực password bằng constant-time comparison.
- Handshake đúng thì server tạo `remote_session_id`, session token và permission snapshot.
- Handshake sai thì server trả lỗi chung và đóng peer connection.
- Chat, frame, game state, tool call và command chỉ được gửi qua P2P DataChannel.
- Mỗi P2P connection tương ứng một remote client session.

### 6.3. Không có fallback

- Không triển khai TURN.
- Không dùng Central Relay làm WebSocket data relay.
- Không tự chuyển sang LAN HTTP/WebSocket khi Internet P2P thất bại.
- UI phải hiển thị rõ `p2p_unavailable` và cho phép người dùng chủ động thử lại.
- Direct P2P có thể làm hai peer nhìn thấy public IP của nhau; đây là đặc tính được chấp nhận.

## 7. STATE MACHINES

### 7.1. Server registry

```text
offline → authenticating → registering → online → offline
```

### 7.2. Signaling session

```text
requested → accepted → exchanging → p2p_connected → closed
                       └──────────→ p2p_failed ─────→ closed
```

### 7.3. P2P authentication

```text
data_channel_open → password_pending → authenticated → active → closed
                                     └→ rejected ─────────────→ closed
```

- Relay quản lý hai state machine đầu nhưng không quản lý password state.
- Auto_MU Server và client quản lý P2P authentication/session state.

## 8. TIMEOUT, HEARTBEAT VÀ CLEANUP

| Tham số                    | Giá trị mặc định | Hành vi                                         |
|----------------------------|------------------|-------------------------------------------------|
| Agent heartbeat interval   | 15 giây          | Duy trì online registry                         |
| Agent offline timeout      | 45 giây          | Xóa rendezvous mapping                          |
| Signaling session timeout  | 30 giây          | Kết thúc offer/answer/ICE chưa hoàn tất         |
| P2P connect timeout        | 20 giây          | Hai peer kết luận `p2p_unavailable`             |
| Registry reconnect backoff | 1–30 giây        | Agent tự reconnect signaling                    |

- Agent signaling disconnect làm server không nhận connection mới.
- Signaling disconnect không được chủ động đóng P2P session đã active.
- Relay restart làm mất registry/signaling session; agent phải đăng ký lại rendezvous ID của server run hiện tại.
- Relay không lưu command để replay sau reconnect.

## 9. BẢO MẬT VÀ RIÊNG TƯ

- Mọi signaling connection phải dùng TLS (`wss://`).
- Relay phải xác thực agent trước khi cho đăng ký rendezvous ID.
- Relay phải rate-limit `connection_request` theo source IP, rendezvous ID và installation.
- Relay không được log SDP nguyên bản nếu SDP chứa địa chỉ mạng không cần thiết cho vận hành.
- Relay không được nhận/log password, remote session token hoặc application payload.
- Error response không được xác nhận một rendezvous ID từng tồn tại trong quá khứ.
- WebRTC DTLS bảo vệ DataChannel; password chỉ truyền bên trong kênh đã mã hóa.
- Fingerprint từ SDP phải được ràng buộc với signaling session để tránh tráo peer giữa các session.

## 10. ERROR CONTRACT

| Error code             | Phạm vi             | Ý nghĩa                                              |
|------------------------|----------------------|-----------------------------------------------------|
| `invalid_agent`        | Agent registration   | Agent identity không hợp lệ                         |
| `rendezvous_conflict`  | Agent registration   | Rendezvous ID đang thuộc server online khác         |
| `server_unavailable`   | Client request       | Không có server active cho rendezvous ID            |
| `signaling_rejected`   | Signaling            | Agent từ chối yêu cầu                               |
| `signaling_timeout`    | Signaling            | Không hoàn tất offer/answer/ICE đúng hạn            |
| `invalid_signaling`    | Signaling            | Message hoặc state không hợp lệ                     |
| `rate_limited`         | Registration/request | Vượt giới hạn request                               |
| `p2p_unavailable`      | Peer connection      | ICE/DataChannel không tạo được đường trực tiếp      |

## 11. ACCEPTANCE CRITERIA

- [ ] Hai server ở hai mạng khác nhau đăng ký rendezvous ID đồng thời mà không xung đột.
- [ ] Client cung cấp rendezvous ID được ghép đúng agent connection.
- [ ] Rendezvous ID có ít nhất 128 bit entropy và không được dùng thay username/password.
- [ ] Relay chuyển đúng SDP offer, answer và ICE candidate theo signaling session.
- [ ] Relay từ chối cross-session signaling và không công khai registry.
- [ ] Password không xuất hiện trong signaling schema hoặc Relay log.
- [ ] Windows/Android/iOS WebRTC implementation có thể dùng cùng protocol version.
- [ ] Sau DataChannel open, server/client tự handshake password và tạo remote session.
- [ ] Application payload không đi qua Relay.
- [ ] ICE thất bại trả `p2p_unavailable`, không sinh TURN/Relay candidate.
- [ ] Relay disconnect không đóng P2P session đang active.
- [ ] Server disconnect xóa rendezvous mapping và signaling session chưa hoàn tất.

## 12. ĐIỂM PHẢI CHỐT TRONG DESIGN

1. Cơ chế enrollment và phát hành `agent_token` cho mỗi installation.
2. STUN service sử dụng trong production và chính sách thay thế khi STUN unavailable.
3. WebRTC implementation cụ thể: Windows/Python, Android và iOS.
4. Binary frame size, fragmentation và backpressure trên `stream` DataChannel.
5. Cách tích hợp asyncio network worker với PyQt mà không update UI ngoài UI thread.
6. Chính sách rate limit và thời gian lưu audit metadata.
7. Chính sách bảo vệ username/password 4 chữ số trước brute-force sau khi P2P DataChannel mở; mỗi peer connection
   phải bị đóng sau một lần xác thực thất bại và mọi lần thử mới phải đi qua signaling rate limit.

