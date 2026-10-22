# Event Registration and Location Observer - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**
Ứng dụng cần cho phép người dùng đăng ký nhiều event theo trạng thái map và tọa độ trong game. Mỗi event có prompt riêng để gửi cho AI khi điều kiện xảy ra, nhưng việc cấu hình hiện chưa có danh sách quản lý tập trung và chưa có observer theo dõi vị trí.

**Mục tiêu:**
Tạo cửa sổ quản lý event riêng, cho phép tạo, sửa, bật/tắt, xóa và lưu persistence các event đăng ký. Triển khai observer đầu tiên là `Location Observer`, theo dõi map và vùng tọa độ từ MCP game-state tool, phát event khi điều kiện vị trí thỏa mãn, sau đó gửi prompt trực tiếp cho AI hoặc đưa vào hàng đợi tin nhắn chờ nếu AI chưa thể xử lý ngay.

**Input/Output:**

| Loại   | Mô tả                                                                 | Ví dụ                                      |
|--------|-----------------------------------------------------------------------|--------------------------------------------|
| Input  | Event name                                                           | `Farm map 1`                                |
| Input  | Prompt                                                               | `Hãy kiểm tra trạng thái nhân vật`          |
| Input  | Enabled state                                                        | `true`                                      |
| Input  | Observer type                                                        | `Location Observer`                         |
| Input  | Map, tọa độ và vùng offset                                           | Map `Dungeon`, x `100-120`, y `50-70`       |
| Input  | Trigger mode                                                         | `Đi từ nguồn tới đích`                      |
| Input  | State game hiện tại theo chu kỳ cập nhật                              | `{map, x, y}`                               |
| Output | Event được phát khi điều kiện thỏa mãn                                | Event `Farm map 1`                          |
| Output | Prompt được gửi cho AI hoặc thêm vào waiting-message queue            | `Hãy kiểm tra trạng thái nhân vật`          |
| Output | Danh sách event được lưu và khôi phục sau khi mở lại ứng dụng         | Danh sách event đã đăng ký                  |

**Parameters (Tham số):**

| Tham số          | Kiểu           | Mô tả                                                        | Giá trị mặc định |
|------------------|----------------|--------------------------------------------------------------|------------------|
| `name`           | string         | Tên event, tạo/sửa trong event dialog                         | Bắt buộc         |
| `prompt`         | string         | Nội dung gửi cho AI, sửa trực tiếp được trong list view       | Bắt buộc         |
| `enabled`        | boolean        | Cho phép hoặc tạm dừng observer của event                     | `true`           |
| `observer_type`  | enum           | Loại observer                                                  | `location`       |
| `trigger_mode`   | enum           | `enter`, `exit`, hoặc `source_to_destination`                  | Bắt buộc         |
| `map`            | string/ID      | Map cần khớp                                                   | Bắt buộc         |
| `use_coordinates`| boolean        | Có kiểm tra vùng tọa độ hay chỉ kiểm tra map                   | `false`          |
| `min_x`          | integer        | Biên trái vùng tọa độ                                          | Bắt buộc nếu bật |
| `max_x`          | integer        | Biên phải vùng tọa độ                                          | Bắt buộc nếu bật |
| `min_y`          | integer        | Biên trên vùng tọa độ                                          | Bắt buộc nếu bật |
| `max_y`          | integer        | Biên dưới vùng tọa độ                                          | Bắt buộc nếu bật |
| `source`         | location       | Vị trí nguồn cho trigger `source_to_destination`               | Bắt buộc         |
| `destination`    | location       | Vị trí đích cho trigger `enter`, `exit`, hoặc source-to-dest   | Bắt buộc         |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌──────────────────────────────┐
│ Game state được cập nhật      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Lấy map và tọa độ qua MCP      │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Event đang enabled?            │
└──────────┬───────────┬───────┘
           │YES        │NO
           ▼           └──────────────► Bỏ qua event
┌──────────────────────────────┐
│ Kiểm tra map và tọa độ         │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Trigger condition thỏa mãn?    │
└──────────┬───────────┬───────┘
           │YES        │NO
           ▼           └──────────────► Chờ chu kỳ kế tiếp
