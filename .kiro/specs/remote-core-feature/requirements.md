# Remote Core Feature Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Auto_MU cần một Remote Server dùng chung để Android hoặc thiết bị khác có thể kết nối tới các process/window đang được quản lý trong các tab AI Chat. Remote phải bị giới hạn quyền bởi người dùng Windows và không được điều khiển nhầm window.

**Mục tiêu:**

- Tạo feature độc lập tại `remote/`, nằm ngang hàng với `mcp/` và `src/`.
- Cung cấp một Remote Server dùng chung cho toàn bộ ứng dụng.
- Server chỉ được khởi động hoặc dừng bằng thao tác thủ công của Windows user; không tự động start/stop theo target.
- Chỉ cho phép start khi có ít nhất một game window được chọn trong AI Chat.
- Cho phép nhiều remote session kết nối nhưng mỗi session chỉ gắn với một window sau handshake.
- Auto_MU Server tự tạo `rendezvous_id` và username/password cho mỗi lần Remote Server chạy.
- Đăng ký rendezvous ID với Central Relay để Internet client tìm đúng Auto_MU Server đang online.
- Không gửi username/password cho Central Relay; rendezvous ID chỉ dùng để phân biệt và định tuyến signaling.
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

| Loại   | Mô tả                                      | Ví dụ                                                  |
|--------|--------------------------------------------|--------------------------------------------------------|
| Input  | Kết nối, handshake, yêu cầu quyền, event   | `connect`, `subscribe_stream`, `chat`                  |
| Input  | Window identity do remote chọn lúc đầu     | `pid`, `hwnd`, `creation_time`                         |
| Input  | Signaling Internet và WebRTC negotiation  | Offer, answer, ICE candidate                            |
| Output | Trạng thái server/session                  | `stopped`, `starting`, `running`, `stopping`, `error`  |
| Output | Frame, state, tool result hoặc message     | JSON metadata và binary JPEG frame                     |
| Output | Trạng thái P2P                             | `connecting`, `connected`, `p2p_unavailable`           |

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
| `host`                     | string | Địa chỉ bind của Remote Server               | `127.0.0.1`               |
| `port`                     | int    | Cổng HTTP/WebSocket                          | `8765`                    |
| `stream_fps`               | float  | Cadence stream tối đa                        | `2.0`                     |
| `max_frame_queue`          | int    | Số frame tối đa giữ cho một client           | `1`                       |
| `tool_timeout_seconds`     | float  | Timeout cho một tool call                    | `45.0`                    |
| `max_mutating_sessions`    | int    | Số session mutate đồng thời trên một target  | `1`                       |
| `signaling_url`            | string | Central Relay WSS endpoint                   | Cấu hình triển khai       |
| `stun_urls`                | list   | STUN service dùng cho ICE                    | Cấu hình triển khai       |
| `p2p_connect_timeout`      | float  | Timeout tạo WebRTC DataChannel               | `20.0` giây               |

## 1.1. Hợp đồng LAN transport realtime

- Bootstrap dùng HTTP: `GET /status`, `POST /handshake`, `POST /sessions/{session_id}/target`.
- Sau khi bind target, client mở WebSocket tại `/sessions/{session_id}/stream` trên cùng port.
- WebSocket bắt buộc gửi `Authorization: Bearer {session_id}`.
- Server gửi binary JPEG frame tối đa 2 frame/giây; trước mỗi binary frame gửi JSON `frame` gồm `sequence`, `timestamp`, `mime`, `size`.
- Server gửi JSON `game_state` tối đa 1 lần/giây, gồm `sequence`, `timestamp`, `target_hwnd` và `data`.
- Server gửi JSON `targets_changed` khi allowlist window thay đổi và `session_revoked` khi session không còn target hợp lệ.
- Client phải bỏ frame cũ khi frame mới đã đến; server không giữ queue frame quá một frame cho mỗi client.
- Client phải xử lý `permission_denied`, `target_unavailable`, `session_revoked`, timeout và WebSocket close.
- Các API session ngoài handshake đều yêu cầu `Authorization` tương ứng với `session_id`.

LAN mode giữ HTTP/WebSocket contract hiện tại và không phụ thuộc Central Relay. LAN mode và Internet P2P mode
là hai transport riêng; Internet P2P thất bại không được tự động chuyển sang LAN transport.

## 1.2. Hợp đồng Internet WebRTC P2P

- Auto_MU Agent giữ một outbound WSS signaling connection tới Central Relay trong khi Internet remote được bật.
- Khi Remote Server start, Auto_MU tự tạo `server_run_id`, `rendezvous_id` ngẫu nhiên ít nhất 128 bit, username
  4 chữ số và password 4 chữ số.
- Agent đăng ký `server_run_id` và `rendezvous_id` với Relay; username/password chỉ tồn tại trên Auto_MU Server.
- Nếu Relay trả `rendezvous_conflict`, Auto_MU tạo rendezvous ID mới và đăng ký lại; username/password không đổi
  nếu server run vẫn giữ nguyên.
