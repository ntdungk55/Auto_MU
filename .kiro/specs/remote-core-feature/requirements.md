# Remote Core Feature Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Auto_MU cần một Remote Server dùng chung để Android hoặc thiết bị khác có thể kết nối tới các process/window đang được quản lý trong các tab AI Chat. Remote phải bị giới hạn quyền bởi người dùng Windows và không được điều khiển nhầm window.

**Mục tiêu:**

- Tạo feature độc lập tại `remote/`, nằm ngang hàng với `mcp/` và `src/`.
- Cung cấp một Remote Server dùng chung cho toàn bộ ứng dụng.
- Server chỉ được khởi động hoặc dừng bằng thao tác thủ công của Windows user; không tự động start/stop theo target.
- Chỉ cho phép start khi có ít nhất một game window được chọn trong AI Chat.
- Mỗi server chỉ phục vụ một remote client tại một thời điểm; session đó chỉ gắn với một window
  sau handshake. Client khác bị từ chối ngay, không xếp hàng chờ.
- Auto_MU Server tự tạo username 9 chữ số và password 6 chữ số cho mỗi lần Remote Server chạy.
- Đăng ký username với Central Relay để Internet client tìm đúng Auto_MU Server đang online.
- Không gửi password cho Central Relay; username chỉ dùng để phân biệt và định tuyến signaling.
- Thiết lập WebRTC P2P trực tiếp với client; Central Relay chỉ chuyển signaling và không mang dữ liệu remote.
- Xác thực password trực tiếp sau khi WebRTC DataChannel mã hóa đã mở.
- Internet mode là P2P-only; nếu không tạo được đường trực tiếp thì kết nối thất bại, không dùng TURN/Relay fallback.
- Mặc định các permission remote đều được bật sau khi xác thực.
- Người dùng Windows là admin, có quyền cấp/revoke từng permission.
- Bảo đảm event được xử lý theo thứ tự server nhận được.

**Cấu trúc bắt buộc:**

```text
remote/
  src/
    domain/
    application/
    infrastructure/
    logic/
    ui/
```

`remote/ui/` chỉ chứa thành phần UI thuộc feature remote. Vị trí tích hợp cuối cùng vào UI chính sẽ được quyết định ở design.

**Input/Output:**

"Relay tech" là `.kiro/specs/central-relay/technical-requirements.md`; "Android" là
`.kiro/specs/android-remote-client/requirements.md`.