┌──────────────────────────────┐
│ Phát event một lần theo        │
│ transition/state machine       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ AI sẵn sàng xử lý prompt?      │
└──────────┬───────────┬───────┘
           │YES        │NO
           ▼           ▼
┌────────────────┐  ┌────────────────────┐
│ Gửi prompt cho │  │ Thêm prompt vào    │
│ AI             │  │ waiting-message    │
└────────────────┘  │ queue              │
                    └────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Quản lý danh sách event

**Bước 1: Mở cửa sổ quản lý**
- Input: Người dùng nhấn button danh sách event, đặt bên trái bubble tự động.
- Process: Mở một cửa sổ quản lý event riêng.
- Output: Hiển thị danh sách event đã lưu.

Button danh sách event hoạt động độc lập với chế độ tự động; event observer không phụ thuộc việc bubble tự động đang bật hay tắt.

**Bước 2: Hiển thị list view**
- Input: Danh sách event persistence.
- Process: Hiển thị tối thiểu các cột `Enabled`, `Name`, `Prompt`, `Observer type` và thông tin trigger.
- Output: Người dùng có thể chọn, sửa và quản lý event.

**Bước 3: Sửa prompt trực tiếp**
- Input: Người dùng chỉnh ô prompt trong list view.
- Process: Cho phép sửa trực tiếp; lưu khi người dùng nhấn Enter hoặc rời khỏi ô nhập.
- Output: Prompt mới được cập nhật vào event và persistence.

**Bước 4: Tạo hoặc sửa event**
- Input: Button tạo event hoặc double-click một event.
- Process: Mở event dialog ở chế độ tạo hoặc chỉnh sửa.
- Output: Event hợp lệ được thêm mới hoặc cập nhật vào danh sách.

**Bước 5: Bật/tắt event**
- Input: Người dùng click control `Enabled`.
- Process: Cập nhật trạng thái enable/disable ngay trên event.
- Output: Event disabled không được observer xử lý.

**Bước 6: Xóa event**
- Input: Người dùng chọn event và nhấn button xóa.
- Process: Hiện hộp thoại xác nhận; chỉ xóa sau khi người dùng xác nhận.
- Output: Event bị xóa khỏi danh sách và persistence.

Nếu event đã phát prompt vào waiting-message queue trước khi bị xóa, message đã phát vẫn tiếp tục được xử lý.

### 3.2. Cấu hình Location Observer

**Bước 1: Chọn observer tab**
- Input: Event dialog.
- Process: Hiển thị các observer theo tab; phiên bản đầu có tab `Location Observer`.
- Output: Form cấu hình location observer.

**Bước 2: Cấu hình vị trí**
- Input: Map và tọa độ nhập thủ công.
- Process: Cho phép cấu hình map; source và destination có checkbox điều kiện tọa độ riêng; khi bật thì nhập `min_x`, `max_x`, `min_y`, `max_y` tương ứng cho từng vùng.
- Output: Một location condition gồm map và tùy chọn vùng tọa độ.

**Bước 3: Chọn trigger mode**
- Input: Dropdown trigger mode.
- Process:
  - `Đi vào`: chỉ cần destination.
  - `Đi ra`: chỉ cần destination.
  - `Đi từ nguồn tới đích`: cần source và destination.
- Output: Cấu hình trigger hợp lệ theo loại đã chọn.

**Bước 4: Lưu cấu hình**
- Input: Event name, prompt và observer settings.
- Process: Validate dữ liệu rồi lưu event vào persistence.
- Output: Event xuất hiện trong list view và sẵn sàng observe nếu enabled.

### 3.3. Location Observer runtime

**Bước 1: Đọc game state**
- Input: Chu kỳ cập nhật state game.
- Process: Gọi MCP tool hiện có để lấy map và tọa độ hiện tại.
- Output: Current location state.

**Bước 2: Kiểm tra event enabled**
- Input: Event configuration.
- Process: Bỏ qua event disabled.
- Output: Chỉ event enabled được xử lý.

