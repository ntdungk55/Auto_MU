# Central Relay Business Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Auto_MU được cài trên nhiều máy và các máy thường nằm sau router, NAT hoặc mạng di động. Remote client không thể
tự biết máy nào đang online, không biết địa chỉ mạng của máy cần kết nối và không có kênh chung để trao đổi thông
tin thiết lập kết nối WebRTC.

**Mục tiêu:**

- Cung cấp một Central Relay công khai để Auto_MU Server và remote client tìm thấy nhau.
- Lưu ánh xạ tạm thời giữa `username` và Auto_MU Server đang online.
- Ghép client có đúng `username` với đúng server tương ứng.
- Chuyển tiếp thông tin signaling cần thiết để hai thiết bị tự thiết lập WebRTC P2P.
- Không nhận, lưu hoặc kiểm tra password của Remote Server.
- Không chuyển tiếp chat, frame, game state, tool call hoặc remote command sau handshake.
- Không cung cấp TURN hoặc data relay fallback khi kết nối P2P thất bại.

**Phạm vi:**

- Một Central Relay phục vụ nhiều bản cài Auto_MU đồng thời.
- Mỗi lần Remote Server chạy, Auto_MU Server tự tạo username 9 chữ số và password 6 chữ số.
- Username là định danh duy nhất trong online registry, dùng để Relay tìm đúng server; username không phải bí mật.
- Password chỉ hiển thị cho Windows user và chỉ được kiểm tra trực tiếp giữa server với client sau khi WebRTC
  DataChannel mã hóa đã mở.
- Username không tự cấp quyền điều khiển server.
- Client không được xem danh sách server online; client phải có username do Windows user chia sẻ.
- Mỗi Auto_MU Server chỉ phục vụ một client tại một thời điểm; khi server đang bận, client khác bị từ chối ngay
  và không được xếp hàng chờ.
- Relay chỉ hoạt động như online registry và signaling coordinator.
- Kết nối dữ liệu là P2P-only; thất bại P2P kết thúc lần kết nối đó.

**Vai trò nghiệp vụ:**

| Vai trò            | Trách nhiệm                                                                         |
|--------------------|-------------------------------------------------------------------------------------|
| Windows user       | Bật/tắt server, chia sẻ credentials và quản lý session/permission                   |
| Auto_MU Server     | Tạo credentials, đăng ký username, thiết lập P2P và tự xác thực password            |
| Remote client      | Nhập credentials, yêu cầu ghép server, thiết lập P2P và gửi password trực tiếp      |
| Central Relay      | Quản lý server online, tìm theo username và chuyển signaling WebRTC                 |

**Input/Output:**

"technical" là `.kiro/specs/central-relay/technical-requirements.md`.