| Loại   | Tác nhân        | Nội dung nghiệp vụ                                          | Chi tiết kỹ thuật                                |
|--------|-----------------|-------------------------------------------------------------|--------------------------------------------------|
| Input  | Windows user    | Nhấn Start server                                           | Lifecycle command (§3.1 Bước 1–2)               |
| Input  | Windows user    | Nhấn Stop server                                            | Lifecycle command (§3.1 Bước 1–2)               |
| Input  | Windows user    | Nhấn Cancel khi đang Start hoặc Stop                         | Lifecycle cancel (§3.1 Bước 2)                  |
| Input  | Windows user    | Bật hoặc tắt từng permission                                | Permission settings (§3.1 Bước 5)               |
| Input  | Windows user    | Tích hoặc bỏ tích window cho phép remote                      | Window allowlist (§6)                            |
| Input  | Windows user    | Revoke một session                                          | `session_revoked` (§1.1)                        |
| Input  | AI Chat         | Một tab chọn game window                                    | Window allowlist update (§6)                    |
| Input  | AI Chat         | Một tab bỏ chọn game window                                 | `targets_changed` (§1.1)                        |
| Input  | AI Chat         | Game window đang chọn bị đóng hoặc đổi identity              | `target_unavailable` (§1.1)                     |
| Input  | Remote client   | Gửi password và nhận diện thiết bị qua P2P đã mã hóa        | `auth_request` (§1.1–1.2; Relay tech §6.2)     |
| Input  | Remote client   | Chọn một window                                             | `target_select` (§1.1)                          |
| Input  | Remote client   | Yêu cầu bắt đầu hoặc dừng nhận frame                         | `stream_subscription` (§1.1)                    |
| Input  | Remote client   | Yêu cầu bắt đầu hoặc dừng nhận Game State                    | `game_state_subscription` (§1.1)                 |
| Input  | Remote client   | Gửi chat message                                            | `chat_submit` (§1.1)                            |
| Input  | Remote client   | Xem danh sách MCP tools                                     | `tool_catalog_request` (§1.1)                   |
| Input  | Remote client   | Gọi tool chỉ đọc                                            | `tool_call` + readonly permission (§1.1)        |
| Input  | Remote client   | Gọi tool thay đổi trạng thái                                | `tool_call` + mutating permission (§1.1)        |
| Input  | Remote client   | Hủy tool call đang chạy                                     | `tool_cancel` (§1.1)                            |
| Input  | Remote client   | Ngắt kết nối                                                | Peer close (§1.2)                                |
| Input  | Remote client   | Báo định kỳ vẫn còn kết nối                                  | `client_heartbeat` (§1.1–1.2)                   |
| Input  | Central Relay   | Xác nhận server đã online                                   | `server_registered` (Relay tech §4.1)            |
| Input  | Central Relay   | Username đang được máy khác dùng                             | `username_conflict` (Relay tech §10)             |
| Input  | Central Relay   | Có client muốn kết nối                                      | `incoming_connection` (Relay tech §4.3)          |
| Input  | Central Relay   | Thông tin thiết lập kết nối từ client                       | `webrtc_offer/answer`, `ice_*` (Relay tech §4.3) |
| Input  | Central Relay   | Client đã hủy hoặc ngắt kết nối                             | `signaling_close` (Relay tech §4.3)              |
| Input  | Central Relay   | Hết thời gian thiết lập kết nối                             | `signaling_timeout` (Relay tech §10)             |
| Input  | Central Relay   | Client báo không kết nối trực tiếp được                       | Forward `p2p_failed` (Relay tech §4.3)           |
| Output | Windows user    | Trạng thái server hiện tại                                  | `stopped/starting/running/stopping/error` (§3.1) |
| Output | Windows user    | Username và password của lần chạy                            | §6                                               |
| Output | Windows user    | Trạng thái kết nối tới Central Relay                         | UI §4                                           |
| Output | Windows user    | Thiết bị đang kết nối và window đã chọn                      | UI §4                                           |
| Output | Windows user    | Lỗi khi Start hoặc Stop                                     | §3.3                                             |
| Output | AI Chat         | Khóa toàn bộ AI Chat khi đang Start hoặc Stop                | §3.1 Bước 2                                      |
| Output | AI Chat         | Mở khóa AI Chat khi Start/Stop kết thúc                      | §3.1 Bước 2                                      |
| Output | Remote client   | Xác thực thành công kèm session và permission hiện tại      | `control` DataChannel (§1.2)                     |
| Output | Remote client   | Xác thực thất bại (lỗi chung)                               | Relay tech §6.2                                  |
| Output | Remote client   | Thiết bị hiện tại đang tạm khóa đăng nhập                   | `auth_locked` (Relay tech §6.2, §10)             |
| Output | Remote client   | Danh sách window được phép chọn                             | `targets_snapshot` (§1.1)                        |
| Output | Remote client   | Danh sách window được phép đã thay đổi                      | `targets_changed` (§1.1)                         |
| Output | Remote client   | Permission đã thay đổi                                      | `permission_changed` (§1.1)                      |
| Output | Remote client   | Frame ảnh của window đã chọn                                | `frame` + JPEG binary (§1.1)                     |
| Output | Remote client   | Game State của window đã chọn                               | `game_state` (§1.1)                              |
| Output | Remote client   | Danh sách MCP tools                                         | `tool_catalog` (§1.1)                            |
| Output | Remote client   | Trạng thái xử lý chat, tool event và câu trả lời           | `chat_event`, `tool_event` (§1.1)                |
| Output | Remote client   | Từ chối do thiếu quyền                                      | `permission_denied` (§1.1)                       |
| Output | Remote client   | Server đang bận với thiết bị khác                            | `server_busy` (Relay tech §10)                   |
| Output | Remote client   | Window đã chọn không còn khả dụng                            | `target_unavailable` (§1.1)                      |
| Output | Remote client   | Session bị thu hồi                                          | `session_revoked` (§1.1)                         |
| Output | Remote client   | Tool call hết thời gian                                     | `tool_timeout` (§1.1)                            |
| Output | Remote client   | Không kết nối trực tiếp được                                 | `p2p_unavailable` (§1.2)                         |
| Output | Remote client   | Server dừng và đóng kết nối                                  | Peer close (§1.2)                                |
| Output | Central Relay   | Báo "tôi online" kèm username và thông tin lần chạy        | `server_register` (Relay tech §4.1)              |
| Output | Central Relay   | Báo định kỳ "tôi vẫn còn online"                            | Agent heartbeat (Relay tech §8)                  |
| Output | Central Relay   | Đồng ý thiết lập kết nối với client                          | `connection_accept` (Relay tech §4.3)            |
| Output | Central Relay   | Từ chối client trước khi thiết lập kết nối                   | `connection_reject` (Relay tech §4.3)            |
| Output | Central Relay   | Từ chối client vì đang bận với client khác                   | `connection_reject` + `reason: busy` (Relay tech §4.3) |
| Output | Central Relay   | Gửi thông tin thiết lập kết nối cho client                   | `webrtc_offer/answer`, `ice_*` (Relay tech §4.3) |
| Output | Central Relay   | Báo kết nối trực tiếp thành công                             | `p2p_connected` (Relay tech §4.3)                |
| Output | Central Relay   | Báo kết nối trực tiếp thất bại                               | `p2p_failed` (Relay tech §4.3)                   |