Event observer không phụ thuộc chế độ `Tự động`, nhưng không được chạy khi game window đang được focus.

**Bước 3: Kiểm tra điều kiện vị trí**
- Input: Current location và location condition.
- Process: Map phải khớp. Nếu `use_coordinates=true`, tọa độ phải thỏa `min_x <= x <= max_x` và `min_y <= y <= max_y`.
- Output: Trạng thái đang ở trong hoặc ngoài vùng.

Nếu game window đang được focus, observer bỏ qua chu kỳ hiện tại và không thay đổi state transition. Nếu MCP tạm thời không trả được state, observer giữ state trước đó và thử lại ở chu kỳ sau.

**Bước 4: Xử lý trigger `Đi vào`**
- Input: Trạng thái destination ở chu kỳ hiện tại và chu kỳ trước.
- Process: Phát event đúng một lần khi chuyển từ ngoài destination sang trong destination.
- Output: Event fired.

**Bước 5: Xử lý trigger `Đi ra`**
- Input: Trạng thái destination ở chu kỳ hiện tại và chu kỳ trước.
- Process: Phát event đúng một lần khi chuyển từ trong destination sang ngoài destination.
- Output: Event fired.

**Bước 6: Xử lý trigger `Đi từ nguồn tới đích`**
- Input: Current location và state theo các chu kỳ trước.
- Process:
  - Chỉ bắt đầu observe khi state hiện tại nằm trong source.
  - Ghi nhận source đã đạt.
  - Sau đó chờ một chu kỳ tiếp theo hoặc các chu kỳ sau đạt destination.
  - Nếu current state không còn nằm trong source trước khi tới destination thì không phát event và trở về trạng thái chờ source.
  - Nếu map thay đổi khỏi map đang theo dõi thì reset ngay về trạng thái chờ source.
  - Khi đạt destination sau source, phát event một lần và reset về trạng thái chờ source.
- Output: Event fired khi đúng thứ tự source rồi destination.

### 3.4. Gửi prompt và waiting-message queue

**Bước 1: Nhận event fired**
- Input: Event name và prompt.
- Process: Chuyển prompt sang cơ chế gửi tin nhắn AI hiện có.
- Output: Prompt được gửi ngay hoặc được xếp hàng.

**Bước 2: AI chưa sẵn sàng**
- Input: AI đang xử lý prompt khác, không nhận được prompt, hoặc chưa thể xử lý tại thời điểm event phát.
- Process: Nếu prompt của cùng event chưa tồn tại trong queue, thêm prompt vào waiting-message queue theo thứ tự FIFO; nếu đã có prompt đang chờ thì không thêm bản trùng. Giữ event name cùng prompt để truy vết.
- Output: Tin nhắn chờ được xử lý khi AI sẵn sàng.

**Bước 3: AI sẵn sàng**
- Input: Waiting-message queue không rỗng và AI có thể nhận message.
- Process: Lấy message đầu hàng đợi và gửi cho AI.
- Output: Message được xử lý, sau đó tiếp tục message kế tiếp.

Khi prompt được sửa trực tiếp trong list view, hệ thống tự lưu và hiển thị thông báo lưu thành công hoặc lỗi lưu.

### 3.5. Persistence

- Lưu toàn bộ event configuration, bao gồm name, prompt, enabled state, observer type, trigger mode, map, coordinate toggle, source và destination.
- Khi mở lại ứng dụng, khôi phục chính xác danh sách và trạng thái enabled/disabled.
- Khi sửa prompt trực tiếp, tạo/sửa event hoặc xóa event, persistence phải được cập nhật.
- Xóa event phải xóa cấu hình event khỏi persistence, không chỉ xóa trên UI.

### 3.6. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Event name trùng**
- Xử lý: Không cho lưu; hiển thị lỗi yêu cầu tên duy nhất.

**Case 2: Prompt rỗng**
- Xử lý: Không cho lưu hoặc commit thay đổi prompt; hiển thị lỗi validation.

**Case 3: Tọa độ không hợp lệ**
- Xử lý: Không cho lưu nếu `min_x > max_x` hoặc `min_y > max_y`.