| Loại   | Tác nhân                | Nội dung nghiệp vụ                                          | Chi tiết kỹ thuật                                   |
|--------|-------------------------|-------------------------------------------------------------|-----------------------------------------------------|
| Input  | Auto_MU Server          | Báo "tôi online" kèm username và thông tin lần chạy        | `server_register` (technical §4.1)                  |
| Input  | Auto_MU Server          | Báo định kỳ "tôi vẫn còn online"                            | Agent heartbeat (technical §8)                      |
| Input  | Auto_MU Server          | Ngắt kết nối khi Windows user dừng server hoặc mất mạng     | Agent disconnect (technical §3.2, §8)               |
| Input  | Auto_MU Server          | Đồng ý thiết lập kết nối với client                          | `connection_accept` (technical §4.3)                |
| Input  | Auto_MU Server          | Từ chối client trước khi thiết lập kết nối                   | `connection_reject` (technical §4.3)                |
| Input  | Auto_MU Server          | Từ chối client vì đang bận với client khác                   | `connection_reject` + `reason: busy` (technical §4.3) |
| Input  | Auto_MU Server          | Gửi thông tin thiết lập kết nối cho client                   | `webrtc_offer/answer`, `ice_*` (technical §4.3)     |
| Input  | Auto_MU Server          | Báo kết nối trực tiếp thành công                             | `p2p_connected` (technical §4.3)                    |
| Input  | Auto_MU Server          | Báo kết nối trực tiếp thất bại                               | `p2p_failed` (technical §4.3)                       |
| Input  | Remote client           | Yêu cầu kết nối tới máy có username X kèm nhận diện thiết bị | `connection_request`, `client_instance_id` (technical §4.2) |
| Input  | Remote client           | Gửi thông tin thiết lập kết nối cho server                   | `webrtc_offer/answer`, `ice_*` (technical §4.3)     |
| Input  | Remote client           | Báo kết nối trực tiếp thành công                             | `p2p_connected` (technical §4.3)                    |
| Input  | Remote client           | Báo kết nối trực tiếp thất bại                               | `p2p_failed` (technical §4.3)                       |
| Input  | Remote client           | Hủy yêu cầu hoặc ngắt kết nối với Relay                       | `signaling_close` (technical §4.3)                  |
| Output | Auto_MU Server          | Xác nhận đã online                                          | `server_registered` (technical §4.1)                |
| Output | Auto_MU Server          | Từ chối online vì username đang được máy khác dùng          | `username_conflict` (technical §10)                 |
| Output | Auto_MU Server          | Từ chối online vì máy không hợp lệ                          | `invalid_agent` (technical §10)                     |
| Output | Auto_MU Server          | Từ chối đăng ký vì vượt 5 lần/phút                            | `rate_limited` (technical §10)                      |
| Output | Auto_MU Server          | Thông báo có client muốn kết nối kèm nhận diện thiết bị     | `incoming_connection` (technical §4.2–4.3)          |
| Output | Auto_MU Server          | Chuyển thông tin thiết lập kết nối từ client                | Forward `webrtc_*`, `ice_*` (technical §5)          |
| Output | Auto_MU Server          | Thông báo client đã hủy hoặc ngắt kết nối                   | `signaling_close` (technical §4.3)                  |
| Output | Auto_MU Server          | Thông báo hết thời gian thiết lập kết nối                   | `signaling_timeout` (technical §10)                 |
| Output | Remote client           | Không tìm thấy máy (lỗi chung, không tiết lộ máy từng tồn tại) | `server_unavailable` (technical §4.2, §10)          |
| Output | Remote client           | Máy từ chối kết nối                                         | `signaling_rejected` (technical §10)                |
| Output | Remote client           | Máy đang bận với thiết bị khác                               | `server_busy` (technical §10)                       |
| Output | Remote client           | Chuyển thông tin thiết lập kết nối từ server                | Forward `webrtc_*`, `ice_*` (technical §5)          |
| Output | Remote client           | Máy đã offline trong lúc thiết lập kết nối                  | `server_unavailable` + `signaling_close` (technical §4.3, §10) |
| Output | Remote client           | Hết thời gian thiết lập kết nối                             | `signaling_timeout` (technical §10)                 |
| Output | Remote client           | Từ chối vì gửi quá nhiều yêu cầu                            | `rate_limited` (technical §10)                      |
| Output | Auto_MU Server, client  | Báo phía còn lại không kết nối trực tiếp được                | Forward `p2p_failed` (technical §4.3)               |
| Output | Auto_MU Server, client  | Từ chối thông tin thiết lập không hợp lệ                     | `invalid_signaling` (technical §10)                 |

**Tham số nghiệp vụ:**

| Tham số                        | Kiểu | Ý nghĩa                                                        | Giá trị mặc định |
|---------------------------------|------|----------------------------------------------------------------|------------------|
| `max_clients_per_server`        | int  | Số client được thiết lập hoặc giữ kết nối với một server     | `1`              |
| `signaling_session_timeout`     | int  | Thời gian tối đa để hai phía hoàn tất thiết lập P2P            | `30` giây        |
| `agent_heartbeat_interval`      | int  | Chu kỳ server báo vẫn còn online                              | `15` giây        |
| `agent_offline_timeout`         | int  | Thời gian không nhận heartbeat trước khi coi server offline   | `45` giây        |
| `connection_request_rate_limit` | int  | Số yêu cầu tìm server tối đa cho mỗi IP trong một phút        | `10`             |
| `agent_register_rate_limit`     | int  | Số lần đăng ký online tối đa cho mỗi bản cài trong một phút  | `5`              |

