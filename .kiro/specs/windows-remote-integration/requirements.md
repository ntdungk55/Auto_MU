# Windows Remote Integration Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Auto_MU hiện có AI Chat, process selection và các MCP server nhưng chưa có UI điều khiển thủ công một shared Remote Server. Cần cho phép Windows user quản lý lifecycle và remote session mà không phá vỡ automation, AI Chat hoặc MCP hiện có.

**Mục tiêu:**

- Thêm khung thông tin Remote Server trong mỗi AI Chat và đồng bộ trạng thái giữa các tab.
- Chỉ cho phép user start shared Remote Server khi có ít nhất một game window được chọn.
- Start/Stop hoàn toàn thủ công; chọn hoặc bỏ chọn window không tự động start/stop server.
- Hiển thị dialog có Cancel trong khi server đang khởi động hoặc dừng và khóa toàn bộ AI Chat.
- Gửi đúng thông tin process/window mà tab đang quản lý tới remote session.
- Windows user là admin; các remote permission mặc định được bật và có thể bị revoke.
- Message remote được đưa vào queue theo thứ tự event đến server.
- Bảo vệ target bằng `PID + HWND + creation_time`.

**Input/Output:**

| Loại   | Mô tả                                  | Ví dụ                                  |
|--------|----------------------------------------|----------------------------------------|
| Input  | Tab AI Chat chọn/bỏ chọn window        | `selected_window_hwnd=12345`           |
| Input  | Remote session và permission request   | `session_id`, `permission=send_chat`   |
| Output | Dialog lifecycle                       | `Stopped`, `Starting`, `Running`, `Stopping`, `Error` |
| Output | Permission/session status              | `Authenticated`, `Revoked`, `Closed`   |

**Parameters:**

| Tham số                 | Kiểu   | Mô tả                                  | Giá trị mặc định |
|------------------------|--------|----------------------------------------|------------------|
| `remote_server_host`   | string | Địa chỉ server                         | `127.0.0.1`      |
| `remote_server_port`   | int    | Cổng server                            | `8765`           |
| `startup_timeout`      | float  | Thời gian chờ server ready             | `10.0` giây      |
| `shutdown_timeout`     | float  | Thời gian cleanup                      | `8.0` giây       |
| `allow_remote_connect` | bool   | Cho phép remote handshake              | `true`           |