**Case 4: Trigger `Đi vào` hoặc `Đi ra` thiếu destination**
- Xử lý: Không cho lưu.

**Case 5: Trigger `Đi từ nguồn tới đích` thiếu source hoặc destination**
- Xử lý: Không cho lưu.

**Case 6: Tắt điều kiện tọa độ**
- Xử lý: Ẩn hoặc disable các field tọa độ; chỉ kiểm tra map.

**Case 7: Không có game state**
- Xử lý: Không phát event; ghi log lỗi hoặc warning; tiếp tục thử ở chu kỳ sau.

**Case 8: MCP trả về state thiếu map hoặc tọa độ cần thiết**
- Xử lý: Không coi là match; không làm thay đổi state machine source/destination.

**Case 9: Event disabled trong khi đang theo dõi source-to-destination**
- Xử lý: Dừng xử lý event và reset state machine về chờ source khi event được bật lại.

**Case 10: AI chưa thể xử lý prompt**
- Xử lý: Không mất prompt; đưa prompt vào waiting-message queue theo FIFO.

**Case 11: Prompt của cùng event đã tồn tại trong queue**
- Xử lý: Không thêm prompt trùng; giữ message đang chờ hiện tại.

**Case 12: Game window đang được focus**
- Xử lý: Không chạy observer và không thay đổi state machine trong chu kỳ đó.

**Case 13: MCP tạm thời không trả được state**
- Xử lý: Giữ state trước đó và thử lại ở chu kỳ kế tiếp.

**Case 14: Đổi map trong source-to-destination**
- Xử lý: Reset state machine về chờ source.

**Case 15: Sửa prompt trực tiếp**
- Xử lý: Tự động lưu persistence và hiển thị thông báo thành công hoặc lỗi.

**Case 11: Đóng cửa sổ quản lý khi còn thay đổi prompt chưa lưu**
- Xử lý: Hỏi người dùng lưu hoặc hủy thay đổi.

### 3.7. Xử lý lỗi (Error Handling)

**Lỗi 1: MCP game-state tool thất bại**
- Nguyên nhân: Tool lỗi, game window không tồn tại hoặc mất kết nối.
- Xử lý: Ghi log, không phát event giả, tiếp tục retry ở chu kỳ kế tiếp.

**Lỗi 2: Persistence không đọc được**
- Nguyên nhân: JSON hỏng hoặc schema không hợp lệ.
- Xử lý: Báo lỗi rõ ràng; không ghi đè dữ liệu cũ nếu chưa được người dùng xác nhận.

**Lỗi 3: Persistence không ghi được**
- Nguyên nhân: Không có quyền ghi hoặc lỗi file system.
- Xử lý: Báo lỗi; giữ thay đổi trong UI chưa coi là đã lưu thành công.

**Lỗi 4: AI/message channel không nhận prompt**
- Nguyên nhân: AI đang bận hoặc channel tạm thời không sẵn sàng.
- Xử lý: Đưa prompt vào waiting-message queue và xử lý lại khi channel sẵn sàng.

---

## 4. PHÁC THẢO UI

### 4.1. Main window

```text
...  [Danh sách event]  [Bubble tự động]  ...
```

### 4.2. Event Management Window

```text
┌────────────────────────────────────────────────────────────────────┐
│ Danh sách đăng ký event                                      [X]    │
├────────────────────────────────────────────────────────────────────┤
│ [Tạo thêm event]  [Xóa event]                                      │
├──────┬──────────────────┬─────────────────────────┬───────────────┤
│Enable│ Tên event        │ Prompt                  │ Observer      │
├──────┼──────────────────┼─────────────────────────┼───────────────┤
│  ☑   │ Farm map 1       │ [Prompt có thể sửa]     │ Location      │
│  ☐   │ Check boss       │ [Prompt có thể sửa]     │ Location      │
└──────┴──────────────────┴─────────────────────────┴───────────────┘
Double-click một dòng: mở Event Dialog để sửa
```

## 6. FINAL DECISIONS

