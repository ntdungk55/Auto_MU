# Central Relay Business Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Auto_MU được cài trên nhiều máy và các máy thường nằm sau router, NAT hoặc mạng di động. Remote client không thể
tự biết máy nào đang online, không biết địa chỉ mạng của máy cần kết nối và không có kênh chung để trao đổi thông
tin thiết lập kết nối WebRTC.

**Mục tiêu:**

- Cung cấp một Central Relay công khai để Auto_MU Server và remote client tìm thấy nhau.
- Lưu ánh xạ tạm thời giữa `rendezvous_id` và Auto_MU Server đang online.
- Ghép client có đúng `rendezvous_id` với đúng server tương ứng.
- Chuyển tiếp thông tin signaling cần thiết để hai thiết bị tự thiết lập WebRTC P2P.
- Không nhận, lưu hoặc kiểm tra password của Remote Server.
- Không chuyển tiếp chat, frame, game state, tool call hoặc remote command sau handshake.
- Không cung cấp TURN hoặc data relay fallback khi kết nối P2P thất bại.

**Phạm vi:**

- Một Central Relay phục vụ nhiều bản cài Auto_MU đồng thời.
- Mỗi lần Remote Server chạy có một `rendezvous_id` ngẫu nhiên, dùng riêng để phân biệt và tìm server.
- Username/password do Auto_MU Server tự tạo, chỉ hiển thị cho Windows user và chỉ được kiểm tra trực tiếp giữa
  server với client sau khi WebRTC DataChannel mã hóa đã mở.
- `rendezvous_id` không thay thế username/password và không tự cấp quyền điều khiển server.
- Client không được xem danh sách server online; client phải có `rendezvous_id` do Windows user chia sẻ.
- Relay chỉ hoạt động như online registry và signaling coordinator.
- Kết nối dữ liệu là P2P-only; thất bại P2P kết thúc lần kết nối đó.

**Vai trò nghiệp vụ:**

| Vai trò            | Trách nhiệm                                                                         |
|--------------------|-------------------------------------------------------------------------------------|
| Windows user       | Bật/tắt server, chia sẻ rendezvous ID/credentials và quản lý session/permission       |
| Auto_MU Server     | Tạo rendezvous ID/credentials, thiết lập P2P và tự xác thực username/password         |
| Remote client      | Nhập credentials, yêu cầu ghép server, thiết lập P2P và gửi password trực tiếp      |
| Central Relay      | Quản lý server online, tìm theo rendezvous ID và chuyển signaling WebRTC            |

**Input/Output:**

| Loại   | Mô tả                                                        | Ví dụ                                   |
|--------|--------------------------------------------------------------|-----------------------------------------|
| Input  | Server đăng ký hoặc hủy đăng ký trạng thái online            | `rendezvous_id`, online/offline         |
| Input  | Client yêu cầu tìm server theo rendezvous ID                 | `rendezvous_id=...`                     |
| Input  | Thông tin thiết lập WebRTC từ server hoặc client             | Offer, answer, network candidate        |
| Output | Kết quả tìm server                                            | Found, offline, unavailable            |
| Output | Một signaling session tạm thời giữa đúng server và client    | Ghép PC-A với Android-X                 |
| Output | Thông tin signaling được chuyển đến đúng phía                | Server offer đến đúng client            |

**Tham số nghiệp vụ:**

| Tham số                    | Ý nghĩa                                                        | Giá trị mặc định                  |
|----------------------------|----------------------------------------------------------------|-----------------------------------|
| Vòng đời rendezvous ID     | Thời gian rendezvous ID được Relay coi là online               | Trong một lần Remote Server chạy  |
| Số signaling session       | Số client có thể yêu cầu ghép với cùng server                  | Nhiều session độc lập             |
| Thời hạn signaling session | Thời gian tối đa để hai phía hoàn tất thiết lập P2P            | Có giới hạn                       |
| Data fallback              | Cách xử lý khi không tạo được kết nối trực tiếp                | Không có                          |
| Quyền xác thực password    | Thành phần được phép kiểm tra password                         | Auto_MU Server                    |

### 1.1. Quy tắc nghiệp vụ của Central Relay