### 1.1. Quy tắc nghiệp vụ của Central Relay

1. Auto_MU Server phải tạo username 9 chữ số và password 6 chữ số mới cho mỗi lần Remote Server chạy.
2. Username phải được tạo ngẫu nhiên và không được suy ra từ IP hoặc thông tin máy.
3. Server chỉ gửi username và metadata tối thiểu cần thiết cho Relay; không gửi password.
4. Relay chỉ chấp nhận một server online cho mỗi username tại một thời điểm.
5. Nếu username đang được server online khác sử dụng, Relay từ chối registration để Auto_MU tạo username khác.
6. Relay phải lưu ánh xạ `username → agent connection` trong thời gian server online.
7. Client chỉ được yêu cầu ghép nối khi có username; Relay không cung cấp API liệt kê server công khai.
8. Username chỉ dùng để tìm server; Auto_MU vẫn phải xác thực password trước khi tạo remote session.
9. Mỗi yêu cầu hợp lệ tạo một signaling session riêng giữa một client và đúng một server.
10. Relay chỉ chuyển offer, answer, ICE candidate và trạng thái thiết lập kết nối.
11. Relay không được nhận hoặc chuyển password trong signaling message.
12. Relay không được chuyển dữ liệu ứng dụng sau khi P2P được thiết lập.
13. Khi server disconnect, Relay phải xóa username mapping và đóng signaling session chưa hoàn tất.
14. P2P session đã thiết lập có thể tiếp tục khi Relay mất kết nối vì dữ liệu không đi qua Relay.
15. Khi P2P thất bại, Relay chuyển thông báo thất bại cho phía còn lại và đóng signaling session; không fallback qua
    Relay hoặc TURN.
16. Relay phải rate-limit yêu cầu tìm server tối đa 10 lần/phút cho mỗi IP để hạn chế spam và dò username.
17. Khi Auto_MU Server từ chối vì đang bận, Relay trả `server_busy` cho client và đóng signaling session ngay;
    Relay không xếp hàng client chờ.
18. Relay phải rate-limit đăng ký online tối đa 5 lần/phút cho mỗi bản cài Auto_MU.
19. Auto_MU Server phải reserve một client slot bằng thao tác atomic trước khi gửi `connection_accept`; Relay không
    tự quyết định slot và chỉ chuyển kết quả accept/reject.
20. Relay chỉ coi signaling hoàn tất khi cả server và client cùng báo `control` DataChannel đã mở.
21. Nếu một peer báo P2P thất bại, Relay thông báo cho peer còn kết nối và cleanup session; cleanup phải idempotent
    khi peer còn lại đã disconnect.

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌────────────────────────────┐
│ Windows user bật           │
│ Remote Server              │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Auto_MU tự tạo username    │
│ và password                │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Server đăng ký username    │
│ với Central Relay          │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Client gửi username        │
│ tới Central Relay          │
└──────────────┬─────────────┘
               ▼
       ┌───────┴────────┐
       │ Username       │
       │ đang online?   │
       └───────┬────────┘
          No   │   Yes
        ┌──────┘   └────────────┐
        ▼                       ▼
┌───────────────┐      ┌────────────────────┐
│ Báo server    │      │ Tạo signaling      │
│ unavailable   │      │ session tạm thời   │
└───────────────┘      └─────────┬──────────┘
                                 ▼
                       ┌────────────────────┐
                       │ Server đang bận?   │
                       │ Yes → `server_busy`│
                       └─────────┬──────────┘
                                 ▼ No
                       ┌────────────────────┐
                       │ Chuyển offer,      │
                       │ answer, candidate  │
                       └─────────┬──────────┘
                                 ▼
                         ┌───────┴───────┐
                         │ P2P thành công│
                         └───────┬───────┘
                            No   │   Yes
                     ┌───────────┘   └──────────────┐
                     ▼                              ▼
             ┌────────────────┐          ┌────────────────────┐
             │ Báo thất bại  │          │ Server/client tự   │
             │ cho cả hai phía│          │ handshake password │
             └────────────────┘          └─────────┬──────────┘
                                                  ▼
                                        ┌────────────────────┐
                                        │ Dữ liệu đi trực tiếp│
                                        │ không qua Relay     │
                                        └────────────────────┘