- Client tìm server bằng rendezvous ID; Relay tạo signaling session và chỉ chuyển SDP offer/answer cùng ICE candidate.
- Rendezvous ID không thay thế username/password và không cấp quyền tạo remote session.
- Auto_MU tạo WebRTC peer connection riêng cho mỗi client request được chấp nhận.
- ICE chỉ sử dụng host/server-reflexive candidate qua STUN; không cấu hình TURN hoặc relay candidate.
- Sau khi `control` DataChannel mở, client gửi password trực tiếp cho Auto_MU.
- Auto_MU so khớp password, tạo remote session và trả session token/permission snapshot trực tiếp qua P2P.
- Chat, game state, JPEG frame, tool call và remote command chỉ đi qua WebRTC DataChannel.
- Central Relay không được nhận password hoặc application payload.
- Khi ICE/DataChannel không connected trước timeout, Auto_MU cleanup peer connection và trả `p2p_unavailable`.
- Signaling disconnect sau khi P2P active không được chủ động đóng remote session hiện tại.
- Một agent signaling connection phải multiplex được nhiều client signaling session.

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
Tạo rendezvous ID và
username/password local
        ↓
Đăng ký rendezvous ID với Relay
        ↓
Client tìm server theo rendezvous ID
        ↓
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

- Input: Remote connection và username/password 4 chữ số hiển thị trong dialog `Remote Server Status` khi server đang `running`.
- Process LAN: Xác thực qua HTTP, tạo `session_id` và tiếp tục LAN transport hiện tại.
- Process Internet: Dùng rendezvous ID để Relay ghép signaling; sau khi WebRTC DataChannel mã hóa mở, client gửi
  username/password trực tiếp và Auto_MU tự xác thực. Relay không nhận hoặc kiểm tra credentials.
- Process chung: Nhiều thiết bị có thể đăng nhập đồng thời bằng cùng credentials; mỗi thiết bị có session riêng,
  dùng permission mặc định và vẫn có thể bị Windows admin revoke.
- Output: Authenticated session cùng permission snapshot hiện tại.

**Bước 4: Chọn target**

- Input: Remote chọn một window trong danh sách đã được tích trong Settings.
- Process: Kiểm tra `window_title`, `process_name`, `pid`, `hwnd`, `tab_name`, PID và creation time; sau khi chấp nhận thì session bị khóa vào đúng một target.
- Output: `target_window_identity` cố định cho session.

**Bước 5: Admin cấp quyền**

- Input: Settings global của Windows user.
- Process: Enable hoặc disable từng permission cho tất cả remote session.
- Output: Permission snapshot được gửi cho remote.

**Bước 6: Xử lý event**

- Input: Stream request, state request, chat message hoặc tool request.
- Process: Đưa event vào queue chung theo thứ tự server nhận được; event đến trước được xử lý trước; kiểm tra permission và target trước khi xử lý.
- Output: Result, error hoặc event bị từ chối.

**Bước 7: Invalidate và cleanup**

- Input: Window đóng, identity đổi, tab bỏ chọn target, server stop hoặc admin revoke.
- Process: Thu hồi quyền, ngừng stream/tool mutate, đóng LAN socket hoặc WebRTC peer connection và giải phóng worker.
- Output: Remote nhận trạng thái `target_unavailable`, `revoked` hoặc `closed`.

### 3.2. Các trường hợp ngoại lệ

**Case 1: Nhiều client cùng kết nối**

- Mỗi client có session riêng.
- Không dùng chung target identity nếu chưa hoàn tất handshake.

**Case 2: Hai session cùng gọi tool mutate**

- Chỉ một session được giữ control lease trên một target.
- Session còn lại nhận lỗi busy/denied.

**Case 3: Remote yêu cầu đổi window**

- Không đổi target trong session hiện tại.
- Phải tạo handshake/session mới.

**Case 4: Client chậm nhận frame**

- Drop frame cũ và giữ frame mới nhất.
- Không tăng queue vô hạn.

**Case 5: Windows admin revoke quyền**

- Quyền bị thu hồi ngay theo loại permission.
- `view_stream`: dừng stream của tất cả remote.
- `view_game_state`: dừng gửi state của tất cả remote.
- `send_chat`: xóa message remote đang chờ; lượt AI đang chạy được hoàn tất và message đã hiển thị không bị xóa.
- `discover_tools`: xóa tool catalog remote.
- `call_readonly_tools`: từ chối hoặc hủy readonly request đang chờ.
- `call_mutating_tools`: thu hồi control lease và dừng mutate request.

**Case 6: Lifecycle operation đồng thời**

- Khi server đang `starting` hoặc `stopping`, mọi yêu cầu lifecycle mới ngoài Cancel bị từ chối hoặc gộp idempotently.
- Trạng thái shared server và trạng thái khóa UI phải nhất quán trên mọi tab AI Chat.

**Case 7: Target cuối cùng bị bỏ chọn khi server đang chạy**

- Invalidate session đang binding vào target bị bỏ chọn.
- Không tự động dừng server; user phải nhấn Stop.
- Nút Start chỉ được enable trở lại sau khi có ít nhất một target hợp lệ.

**Case 8: Rendezvous ID bị trùng trên Central Relay**