1. Auto_MU Server phải tạo `rendezvous_id`, username và password mới cho mỗi lần Remote Server chạy.
2. `rendezvous_id` phải ngẫu nhiên ít nhất 128 bit và không được suy ra từ IP, username hoặc thông tin máy.
3. Server chỉ gửi `rendezvous_id` và metadata tối thiểu cần thiết cho Relay; không gửi username/password.
4. Relay chỉ chấp nhận một server online cho mỗi `rendezvous_id` tại một thời điểm.
5. Nếu xảy ra collision, Relay từ chối registration để Auto_MU tạo `rendezvous_id` khác.
6. Relay phải lưu ánh xạ `rendezvous_id → agent connection` trong thời gian server online.
7. Client chỉ được yêu cầu ghép nối khi có `rendezvous_id`; Relay không cung cấp API liệt kê server công khai.
8. `rendezvous_id` chỉ là locator; Auto_MU vẫn phải xác thực username/password trước khi tạo remote session.
9. Mỗi yêu cầu hợp lệ tạo một signaling session riêng giữa một client và đúng một server.
10. Relay chỉ chuyển offer, answer, ICE candidate và trạng thái thiết lập kết nối.
11. Relay không được nhận hoặc chuyển username/password trong signaling message.
12. Relay không được chuyển dữ liệu ứng dụng sau khi P2P được thiết lập.
13. Khi server disconnect, Relay phải xóa rendezvous mapping và đóng signaling session chưa hoàn tất.
14. P2P session đã thiết lập có thể tiếp tục khi Relay mất kết nối vì dữ liệu không đi qua Relay.
15. Khi P2P thất bại, Relay trả trạng thái thất bại; không fallback qua Relay hoặc TURN.
16. Relay phải rate-limit yêu cầu tìm server/signaling để hạn chế spam và enumeration.

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌────────────────────────────┐
│ Windows user bật           │
│ Remote Server              │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Auto_MU tự tạo rendezvous  │
│ ID và username/password    │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Server đăng ký rendezvous ID│
│ với Central Relay          │
└──────────────┬─────────────┘
               ▼
┌────────────────────────────┐
│ Client gửi rendezvous ID   │
│ tới Central Relay          │
└──────────────┬─────────────┘
               ▼
       ┌───────┴────────┐
       │ Rendezvous ID  │
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
             │ Báo P2P không  │          │ Server/client tự   │
             │ khả dụng       │          │ handshake password │
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

- Input: Remote Server đã được Windows user bật, `rendezvous_id` và nhận diện của lần chạy.
- Process: Relay xác thực Auto_MU Agent, kiểm tra rendezvous ID chưa được sử dụng và lưu mapping online.
- Output: Server được đăng ký hoặc nhận yêu cầu tạo rendezvous ID khác.

**Bước 2: Client tìm server**

- Input: Rendezvous ID do Windows user chia sẻ, thường qua QR/deep link.
- Process: Relay tra mapping online mà không yêu cầu hoặc kiểm tra username/password.
- Output: Server unavailable hoặc một signaling session tạm thời được tạo.

**Bước 3: Ghép đúng hai thiết bị**

- Input: Agent connection của server và connection của client.
- Process: Relay gắn cả hai vào cùng signaling session; session khác không được truy cập dữ liệu này.
- Output: Hai phía sẵn sàng trao đổi thông tin thiết lập WebRTC.

**Bước 4: Chuyển signaling**

- Input: Offer, answer và network candidate của server/client.
- Process: Relay chuyển nguyên vẹn thông tin tới đúng peer trong signaling session.
- Output: Hai thiết bị có đủ thông tin để WebRTC tự kiểm tra đường kết nối trực tiếp.

**Bước 5: Hoàn tất signaling**

- Input: Trạng thái WebRTC connected hoặc failed.
- Process: Relay đánh dấu kết quả và cleanup signaling session khi hết thời hạn.
- Output: Hai phía chuyển sang P2P hoặc nhận lỗi `p2p_unavailable`.

**Bước 6: Giao tiếp trực tiếp**

- Input: WebRTC DataChannel đã mã hóa.
- Process: Client gửi password trực tiếp; Auto_MU Server xác thực và tạo remote session.
- Output: Chat, frame, game state và command đi trực tiếp giữa hai thiết bị, không qua Relay.

### 3.2. Các trường hợp ngoại lệ

**Case 1: Rendezvous ID bị trùng**