```

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Server đăng ký online**

- Input: Remote Server đã được Windows user bật, username và nhận diện của lần chạy.
- Process: Relay xác thực Auto_MU Agent, kiểm tra username chưa được sử dụng và lưu mapping online.
- Output: Server được đăng ký hoặc nhận yêu cầu tạo username khác.

**Bước 2: Client tìm server**

- Input: Username do Windows user chia sẻ.
- Process: Relay tra mapping online theo username mà không yêu cầu hoặc kiểm tra password.
- Output: Server unavailable, `server_busy` hoặc một signaling session tạm thời được tạo.

**Bước 3: Ghép đúng hai thiết bị**

- Input: Agent connection của server, connection của client và `client_instance_id` của bản cài client.
- Process: Relay gắn cả hai vào cùng signaling session, chuyển request cho Auto_MU reserve slot; session khác không
  được truy cập dữ liệu này.
- Output: Hai phía sẵn sàng trao đổi thông tin thiết lập WebRTC.

**Bước 4: Chuyển signaling**

- Input: Offer, answer và network candidate của server/client.
- Process: Relay chuyển nguyên vẹn thông tin tới đúng peer trong signaling session.
- Output: Hai thiết bị có đủ thông tin để WebRTC tự kiểm tra đường kết nối trực tiếp.

**Bước 5: Hoàn tất signaling**

- Input: Trạng thái DataChannel open từ từng peer hoặc P2P failed.
- Process: Relay chỉ đánh dấu thành công khi cả hai peer đã sẵn sàng; nếu fail/disconnect/timeout thì cleanup
  idempotently.
- Output: Hai phía chuyển sang P2P hoặc nhận lỗi `p2p_unavailable`.

**Bước 6: Giao tiếp trực tiếp**

- Input: WebRTC DataChannel đã mã hóa.
- Process: Client gửi password trực tiếp; Auto_MU Server xác thực và tạo remote session.
- Output: Chat, frame, game state và command đi trực tiếp giữa hai thiết bị, không qua Relay.

### 3.2. Các trường hợp ngoại lệ

**Case 1: Username bị trùng**

- Relay từ chối registration mới; Auto_MU tạo username mới, cập nhật UI và đăng ký lại.

**Case 2: Client dùng username không online**

- Relay trả một lỗi chung, không tiết lộ server từng tồn tại hay không.

**Case 3: Client thứ hai kết nối khi server đang bận**

- Auto_MU reserve slot atomically; khi server đang `reserved`, `authenticating` hoặc `active`, request khác bị từ chối.
- Relay trả `server_busy` và đóng signaling session của client bị từ chối.
- Client bị từ chối không được xếp hàng; kết nối của client hiện tại không bị ảnh hưởng.

**Case 4: Server offline trong lúc signaling**

- Relay đóng signaling session và báo server unavailable cho client.

**Case 5: Relay mất kết nối sau khi P2P active**

- P2P session hiện có tiếp tục; không thể tạo session mới cho tới khi signaling hoạt động lại.

**Case 6: ICE không tìm được đường trực tiếp**

- Kết nối thất bại với `p2p_unavailable`; Relay chuyển thông báo thất bại cho phía còn lại, không chuyển traffic qua
  Relay và không dùng TURN.

**Case 7: Client gửi password sai**

- Auto_MU Server tự từ chối trên DataChannel; Relay không nhận được password hoặc kết quả chi tiết.
- Sau 5 lần sai liên tiếp từ cùng `client_instance_id`, Auto_MU chỉ tạm khóa thiết bị đó; server và thiết bị khác
  không bị khóa theo.

### 3.3. Xử lý lỗi

| Lỗi                            | Hành vi nghiệp vụ                                                          |
|--------------------------------|----------------------------------------------------------------------------|
| Agent không hợp lệ             | Từ chối đăng ký username                                                   |
| Username conflict              | Yêu cầu server tạo username mới                                            |
| Server unavailable             | Không tạo signaling session                                                |
| Server bận                     | Trả `server_busy`, đóng signaling session, không xếp hàng                 |
| Vượt 10 yêu cầu/phút từ một IP | Trả `rate_limited`, không tra username                                     |
| Vượt 5 lần đăng ký/phút        | Trả `rate_limited` cho Auto_MU Server, không đăng ký username             |
| Signaling timeout              | Cleanup session và cho phép client thử lại                                 |
| Signaling peer disconnect      | Đóng signaling session còn lại                                             |
| P2P unavailable                | Báo phía còn lại, kết thúc kết nối, không fallback                          |
| Relay unavailable              | Không tạo kết nối mới; P2P session active không bị Relay chủ động đóng     |
| Signaling message không hợp lệ | Từ chối message mà không chuyển sang peer                                  |

## 4. PHÁC THẢO UI

**Auto_MU Server:**

```text
┌─────────────────────────────────────────────┐
│ Remote Server                              │
├─────────────────────────────────────────────┤
│ Signaling: Online                          │
│ Username: 123 456 789                      │
│ Password: 567890                           │
│ Connected client: Android-X                │
│                                             │
│ [Open Status]          [Stop Remote Server]│
└─────────────────────────────────────────────┘
```

**Remote client:**

```text
┌─────────────────────────────────────────────┐
│ Connect to Auto_MU                         │
├─────────────────────────────────────────────┤
│ Username: [                              ] │
│ Password: [                              ] │
│                                             │
│ Status: Finding server / Connecting P2P     │
│                         [Connect]           │
└─────────────────────────────────────────────┘
```

## 5. ACCEPTANCE CRITERIA

- [ ] Nhiều Auto_MU Server có thể đăng ký đồng thời với username khác nhau.
- [ ] Relay tìm đúng agent connection từ username và không cung cấp danh sách server công khai.
- [ ] Username không đủ để tạo remote session khi thiếu password đúng.
- [ ] Relay không nhận, lưu, log hoặc xác thực password.
- [ ] Mỗi client request tạo signaling session riêng với đúng server.
- [ ] Offer, answer và ICE candidate chỉ được chuyển giữa hai peer của cùng signaling session.
- [ ] Chat, frame, game state và remote command không đi qua Relay.
- [ ] Client và server tự xác thực password sau khi WebRTC DataChannel mã hóa mở.
- [ ] P2P thất bại trả `p2p_unavailable`, được thông báo cho cả hai phía và không dùng TURN/Relay fallback.
- [ ] Server đang thiết lập hoặc đã có client thì client mới nhận `server_busy` ngay, không bị xếp hàng.
- [ ] Server disconnect làm username biến mất khỏi online registry.
- [ ] Relay disconnect không chủ động đóng P2P connection đã thiết lập.
- [ ] Relay từ chối yêu cầu thứ 11 trong một phút từ cùng IP bằng `rate_limited` mà không cần biết password.
- [ ] Relay từ chối lần đăng ký thứ 6 trong một phút từ cùng bản cài bằng `rate_limited`.
- [ ] `client_instance_id` được chuyển tới đúng Auto_MU Server nhưng không được coi là credential.
- [ ] Chỉ request reserve slot thành công atomically mới nhận `connection_accept`.
- [ ] Signaling chỉ hoàn tất khi cả hai peer báo `control` DataChannel đã mở.

## 6. NGOÀI PHẠM VI BUSINESS REQUIREMENTS

- Chuyển tiếp dữ liệu ứng dụng hoặc lưu nội dung remote session.
- TURN server, media relay hoặc Central Relay data fallback.
- Kiểm tra password của Remote Server.
- Danh bạ công khai cho phép client duyệt mọi server online.
- Lựa chọn framework, database hoặc hosting topology của Relay.