- Maps use a static in-code catalog with `{id, name}` items. The UI shows `name`; persistence stores both `id` and `name`.
- Custom maps are not allowed. Map matching is case-insensitive.
- Event observers run independently of the automatic mode.
- The first valid state after app startup, game startup, or game restart is baseline only and never fires an event.
- Missing required MCP state does not match. A temporary MCP failure preserves the previous state and retries on the next cycle.
- While the game is focused, transitions are still evaluated, but fired events are ignored completely: no AI send and no queue insertion.
- Prompt duplicates are checked by `event_id`; a prompt currently being processed also counts as a duplicate.
- Enabling an event while already inside its destination does not fire immediately; the current state becomes baseline.
- Re-enabling or editing an observer resets its state machine.
- A map change away from the configured map resets source-to-destination tracking.
- Deleting one event at a time requires confirmation, stops observing immediately, and removes runtime state. Already queued prompts continue processing.
- The event list columns are `Enabled`, `Name`, `Prompt`, `Observer`, and `Status`.
- Runtime status is session-only and is shown in the list, including `Waiting for initial state`, `Waiting source`, `Source matched`, `Destination matched`, `Ignored: game focused`, and `Disabled`.
- Direct prompt edits are persisted and show a success or failure message.

## 7. REQUIREMENT ERRATA (AUTHORITATIVE)

The following decisions supersede any earlier wording in this document:

- Game focus does not stop observation. The observer continues evaluating and updating transition state, but a trigger detected while the game is focused is discarded completely: it is not sent to AI and is not added to the waiting queue.
- A prompt is duplicate when the same `event_id` is already being processed by AI or is present in the shared waiting queue. Prompt text is not used for duplicate detection.
- The map selector uses only the static in-code catalog of `{id, name}` entries. Custom map input is not supported. Matching is case-insensitive.
- The event list must include the `Status` column. Runtime status is session-only and is not persisted.
- The first valid state after app startup, game startup, or game restart is baseline only and must not trigger an event.
- Enabling an event while already inside its destination uses the current state as baseline and must not trigger immediately.
- Enabling an event again or editing its observer configuration resets its runtime state.
- Deleting an event stops observation immediately and removes its runtime state. Already queued prompts remain in the shared queue and continue processing.
- The old question list in Section 5 is resolved by the decisions above; it is not an open-requirements list.

### 4.3. Event Dialog

```text
┌──────────────────────────────────────────────┐
│ Thêm/Sửa event                          [X]  │
├──────────────────────────────────────────────┤
│ Tên event: [                              ]  │
│ Prompt:    [                              ]  │
│ Enabled:   [☑]                              │
├──────────────────────────────────────────────┤
│ Observer tabs: [Location Observer]           │
├──────────────────────────────────────────────┤
│ Trigger: [Đi vào ▼]                          │
│ Destination map: [                         ] │
│ ☐ Thêm điều kiện tọa độ                      │
│ min_x [   ] max_x [   ]                      │
│ min_y [   ] max_y [   ]                      │
│                                              │
│                         [Hủy] [Lưu]          │
└──────────────────────────────────────────────┘
```

Khi chọn `Đi từ nguồn tới đích`, dialog hiển thị thêm nhóm cấu hình source với các field tương tự destination.

---

## 5. CÂU HỎI CẦN LÀM RÕ

Các điểm đã chốt:
- Dùng chung cơ chế gửi AI và waiting-message queue hiện tại.
- Nhiều event phát cùng chu kỳ xử lý theo thứ tự event trong danh sách.
- Event enabled bắt đầu observe ngay khi ứng dụng khởi động.
- Event observer độc lập với chế độ `Tự động`.
- Không chạy observer khi game window đang được focus.
- Prompt trùng của cùng event không được thêm lần nữa khi đã tồn tại trong queue.
- Source và destination có checkbox điều kiện tọa độ riêng.
- Đổi map khỏi map đang theo dõi reset state machine source-to-destination.
- MCP lỗi giữ state trước đó.
- Prompt đã vào queue vẫn được xử lý sau khi event bị xóa.
- Sửa prompt trực tiếp phải có thông báo lưu thành công hoặc lỗi.