**Permissions mặc định:**

| Permission             | Mặc định | Ý nghĩa                                      |
|------------------------|----------|----------------------------------------------|
| `connect`              | Bật      | Đăng nhập bằng username/password server cấp  |
| `view_stream`          | Bật      | Cho phép nhận frame                          |
| `view_game_state`      | Bật      | Cho phép nhận Game State                     |
| `send_chat`            | Bật      | Cho phép gửi message mới vào AI Chat         |
| `discover_tools`       | Bật      | Cho phép xem danh sách MCP tools             |
| `call_readonly_tools`  | Bật      | Cho phép gọi tool chỉ đọc                    |
| `call_mutating_tools`  | Bật      | Cho phép gọi tool thay đổi trạng thái        |

**Parameters:**

| Tham số                    | Kiểu   | Mô tả                                        | Mặc định                  |
|----------------------------|--------|----------------------------------------------|---------------------------|
| `stream_fps`               | float  | Cadence stream tối đa                        | `2.0`                     |
| `max_frame_queue`          | int    | Số frame tối đa giữ cho một client           | `1`                       |
| `tool_timeout_seconds`     | float  | Timeout cho một tool call                    | `45.0`                    |
| `max_clients`              | int    | Số remote client tối đa tại một thời điểm    | `1`                       |
| `client_heartbeat_interval`| float  | Chu kỳ client báo còn kết nối                | `15.0` giây               |
| `client_heartbeat_timeout` | float  | Không nhận heartbeat quá thời gian này thì giải phóng session | `45.0` giây        |
| `signaling_url`            | string | Central Relay WSS endpoint                   | Cấu hình triển khai       |
| `stun_urls`                | list   | STUN service dùng cho ICE                    | Cấu hình triển khai       |
| `p2p_connect_timeout`      | float  | Timeout tạo WebRTC DataChannel               | `20.0` giây               |
| `auth_timeout_seconds`     | float  | Timeout xác thực sau khi control channel mở  | `10.0` giây               |
| `auth_max_failures`        | int    | Số lần sai liên tiếp của một thiết bị        | `5`                       |
| `auth_lockout_seconds`     | float  | Thời gian khóa riêng thiết bị                | `300.0` giây              |
| `frame_chunk_bytes`        | int    | Payload tối đa của một frame chunk           | `16384`                   |
| `max_frame_bytes`          | int    | Kích thước JPEG tối đa                       | `8388608`                 |

## 1.1. Hợp đồng dữ liệu realtime

- Mọi JSON control message phải có `type`, `protocol_version`, `remote_session_id` sau xác thực, `request_id` cho
  request/response và timestamp.
- Client có thể gửi `auth_request`, `target_select`, `stream_subscription`, `game_state_subscription`, `chat_submit`,
  `tool_catalog_request`, `tool_call`, `tool_cancel` và `client_heartbeat` khi đúng state/permission.