- Tạo rendezvous ID mới và đăng ký lại trong cùng server run.
- Không gửi username/password cho Relay trong bất kỳ lần đăng ký nào.

**Case 9: Internet P2P không thiết lập được**

- Trả `p2p_unavailable`, đóng peer connection và không tạo remote session.
- Không fallback qua Central Relay, TURN hoặc LAN mode.

**Case 10: Signaling bị mất sau khi P2P active**

- Session P2P hiện tại tiếp tục nếu DataChannel vẫn hoạt động.
- Server không nhận Internet client mới cho tới khi agent đăng ký signaling lại.

**Case 11: Password Internet không hợp lệ**

- Auto_MU trả lỗi chung trên DataChannel và đóng peer connection.
- Không tiết lộ target hoặc permission trước khi xác thực thành công.

### 3.3. Xử lý lỗi

| Lỗi                           | Xử lý                                                         |
|-------------------------------|---------------------------------------------------------------|
| Token/handshake không hợp lệ  | Từ chối kết nối, không tiết lộ thông tin target               |
| Target không tồn tại          | Không tạo session active, trả `target_unavailable`            |
| Permission bị thiếu           | Từ chối event và ghi audit event                              |
| Tool timeout                  | Cancel hoặc đánh dấu timeout, trả lỗi có mã                   |
| Server stop                   | Đóng toàn bộ session, worker và queue                         |
| Start khi chưa có target      | Không chạy operation; giữ `stopped` và disable Start          |
| Start/Stop bị hủy             | Quay về stable state trước operation và unlock AI Chat        |
| Start/Stop thất bại           | Chuyển `error`, hiển thị lỗi và unlock AI Chat                |
| Identity thay đổi             | Thu hồi quyền mutate và ngắt target binding                   |
| Relay unavailable             | Báo Internet remote unavailable; local feature vẫn hoạt động  |
| Rendezvous conflict           | Tạo rendezvous ID mới và đăng ký lại                          |
| WebRTC timeout/ICE failed     | Trả `p2p_unavailable`, cleanup và không fallback              |
| P2P password sai              | Từ chối trực tiếp, đóng peer connection                       |

## 4. PHÁC THẢO UI

**Khung tóm tắt dùng chung ở trên cùng AI Chat workspace:**

Chỉ có một khung Remote Server. Khung nằm bên ngoài và phía trên toàn bộ dãy tab cùng mọi thành phần bên trong các tab AI Chat; không lặp lại khung trong từng tab.

```text
┌──────────────────────────────────────────┐
│ Remote Server                            │
├──────────────────────────────────────────┤
│ Status: Running                          │
│ Connected devices: 2                     │
│ - Device A                               │
│ - Device B                               │
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
│ Endpoint: http://127.0.0.1:8765          │
│ Signaling: Online                        │
│ Internet transport: WebRTC P2P-only      │
│ Rendezvous ID: [Show QR]                 │
│ Username: 1234  Password: 5678           │
│ Sessions: 2                              │
│                                          │
│ Active sessions                          │
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

- Mỗi lần server start tạo username 4 chữ số và password 4 chữ số.
- Mỗi lần server start tạo thêm một rendezvous ID ngẫu nhiên ít nhất 128 bit.
- Rendezvous ID được đăng ký với Central Relay khi Internet remote bật; username/password không được gửi ra Relay.
- Rendezvous ID chỉ dùng để tìm agent connection, không thay thế credentials hoặc permission.
- Credentials hiển thị trong dialog `Remote Server Status` khi server `running` và không ghi vào log.
- Credentials mất hiệu lực khi server stop.
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
- [ ] Khung tóm tắt dùng chung có trạng thái, danh sách thiết bị, nút mở `Remote Server Status` và nút Start/Stop thể hiện stable state hiện tại.
- [ ] Dialog `Remote Server Status` hiển thị endpoint, username/password, session và action Start/Stop phù hợp.
- [ ] `starting` hoặc `stopping` khóa toàn bộ UI của tất cả AI Chat; chỉ dialog lifecycle và Cancel hoạt động.
- [ ] Cancel Start trả về `stopped`; Cancel Stop trả về `running`.
- [ ] Hoàn tất, lỗi hoặc cancel lifecycle operation luôn unlock AI Chat.
- [ ] Không có hai lifecycle operation chạy đồng thời.
- [ ] Auto_MU tự tạo rendezvous ID và username/password; Central Relay chỉ nhận rendezvous ID.
- [ ] Rendezvous ID có ít nhất 128 bit entropy và không cấp quyền remote.
- [ ] Một outbound signaling connection hỗ trợ nhiều client WebRTC session.
- [ ] SDP offer/answer và ICE candidate được trao đổi qua đúng signaling session.
- [ ] Password Internet được Auto_MU xác thực trực tiếp trên DataChannel mã hóa.
- [ ] Chat, frame, game state và remote command đi trực tiếp qua WebRTC P2P.
- [ ] ICE/DataChannel thất bại trả `p2p_unavailable` và không fallback.
- [ ] Signaling disconnect không chủ động đóng P2P session đang active.