- Relay từ chối registration mới; Auto_MU tạo rendezvous ID mới và đăng ký lại.

**Case 2: Client dùng rendezvous ID không online**

- Relay trả một lỗi chung, không tiết lộ server từng tồn tại hay không.

**Case 3: Nhiều client cùng kết nối một server**

- Mỗi client có signaling session và P2P connection riêng.

**Case 4: Server offline trong lúc signaling**

- Relay đóng signaling session và báo server unavailable cho client.

**Case 5: Relay mất kết nối sau khi P2P active**

- P2P session hiện có tiếp tục; không thể tạo session mới cho tới khi signaling hoạt động lại.

**Case 6: ICE không tìm được đường trực tiếp**

- Kết nối thất bại với `p2p_unavailable`; không chuyển traffic qua Relay và không dùng TURN.

**Case 7: Client gửi password sai**

- Auto_MU Server tự từ chối trên DataChannel; Relay không nhận được password hoặc kết quả chi tiết.

### 3.3. Xử lý lỗi

| Lỗi                            | Hành vi nghiệp vụ                                                          |
|--------------------------------|----------------------------------------------------------------------------|
| Agent không hợp lệ             | Từ chối đăng ký rendezvous ID                                              |
| Rendezvous conflict            | Yêu cầu server tạo rendezvous ID mới                                       |
| Server unavailable             | Không tạo signaling session                                                |
| Signaling timeout              | Cleanup session và cho phép client thử lại                                 |
| Signaling peer disconnect      | Đóng signaling session còn lại                                             |
| P2P unavailable                | Kết thúc kết nối, không fallback                                           |
| Relay unavailable              | Không tạo kết nối mới; P2P session active không bị Relay chủ động đóng     |
| Signaling message không hợp lệ | Từ chối message mà không chuyển sang peer                                  |

## 4. PHÁC THẢO UI

**Auto_MU Server:**

```text
┌─────────────────────────────────────────────┐
│ Remote Server                              │
├─────────────────────────────────────────────┤
│ Signaling: Online                          │
│ Rendezvous ID: [Show QR]                   │
│ Username: 1234                             │
│ Password: 5678                             │
│ P2P clients: 2                             │
│                                             │
│ [Open Status]          [Stop Remote Server]│
└─────────────────────────────────────────────┘
```

**Remote client:**

```text
┌─────────────────────────────────────────────┐
│ Connect to Auto_MU                         │
├─────────────────────────────────────────────┤
│ Rendezvous ID: [                         ] │
│ Username: [                              ] │
│ Password: [                              ] │
│                                             │
│ Status: Finding server / Connecting P2P     │
│                         [Connect]           │
└─────────────────────────────────────────────┘
```

## 5. ACCEPTANCE CRITERIA

- [ ] Nhiều Auto_MU Server có thể đăng ký đồng thời với rendezvous ID khác nhau.
- [ ] Relay tìm đúng agent connection từ rendezvous ID và không cung cấp danh sách server công khai.
- [ ] Rendezvous ID không được coi là credentials và không thay thế username/password.
- [ ] Relay không nhận, lưu, log hoặc xác thực password.
- [ ] Mỗi client request tạo signaling session riêng với đúng server.
- [ ] Offer, answer và ICE candidate chỉ được chuyển giữa hai peer của cùng signaling session.
- [ ] Chat, frame, game state và remote command không đi qua Relay.
- [ ] Client và server tự xác thực password sau khi WebRTC DataChannel mã hóa mở.
- [ ] P2P thất bại trả `p2p_unavailable` và không dùng TURN/Relay fallback.
- [ ] Server disconnect làm rendezvous ID biến mất khỏi online registry.
- [ ] Relay disconnect không chủ động đóng P2P connection đã thiết lập.
- [ ] Relay rate-limit request theo source và rendezvous ID mà không cần biết username/password.

## 6. NGOÀI PHẠM VI BUSINESS REQUIREMENTS

- Chuyển tiếp dữ liệu ứng dụng hoặc lưu nội dung remote session.
- TURN server, media relay hoặc Central Relay data fallback.
- Kiểm tra password của Remote Server.
- Danh bạ công khai cho phép client duyệt mọi server online.
- Lựa chọn framework, database hoặc hosting topology của Relay.