- Server có thể gửi `auth_result`, `targets_snapshot`, `targets_changed`, `permission_snapshot`,
  `permission_changed`, `chat_event`, `tool_event`, `tool_timeout`, `permission_denied`, `target_unavailable` và
  `session_revoked`.
- Server gửi frame tối đa 2 frame/giây. Mỗi frame có `frame_start` gồm `frame_id`, `sequence`, `timestamp`,
  `mime=image/jpeg`, `total_size`, `chunk_count`, sau đó là các binary chunk có `frame_id` và `chunk_index`.
- Mỗi chunk tối đa 16 KiB và tổng một JPEG tối đa 8 MiB. Frame vượt giới hạn, thiếu chunk hoặc bị frame mới hơn thay
  thế phải bị drop; server không giữ queue quá một frame.
- Server gửi JSON `game_state` tối đa 1 lần/giây, gồm `sequence`, `timestamp`, `target_hwnd` và `data`.
- Server gửi `targets_changed` khi allowlist window thay đổi và `session_revoked` khi session không còn target hợp lệ.
- Client phải bỏ frame cũ khi frame mới đã đến; server không giữ queue frame quá một frame.
- Client phải xử lý `permission_denied`, `target_unavailable`, `session_revoked`, timeout và peer close.
- Client gửi `client_heartbeat` mỗi 15 giây sau xác thực. Server xử lý heartbeat độc lập với chat/tool và đóng session
  nếu không nhận heartbeat trong 45 giây.
- Yêu cầu kết nối khi server đang có client khác bị từ chối bằng lỗi server bận trước khi kiểm tra password.

## 1.2. Hợp đồng Internet WebRTC P2P

- Auto_MU Agent giữ một outbound WSS signaling connection tới Central Relay trong khi Internet remote được bật.
- Khi Remote Server start, Auto_MU tự tạo `server_run_id`, username 9 chữ số và password 6 chữ số bằng CSPRNG.
- Agent đăng ký `server_run_id` và username với Relay; password chỉ tồn tại trên Auto_MU Server.
- Nếu Relay trả `username_conflict`, Auto_MU tạo username mới, cập nhật dialog `Remote Server Status` và đăng ký lại;
  password không đổi nếu server run vẫn giữ nguyên.
- Client tìm server bằng username; Relay tạo signaling session và chỉ chuyển SDP offer/answer cùng ICE candidate.
- Username không phải bí mật và không cấp quyền tạo remote session.
- Auto_MU tạo WebRTC peer connection riêng cho mỗi client request được chấp nhận.
- ICE chỉ sử dụng host/server-reflexive candidate qua STUN; không cấu hình TURN hoặc relay candidate.
- `connection_request` phải mang `client_instance_id` ngẫu nhiên 128 bit được lưu bền vững theo bản cài client.
- Sau khi `control` DataChannel mở, client phải gửi `auth_request` gồm password và cùng `client_instance_id` trong
  tối đa 10 giây; ID phải khớp signaling session.
- Auto_MU so khớp password, tạo remote session và trả session token/permission snapshot trực tiếp qua P2P.
- Auto_MU đếm sai password theo `(server_run_id, client_instance_id)`. Sau `auth_max_failures`, chỉ thiết bị đó nhận
  `auth_locked` trong `auth_lockout_seconds`; username/server và thiết bị khác không bị khóa.
- Xác thực thành công, hết lockout hoặc server restart reset bộ đếm của thiết bị tương ứng.
- Chat, game state, JPEG frame, tool call và remote command chỉ đi qua WebRTC DataChannel.
- Central Relay không được nhận password hoặc application payload.
- Khi ICE/DataChannel không connected trước timeout, Auto_MU cleanup peer connection và trả `p2p_unavailable`.
- Signaling disconnect sau khi P2P active không được chủ động đóng remote session hiện tại.
- Client slot dùng state `available → reserved → authenticating → active → releasing → available`.
- Auto_MU reserve slot atomically trước `connection_accept`; request khác trong `reserved`, `authenticating` hoặc
  `active` bị từ chối bằng `connection_reject` với `reason: busy`.
