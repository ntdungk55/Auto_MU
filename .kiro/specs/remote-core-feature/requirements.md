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

| Loại   | Mô tả                                      | Ví dụ                                      |
|--------|--------------------------------------------|--------------------------------------------|
| Input  | Kết nối, handshake, yêu cầu quyền, event   | `connect`, `subscribe_stream`, `chat`      |
| Input  | Window identity do remote chọn lúc đầu     | `pid`, `hwnd`, `creation_time`             |
| Output | Trạng thái server/session                   | `stopped`, `starting`, `running`, `stopping`, `error` |
| Output | Frame, state, tool result hoặc message      | JSON metadata và binary JPEG frame         |

**Permissions mặc định:**

| Permission             | Mặc định | Ý nghĩa                                  |
|------------------------|----------|------------------------------------------|
| `connect`              | Bật      | Đăng nhập bằng username/password server cấp |
| `view_stream`          | Bật      | Cho phép nhận frame                      |
| `view_game_state`      | Bật      | Cho phép nhận Game State                 |
| `send_chat`            | Bật      | Cho phép gửi message mới vào AI Chat     |
| `discover_tools`       | Bật      | Cho phép xem danh sách MCP tools         |
| `call_readonly_tools`  | Bật      | Cho phép gọi tool chỉ đọc                |
| `call_mutating_tools`  | Bật      | Cho phép gọi tool thay đổi trạng thái    |

**Parameters:**

| Tham số                    | Kiểu   | Mô tả                                      | Mặc định                  |
|---------------------------|--------|--------------------------------------------|---------------------------|
| `host`                    | string | Địa chỉ bind của Remote Server             | `127.0.0.1`               |
| `port`                    | int    | Cổng HTTP/WebSocket                        | `8765`                    |
| `stream_fps`              | float  | Cadence stream tối đa                      | `2.0`                     |
| `max_frame_queue`         | int    | Số frame tối đa giữ cho một client         | `1`                       |
| `tool_timeout_seconds`    | float  | Timeout cho một tool call                 | `45.0`                    |
| `max_mutating_sessions`   | int    | Số session mutate đồng thời trên một target| `1`                       |

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
- Process: Xác thực, tạo `session_id`; nhiều thiết bị có thể đăng nhập đồng thời bằng cùng credentials; các permission dùng giá trị mặc định đã bật và vẫn có thể bị Windows admin revoke.
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
- Process: Thu hồi quyền, ngừng stream/tool mutate, đóng session và giải phóng worker.
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

### 3.3. Xử lý lỗi

| Lỗi                         | Xử lý                                                        |
|----------------------------|--------------------------------------------------------------|
| Token/handshake không hợp lệ | Từ chối kết nối, không tiết lộ thông tin target               |
| Target không tồn tại       | Không tạo session active, trả `target_unavailable`           |
| Permission bị thiếu        | Từ chối event và ghi audit event                             |
| Tool timeout               | Cancel hoặc đánh dấu timeout, trả lỗi có mã                  |
| Server stop                | Đóng toàn bộ session, worker và queue                        |
| Start khi chưa có target   | Không chạy operation; giữ `stopped` và disable Start         |
| Start/Stop bị hủy          | Quay về stable state trước operation và unlock AI Chat       |
| Start/Stop thất bại        | Chuyển `error`, hiển thị lỗi và unlock AI Chat               |
| Identity thay đổi          | Thu hồi quyền mutate và ngắt target binding                  |

## 4. PHÁC THẢO UI

**Khung tóm tắt trong mỗi AI Chat:**

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

- Không triển khai Cloudflare Tunnel, relay hoặc public hosting.
- Không triển khai Device ID/QR/pairing hoàn chỉnh.
- Không triển khai Codex CLI.
- Không mô tả Android remote control UI trong feature core.
- Không tạo server riêng cho từng remote client.

## 6. Credentials và window allowlist

- Mỗi lần server start tạo username 4 chữ số và password 4 chữ số.
- Credentials hiển thị trong dialog `Remote Server Status` khi server `running` và không ghi vào log.
- Credentials mất hiệu lực khi server stop.
- Settings là global cho shared server.
- Settings có bảng checkbox window; mặc định mọi window trong bảng được tích.
- Bảng cập nhật khi AI Chat chọn game window hoặc khi game window đóng thành công.
- Remote chỉ được chọn window đang được tích; bỏ tích window đang binding sẽ ngắt session đó ngay.

## 7. Acceptance Criteria

- [ ] Chọn window không tự động start server và bỏ chọn window cuối cùng không tự động stop server.
- [ ] Start bị disable khi chưa có game window được chọn.
- [ ] Start/Stop thủ công điều khiển duy nhất một shared server.
- [ ] Mọi AI Chat hiển thị cùng lifecycle state và danh sách thiết bị đang kết nối.
- [ ] Khung tóm tắt có trạng thái, danh sách thiết bị, nút mở `Remote Server Status` và nút Start/Stop thể hiện stable state hiện tại.
- [ ] Dialog `Remote Server Status` hiển thị endpoint, username/password, session và action Start/Stop phù hợp.
- [ ] `starting` hoặc `stopping` khóa toàn bộ UI của tất cả AI Chat; chỉ dialog lifecycle và Cancel hoạt động.
- [ ] Cancel Start trả về `stopped`; Cancel Stop trả về `running`.
- [ ] Hoàn tất, lỗi hoặc cancel lifecycle operation luôn unlock AI Chat.
- [ ] Không có hai lifecycle operation chạy đồng thời.