Username và password không persistence. Mỗi lần server start, server tạo mới hai chuỗi số 4 chữ số và hiển thị trong dialog `Remote Server Status` khi server chuyển sang `running`.

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌──────────────────────┐
│ AI Chat chọn window  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Enable nút Start     │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ User nhấn Start      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Starting dialog      │
│ Lock AI Chat/Cancel  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Server running       │
│ Hiển thị credentials│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Remote handshake      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Admin review session  │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Cấp quyền / xử lý FIFO│
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ Target invalid/close  │
│ revoke + cleanup      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ User Stop/Cancel      │
└──────────────────────┘
```

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Theo dõi target từ AI Chat**

- Input: Process/window selection của từng tab.
- Process: Đăng ký target identity vào shared remote lifecycle; không tạo server riêng theo tab và không tự start/stop server.
- Output: Nút Start được enable khi có ít nhất một target hợp lệ, ngược lại bị disable.

Khi không còn game window nào được chọn trong lúc server đang chạy, các session binding vào target không còn hợp lệ bị đóng nhưng server tiếp tục chạy cho tới khi user nhấn Stop.

**Bước 2: Khung Remote Server trong AI Chat**

- Input: Shared server state và session/device snapshot.
- Process: Mỗi AI Chat hiển thị trạng thái/lỗi, danh sách thiết bị đang kết nối, nút mở `Remote Server Status` và action button Start/Stop.
- Output: Mọi tab phản ánh cùng trạng thái và cùng danh sách thiết bị.

**Bước 3: Start/Stop thủ công**

- Input: User nhấn Start hoặc Stop.
- Process: Start chỉ hợp lệ khi có target; Stop chỉ hợp lệ khi server đang `running`; chỉ một lifecycle operation được chạy.
- Output: Server chuyển lần lượt qua `starting`/`stopping` tới stable state tương ứng.

**Bước 4: Lifecycle dialog và UI lock**

- Input: Trạng thái `starting` hoặc `stopping`.
- Process: Mở modal dialog, khóa toàn bộ UI của tất cả AI Chat và chỉ cho phép nút Cancel hoạt động.
- Output: Cancel Start trả về `stopped`; Cancel Stop trả về `running`; hoàn tất, lỗi hoặc cancel đều unlock AI Chat.

**Bước 5: Session admin**

- Input: Remote đăng nhập bằng username/password 4 chữ số trong dialog `Remote Server Status`.
- Process: Không có bước approve connection riêng. Settings global quyết định permissions áp dụng cho tất cả remote client đã đăng nhập.
- Output: Permission snapshot và session state.

**Bước 6: Target binding**

- Input: Remote chọn một window đã được tích trong bảng Settings.
- Process: Đối chiếu `window_title`, `process_name`, `pid`, `hwnd`, `tab_name`, PID và creation time; sau handshake chỉ gửi dữ liệu của một window duy nhất.
- Output: Session binding không được tự đổi target.

**Bước 7: Message/event processing**

- Input: Event từ Windows hoặc remote.
- Process: Server xử lý event nào đến trước trước; permission và control lease được kiểm tra trước khi chạy.
- Output: Event result hoặc denied/busy/timeout.

**Bước 8: Stop**

- Input: User nhấn Stop hoặc ứng dụng đang shutdown.
- Process: Revoke session, stop stream, cancel remote work và dừng server. App shutdown thực hiện forced cleanup; thao tác Stop từ UI có thể cancel.
- Output: Cleanup hoàn tất, không còn worker/socket sống.

### 3.2. Edge Cases

- Nhiều tab cùng chọn các window khác nhau: server vẫn dùng chung, mỗi session phải binding đúng target được cấp.
- Nhiều tab cùng chọn một window: không được tạo mutate song song.
- Tab đổi process: session cũ bị đánh dấu target stale; không tự chuyển remote sang process mới.
- Không có target: nút Start bị disable và server không nhận start operation.
- Target cuối cùng bị bỏ chọn khi đang chạy: invalidate session liên quan nhưng không tự stop server.
- Start bị cancel: cleanup phần đã khởi tạo, trở về `stopped` và unlock toàn bộ AI Chat.
- Stop bị cancel: trở về `running`, giữ credentials/session còn hiệu lực và unlock toàn bộ AI Chat.
- Một tab bắt đầu lifecycle operation: tất cả tab hiển thị cùng modal lock và cùng kết quả.
- Remote kết nối khi `allow_remote_connect=false`: handshake bị từ chối.
- Server startup thất bại: dialog hiển thị lỗi, AI Chat vẫn hoạt động bình thường.
- Server shutdown thất bại: chuyển `error`, hiển thị lỗi và unlock AI Chat.
- Remote chat đến trong lúc Windows đang xử lý event: giữ trong FIFO queue theo thứ tự server nhận.
- Tắt `view_stream`: dừng stream của tất cả remote ngay.
- Tắt `view_game_state`: dừng state của tất cả remote ngay.
- Tắt `send_chat`: xóa remote message đang chờ; không xóa message đã hiển thị và không hủy lượt AI remote đang chạy.
- Tắt `discover_tools`: xóa tool catalog remote.
- Tắt `call_readonly_tools`: từ chối hoặc hủy readonly request đang chờ.
- Tắt `call_mutating_tools`: thu hồi control lease và dừng mutate request.

### 3.3. Global Settings

- Settings chỉ có một bản cho toàn bộ Remote Server.
- Bảng window có checkbox; mặc định mọi window trong bảng được tích.
- Bảng cập nhật khi AI Chat chọn game window hoặc khi game window đóng thành công.
- Bỏ tích một window đang được remote sử dụng phải ngắt session đó ngay.
- Nhiều remote client có thể đăng nhập đồng thời bằng cùng credentials.

### 3.4. Persistence

- Endpoint, port, bind mode và allow remote connection phải có behavior lưu/load rõ trong design.
- Permission cấp cho session không được mặc định lưu lâu dài nếu chưa có quyết định về device identity.
- Không ghi token/secret vào log hoặc file không được bảo vệ.

### 3.5. Thread-safe UI

- Server/worker không được cập nhật trực tiếp QWidget.
- Khung tóm tắt, lifecycle dialog, session list, status, UI lock và permission UI phải nhận cập nhật qua Qt signals với `QueuedConnection`.
- UI lock là trạng thái dùng chung: trong `starting`/`stopping`, toàn bộ widget của tất cả AI Chat bị disable ngoại trừ lifecycle dialog và nút Cancel.

### 3.6. Xử lý lỗi

| Lỗi                         | Hành vi Windows                                      |
|----------------------------|------------------------------------------------------|
| Bind port thất bại         | Hiển thị lỗi, không làm đơ AI Chat                   |
| Server timeout             | Đóng dialog hoặc chuyển trạng thái error             |
| Start không có target      | Giữ `stopped`, disable Start và không tạo worker      |
| Cancel Start               | Cleanup phần đã tạo, về `stopped`, unlock AI Chat     |
| Cancel Stop                | Khôi phục `running`, giữ credentials/session hợp lệ   |
| Target stale               | Revoke quyền mutate và báo target unavailable        |
| Permission denied          | Ghi audit và trả lỗi cho remote                      |
| Remote disconnect          | Cleanup session, giữ server nếu còn target khác      |
| App shutdown               | Stop server, socket, worker và session theo thứ tự   |

## 4. PHÁC THẢO UI

**Khung tóm tắt trong AI Chat:**

```text
┌──────────────────────────────────────────┐
│ Remote Server                            │
├──────────────────────────────────────────┤
│ Status: Running                          │
│ Connected devices:                       │
│ - Device A                               │
│ - Device B                               │
│ [Open Remote Server Status]              │
│ [Running — Stop Server]                  │
└──────────────────────────────────────────┘
```

**Dialog `Remote Server Status`:**

```text
┌──────────────────────────────────────────┐
│ Remote Server Status                     │
├──────────────────────────────────────────┤
│ Status: Running                          │
│ Endpoint: http://127.0.0.1:8765          │
│ Username: 1234  Password: 5678           │
│                                          │
│ Active sessions                          │
│ Device A  Authenticated                  │
│ [Permissions] [Revoke]                   │
│                                          │
│ ☐ Cho phép remote kết nối                │
│ Window allowlist: [window checkbox table]│
│ [Running — Stop Server]          [Close] │
└──────────────────────────────────────────┘
```

**Lifecycle modal:**

```text
┌──────────────────────────────────────────┐
│ Starting/Stopping Remote Server...       │
├──────────────────────────────────────────┤
│ Toàn bộ AI Chat đang bị khóa.            │
│                                 [Cancel] │
└──────────────────────────────────────────┘
```

## 5. Acceptance Criteria

- [ ] Chọn/bỏ chọn target không tự động start/stop server.
- [ ] Start chỉ enable khi có ít nhất một target hợp lệ.
- [ ] Khung Remote Server xuất hiện trong mỗi AI Chat và đồng bộ shared state/device list.
- [ ] Khung có nút mở `Remote Server Status` và action button thể hiện `Running` hoặc `Stopped`.
- [ ] Start/Stop mở lifecycle dialog không block PyQt event loop.
- [ ] `starting`/`stopping` khóa toàn bộ UI của tất cả AI Chat ngoại trừ Cancel.
- [ ] Cancel Start trả về `stopped`; Cancel Stop trả về `running`.
- [ ] Server `running` hiển thị endpoint, username và password trong dialog `Remote Server Status`.
- [ ] Remote session mặc định có đầy đủ permission và Windows admin có thể revoke.
- [ ] Windows admin có thể bật/tắt global permission và revoke session.
- [ ] Sau handshake, session chỉ nhận dữ liệu của một window.
- [ ] Event được xử lý theo thứ tự đến server.
- [ ] Chỉ một session được mutate trên một target tại một thời điểm.
- [ ] Target identity đổi thì remote không được điều khiển target mới.
- [ ] Existing automation, AI Chat và MCP server vẫn hoạt động.

## 6. Ngoài phạm vi

- Không xây Android UI trong feature này.
- Không triển khai Cloudflare Tunnel, relay hoặc public endpoint.
- Không triển khai pairing/QR/device identity hoàn chỉnh.
- Không mô tả remote control UI; quyền được quản lý từ Windows admin.