- Signaling timeout 30 giây tính từ lúc Relay tạo session; P2P timeout 20 giây tính từ `connection_accept`; auth
  timeout 10 giây tính từ lúc `control` open. Timeout/fail/peer close/revoke phải cleanup và release slot idempotently.

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌────────────────────────┐
│ Windows chọn target    │
└───────────┬────────────┘
            ▼
┌────────────────────────┐
│ User nhấn Start         │
└───────────┬────────────┘
            ▼
┌────────────────────────┐
│ Có target hợp lệ?       │
└──────┬───────────┬──────┘
     No│           │Yes
       ▼           ▼
 Start disabled  Starting dialog
                   │
                   ▼
          Running / credentials
                   │
                   ▼
┌────────────────────────┐
│ Remote connect/handshake│
└───────────┬────────────┘
            ▼
      ┌─────┴─────┐
      │ Được phép?│
      └──┬─────┬──┘
       No│     │Yes
         ▼     ▼
      Denied  Chọn một window
                │
                ▼
        Khóa target cho session
                │
                ▼
        Windows cấp permissions
                │
                ▼
        Xử lý event theo FIFO
                │
                ▼
        Revoke/target invalid/close
                │
                ▼
          Dừng session sạch sẽ
                │
                ▼
       User nhấn Stop → Stopping
                │
                ▼
              Stopped
```

## 2.1. LUỒNG INTERNET P2P

```text
Remote Server start
        ↓
Tạo username/password local
        ↓
Đăng ký username với Relay
        ↓
Client tìm server theo username
        ↓
Server đang bận? ── Yes → Từ chối (busy)
        ↓ No
Relay ghép signaling session
        ↓
Trao đổi SDP + ICE qua Relay
        ↓
WebRTC DataChannel connected?
   No ─┴─ Yes
   ↓       ↓
P2P lỗi   Client gửi password trực tiếp
           ↓
       Server xác thực
           ↓
       Tạo remote session
           ↓
       Dữ liệu đi P2P
```

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Quản lý vòng đời server**

- Input: Thao tác Start/Stop của Windows user và danh sách game window đang được AI Chat chọn.
- Process: Quản lý một Remote Server dùng chung với state machine `stopped → starting → running → stopping → stopped`; lỗi chuyển sang `error`.
- Output: Lifecycle state được đồng bộ tới mọi tab AI Chat.

Start chỉ được enable khi có ít nhất một game window được chọn. Việc chọn target không tự khởi động server và việc bỏ chọn target cuối cùng không tự dừng server. Nếu không còn target trong lúc server vẫn chạy, các session bị ảnh hưởng được invalidate nhưng server giữ trạng thái `running` cho tới khi user nhấn Stop.

**Bước 2: Start/Stop và cancellation**

- Khi user nhấn Start, server chuyển sang `starting`, mở dialog tiến trình và khóa toàn bộ UI của tất cả tab AI Chat.
- Khi user nhấn Stop, server chuyển sang `stopping`, mở dialog tiến trình và khóa toàn bộ UI của tất cả tab AI Chat.
- Trong `starting` hoặc `stopping`, chỉ dialog tiến trình và nút `Cancel` nhận tương tác.
- Cancel Start phải hủy operation đang chạy, cleanup tài nguyên đã tạo và đưa server về `stopped`.
- Cancel Stop phải hủy operation đang chạy, khôi phục tài nguyên cần thiết và đưa server về `running` mà không làm credentials/session còn hiệu lực bị thay đổi.
- Chỉ một lifecycle operation được tồn tại tại một thời điểm; Start/Stop/Cancel lặp lại phải idempotent.
- Khi operation hoàn tất, thất bại hoặc bị cancel, toàn bộ AI Chat được unlock và phản ánh cùng một trạng thái.

**Bước 3: Handshake**

- Input: Remote connection, `client_instance_id`, username 9 chữ số và password 6 chữ số hiển thị trong dialog
  `Remote Server Status` khi server đang `running`.
- Process: Dùng username để Relay ghép signaling; Auto_MU reserve slot atomically. Sau khi WebRTC DataChannel mã
  hóa mở, client gửi password và cùng `client_instance_id` trực tiếp để Auto_MU tự xác thực. Relay không nhận hoặc
  kiểm tra password.
- Process chung: Chỉ một thiết bị được thiết lập hoặc giữ kết nối tại một thời điểm; thiết bị khác bị từ chối ngay
  bằng lỗi server bận. Session dùng permission mặc định và vẫn có thể bị Windows admin revoke.
- Output: Authenticated session cùng permission snapshot hiện tại.

**Bước 4: Chọn target**

- Input: Remote chọn một window trong danh sách đã được tích trong Settings.
- Process: Kiểm tra `window_title`, `process_name`, `pid`, `hwnd`, `tab_name`, PID và creation time; sau khi chấp nhận thì session bị khóa vào đúng một target.
- Output: `target_window_identity` cố định cho session.

**Bước 5: Admin cấp quyền**

- Input: Settings global của Windows user.
- Process: Enable hoặc disable từng permission cho remote session hiện tại.
- Output: Permission snapshot được gửi cho remote.

**Bước 6: Xử lý event**

- Input: Stream request, state request, chat message hoặc tool request.
- Process: Đưa event vào queue chung theo thứ tự server nhận được; event đến trước được xử lý trước; kiểm tra permission và target trước khi xử lý.
- Output: Result, error hoặc event bị từ chối.

**Bước 7: Invalidate và cleanup**

- Input: Window đóng, identity đổi, tab bỏ chọn target, server stop hoặc admin revoke.
- Process: Thu hồi quyền, ngừng stream/tool mutate, đóng WebRTC peer connection và giải phóng worker.
- Output: Remote nhận trạng thái `target_unavailable`, `revoked` hoặc `closed`.

### 3.2. Các trường hợp ngoại lệ

**Case 1: Client thứ hai kết nối khi server đang bận**

- Chỉ một request được chuyển atomically từ `available` sang `reserved`; request cạnh tranh nhận lỗi server bận.
- Server ở `reserved`, `authenticating` hoặc `active` từ chối client mới ngay.
- Không xếp hàng chờ; session hiện tại không bị ảnh hưởng.
- Slot được giải phóng idempotently khi signaling/P2P/auth timeout, xác thực sai, client ngắt, bị revoke, bị
  invalidate hoặc server không nhận heartbeat trong `client_heartbeat_timeout`.
- Client mất mạng rồi kết nối lại trước khi slot cũ được giải phóng cũng nhận lỗi server bận.

**Case 2: Lần thử đăng nhập sai khi đã có client**

- Client mới bị từ chối vì server bận trước khi kiểm tra password; không tính vào bộ đếm lockout.

**Case 3: Remote yêu cầu đổi window**

- Không đổi target trong session hiện tại.
- Phải tạo handshake/session mới.

**Case 4: Client chậm nhận frame**

- Drop frame cũ và giữ frame mới nhất.
- Không tăng queue vô hạn.

**Case 5: Windows admin revoke quyền**

- Quyền bị thu hồi ngay theo loại permission.
- `view_stream`: dừng stream của remote.
- `view_game_state`: dừng gửi state của remote.
- `send_chat`: xóa message remote đang chờ; lượt AI đang chạy được hoàn tất và message đã hiển thị không bị xóa.
- `discover_tools`: xóa tool catalog remote.
- `call_readonly_tools`: từ chối hoặc hủy readonly request đang chờ.
- `call_mutating_tools`: dừng mutate request.

**Case 6: Lifecycle operation đồng thời**

- Khi server đang `starting` hoặc `stopping`, mọi yêu cầu lifecycle mới ngoài Cancel bị từ chối hoặc gộp idempotently.
- Trạng thái shared server và trạng thái khóa UI phải nhất quán trên mọi tab AI Chat.

**Case 7: Target cuối cùng bị bỏ chọn khi server đang chạy**

- Invalidate session đang binding vào target bị bỏ chọn.
- Không tự động dừng server; user phải nhấn Stop.
- Nút Start chỉ được enable trở lại sau khi có ít nhất một target hợp lệ.

**Case 8: Username bị trùng trên Central Relay**

- Tạo username mới, cập nhật UI và đăng ký lại trong cùng server run.
- Không gửi password cho Relay trong bất kỳ lần đăng ký nào.

**Case 9: Internet P2P không thiết lập được**

- Trả `p2p_unavailable`, đóng peer connection và không tạo remote session.
- Không fallback qua Central Relay hoặc TURN.

**Case 10: Signaling bị mất sau khi P2P active**

- Session P2P hiện tại tiếp tục nếu DataChannel vẫn hoạt động.
- Server không nhận Internet client mới cho tới khi agent đăng ký signaling lại.

**Case 11: Password Internet không hợp lệ**

- Auto_MU trả lỗi chung trên DataChannel và đóng peer connection.
- Không tiết lộ target hoặc permission trước khi xác thực thành công.
- Sau 5 lần sai liên tiếp của cùng `client_instance_id`, chỉ thiết bị đó bị `auth_locked` trong 300 giây.
- Thiết bị khác và username/server không bị khóa; Relay vẫn áp dụng rate limit theo source IP.

### 3.3. Xử lý lỗi

| Lỗi                           | Xử lý                                                         |
|-------------------------------|---------------------------------------------------------------|
| Token/handshake không hợp lệ  | Từ chối kết nối, không tiết lộ thông tin target               |
| Server đang bận               | Từ chối client mới ngay, không xếp hàng                      |
| Target không tồn tại          | Không tạo session active, trả `target_unavailable`            |
| Permission bị thiếu           | Từ chối event và ghi audit event                              |
| Tool timeout                  | Cancel hoặc đánh dấu timeout, trả lỗi có mã                   |
| Server stop                   | Đóng toàn bộ session, worker và queue                         |
| Start khi chưa có target      | Không chạy operation; giữ `stopped` và disable Start          |
| Start/Stop bị hủy             | Quay về stable state trước operation và unlock AI Chat        |
| Start/Stop thất bại           | Chuyển `error`, hiển thị lỗi và unlock AI Chat                |
| Identity thay đổi             | Thu hồi quyền mutate và ngắt target binding                   |
| Relay unavailable             | Báo Internet remote unavailable; local feature vẫn hoạt động  |
| Username conflict             | Tạo username mới, cập nhật UI và đăng ký lại                 |
| WebRTC timeout/ICE failed     | Trả `p2p_unavailable`, cleanup và không fallback              |
| Authentication timeout       | Trả `auth_timeout`, đóng peer và giải phóng slot              |
| P2P password sai              | Từ chối trực tiếp, đóng peer connection                       |
| Một thiết bị sai quá 5 lần    | Chỉ thiết bị đó nhận `auth_locked` trong thời gian khóa       |

## 4. PHÁC THẢO UI

**Khung tóm tắt dùng chung ở trên cùng AI Chat workspace:**

Chỉ có một khung Remote Server. Khung nằm bên ngoài và phía trên toàn bộ dãy tab cùng mọi thành phần bên trong các tab AI Chat; không lặp lại khung trong từng tab.

```text
┌──────────────────────────────────────────┐
│ Remote Server                            │
├──────────────────────────────────────────┤
│ Status: Running                          │
│ Connected device: Device A               │
│ [Open Remote Server Status]              │
│ [Running — Stop Server]                  │
└──────────────────────────────────────────┘
```

Khi server `stopped`, action button hiển thị `[Stopped — Start Server]` và bị disable nếu chưa có game window được chọn. Khi server ở `error`, khung hiển thị tóm tắt lỗi và cho phép mở dialog chi tiết.

**Dialog `Remote Server Status`:**

```text
┌──────────────────────────────────────────┐
│ Remote Server Status                     │
├──────────────────────────────────────────┤
│ Status: Running                          │
│ Signaling: Online                        │
│ Internet transport: WebRTC P2P-only      │
│ Username: 123 456 789  Password: 567890  │
│ Active session                           │
│ [device] [target] [permissions] [revoke] │
│                                          │
│ [Running — Stop Server]          [Close] │
└──────────────────────────────────────────┘
```

**Dialog lifecycle modal:**

```text
┌──────────────────────────────────────────┐
│ Starting/Stopping Remote Server...       │
├──────────────────────────────────────────┤
│ Đang xử lý. Toàn bộ AI Chat đã bị khóa.  │
│                                 [Cancel] │
└──────────────────────────────────────────┘
```

UI cụ thể và vị trí tích hợp sẽ được mô tả trong design; requirements này không quyết định layout cuối cùng.

## 5. Ngoài phạm vi

- Không triển khai hosting/runtime của Central Relay trong feature Remote Core.
- Không triển khai Cloudflare Tunnel; Relay có thể được public trực tiếp hoặc qua hạ tầng bên ngoài.
- Không triển khai TURN hoặc data relay fallback.
- Không triển khai Device ID/QR/pairing hoàn chỉnh.
- Không triển khai Codex CLI.
- Không mô tả Android remote control UI trong feature core.
- Không tạo server riêng cho từng remote client.

## 6. Credentials và window allowlist

- Mỗi lần server start tạo username 9 chữ số và password 6 chữ số.
- Username được đăng ký với Central Relay khi Internet remote bật; password không được gửi ra Relay.
- Username chỉ dùng để tìm agent connection, không phải bí mật và không cấp permission.
- Credentials hiển thị trong dialog `Remote Server Status` khi server `running`; password không ghi vào log.
- Credentials mất hiệu lực khi server stop.
- Không rotate credentials khi server đang chạy trong phạm vi MVP; Stop rồi Start tạo bộ credentials mới và đóng
  session cũ.
- Trong Internet mode, client chỉ gửi password sau khi WebRTC `control` DataChannel mã hóa đã mở.
- Settings là global cho shared server.
- Settings có bảng checkbox window; mặc định mọi window trong bảng được tích.
- Bảng cập nhật khi AI Chat chọn game window hoặc khi game window đóng thành công.
- Remote chỉ được chọn window đang được tích; bỏ tích window đang binding sẽ ngắt session đó ngay.

## 7. Acceptance Criteria

- [ ] Chọn window không tự động start server và bỏ chọn window cuối cùng không tự động stop server.
- [ ] Start bị disable khi chưa có game window được chọn.
- [ ] Start/Stop thủ công điều khiển duy nhất một shared server.
- [ ] AI Chat workspace có đúng một khung Remote Server dùng chung nằm trên cùng, bên ngoài và phía trên toàn bộ dãy tab cùng mọi thành phần chat.
- [ ] Khung tóm tắt dùng chung có trạng thái, thiết bị đang kết nối, nút mở `Remote Server Status` và nút Start/Stop thể hiện stable state hiện tại.
- [ ] Dialog `Remote Server Status` hiển thị username/password, session và action Start/Stop phù hợp.
- [ ] `starting` hoặc `stopping` khóa toàn bộ UI của tất cả AI Chat; chỉ dialog lifecycle và Cancel hoạt động.
- [ ] Cancel Start trả về `stopped`; Cancel Stop trả về `running`.
- [ ] Hoàn tất, lỗi hoặc cancel lifecycle operation luôn unlock AI Chat.
- [ ] Không có hai lifecycle operation chạy đồng thời.
- [ ] Auto_MU tự tạo username 9 chữ số và password 6 chữ số; Central Relay chỉ nhận username.
- [ ] Username không cấp quyền remote khi thiếu password đúng.
- [ ] Mỗi bản cài client có `client_instance_id` ngẫu nhiên 128 bit và gửi cùng một giá trị trong signaling/auth.
- [ ] Sau 5 lần sai password, chỉ thiết bị có cùng `client_instance_id` bị `auth_locked` trong 300 giây.
- [ ] Khi đã có một client đang thiết lập hoặc đã kết nối, client mới bị từ chối ngay bằng lỗi server bận.
- [ ] Client slot được reserve atomically và mọi đường fail/timeout/close đều release idempotently.
- [ ] Không nhận heartbeat của client trong 45 giây thì server đóng session và nhận client mới.
- [ ] Heartbeat client gửi mỗi 15 giây sau xác thực và được xử lý độc lập với chat/tool.
- [ ] SDP offer/answer và ICE candidate được trao đổi qua đúng signaling session.
- [ ] Password Internet được Auto_MU xác thực trực tiếp trên DataChannel mã hóa.
- [ ] Chat, frame, game state và remote command đi trực tiếp qua WebRTC P2P.
- [ ] Frame chia chunk tối đa 16 KiB, tổng JPEG tối đa 8 MiB và queue không vượt một frame.
- [ ] ICE/DataChannel thất bại trả `p2p_unavailable` và không fallback.
- [ ] Signaling disconnect không chủ động đóng P2P session đang active.
