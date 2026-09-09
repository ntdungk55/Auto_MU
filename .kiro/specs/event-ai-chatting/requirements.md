# Event AI Chatting - Requirements

## 1. SPEC (Đặc tả)

**Vấn đề:**

Tab Gemini Chat sẽ cần một controller chuyên trách để theo dõi state của process/window game đã chọn,
phát event cho UI khi có rule phát hiện phù hợp, và tách hoàn toàn luồng này khỏi các feature hiện có.
Hiện chưa có `EventDetector` thực thi, chưa có rule emit event và chưa có UI tích hợp.

**Mục tiêu:**

- Tạo feature độc lập trong `samples/ai_game_controller/` theo kiến trúc của sample.
- Hoàn thiện `AIProcessController` để tab Gemini Chat có thể chọn target, Start, Stop và đăng ký nhận `GameEvent` ở giai đoạn tích hợp sau.
- Cung cấp `ScenarioManager` để tạo, sửa, xóa và lấy scenario được lưu bền vững theo từng target.
- Xây dựng luồng `GameStateReader → GameStateStore → EventDetector → event listener`.
- Chỉ chuẩn bị đường phát event; `EventDetector` chưa tự tạo hoặc emit bất kỳ event nào.

**Ngoài phạm vi:**

- Không tạo UI riêng.
- Không sửa `src/ui/gemini_chat_widget.py` hoặc bất kỳ feature hiện có nào.
- Không gọi AI, Prompt Builder, MCP server hoặc điều khiển game.
- Không định nghĩa rule, cooldown hoặc semantic cho event.
- Không viết unit test hoặc integration test theo yêu cầu hiện tại.

**Input/Output:**

| Loại             | Mô tả                                                                 | Ví dụ                                                   |
|------------------|------------------------------------------------------------------------|----------------------------------------------------------|
| Input            | Target process/window do caller chọn                                   | `target_id="mu-window-123"`, `hwnd=123456`             |
| Input            | Lệnh tạo, sửa, xóa hoặc chọn scenario của caller                      | Scenario theo dõi cho `target_id="mu-window-123"`       |
| Input            | `GameState` từ `GameStateReader`                                      | Snapshot OCR của target tại một thời điểm                |
| Input            | Event listener do Gemini Chat đăng ký                                 | Hàm nhận một `GameEvent`                                 |
| Output           | State mới nhất của từng target trong `GameStateStore`                 | `GameState(target_id="mu-window-123", ...)`            |
| Output           | Lời gọi event listener khi detector có event trong tương lai          | `listener(game_event)`                                   |
| Output hiện tại  | Không có `GameEvent` nào được phát vì chưa có rule emit               | Danh sách event rỗng                                     |

**Parameters (Tham số):**

| Tham số              | Kiểu                 | Mô tả                                                             | Giá trị mặc định         |
|-----------------------|----------------------|--------------------------------------------------------------------|--------------------------|
| `target_id`           | `str`                | Định danh ổn định của process/window được theo dõi                | Bắt buộc khi Start       |
| `hwnd`                | `int`                | Window handle của target                                           | Bắt buộc khi đọc state   |
| `scenario`            | `Scenario`           | Scenario do `ScenarioManager` tạo/chọn; chưa được gửi cho AI      | Không có                 |
| `scenario_repository` | `ScenarioRepository` | Nơi lưu/đọc JSON scenario theo từng target                         | Bắt buộc khi CRUD        |
| `event_listener`      | callback             | Hàm được gọi khi controller nhận `GameEvent`                      | Không có                 |
| `ocr_interval_ms`     | `int`                | Chu kỳ đọc state; lấy từ `config/app_settings.json`               | `500`                    |
| `event_detector`      | `EventDetector`      | Điểm mở rộng chuyển state sang event; chưa có rule                | Không emit event         |

**Persistence:**

- `ScenarioRepository` phải lưu scenario vào JSON trong thư mục dữ liệu runtime, không dùng `config/sample_scenario.json` làm file runtime.
- Scenario được nhóm theo `target_id` và vẫn tồn tại sau khi ứng dụng tắt/mở lại.
- Target đang chạy, event listener và state store chỉ tồn tại trong memory của `AIProcessController`.
- Khi Stop, worker dừng; state runtime có thể được giải phóng. Không ghi state hoặc event ra log/JSONL ở feature này.

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

```text
┌───────────────────────────────┐
│ Gemini Chat (tích hợp sau này) │
│ - chọn target                  │
│ - quản lý scenario             │
│ - gọi Start / Stop             │
│ - đăng ký event listener       │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│      AIProcessController       │
│   quản lý lifecycle runtime    │
└───────────────┬───────────────┘
                │
                ├───────────────► ScenarioManager ───► ScenarioRepository (JSON)
                ▼
┌───────────────────────────────┐
│        GameStateReader        │
│ capture + OCR qua adapter     │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│        GameStateStore         │
│ state mới nhất theo target    │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│         EventDetector         │
│ chưa có rule → không emit     │
└───────────────┬───────────────┘
                ▼
┌───────────────────────────────┐
│        event listener          │
│ Gemini Chat dùng ở phase sau   │
└───────────────────────────────┘
```

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: Quản lý scenario**

- Input: Lệnh create, update, delete, list hoặc select scenario; `target_id` tương ứng.
- Process: `ScenarioManager` validate dữ liệu, gọi `ScenarioRepository` để lưu/đọc JSON và trả scenario đã chọn.
- Output: Scenario bền vững theo target, sẵn sàng cho lần Start tiếp theo.

**Bước 2: Cấu hình runtime**

- Input: `target_id`, `hwnd`, `Scenario` đã chọn và event listener từ caller.
- Process: `AIProcessController` validate target, giữ runtime context trong memory và lưu listener.
- Output: Controller sẵn sàng để Start, nhưng chưa đọc game state.

**Bước 3: Khởi động đọc state**

- Input: Runtime context và `ocr_interval_ms`.
- Process: `AIProcessController` khởi động worker của `GameStateReader`; worker chỉ đọc state và không chạm UI.
- Output: Các `GameState` chuẩn hóa của target được đưa vào pipeline.

**Bước 4: Lưu state mới nhất**

- Input: `GameState` mới.
- Process: Lấy state trước đó của cùng `target_id`, sau đó cập nhật `GameStateStore` theo cách thread-safe.
- Output: Có previous state và current state sẵn sàng cho detector.

**Bước 5: Phát hiện event**

- Input: Previous state và current state.
- Process: Gọi `EventDetector.detect(...)`. Ở feature này detector không có rule nên luôn trả về danh sách rỗng.
- Output: Không có `GameEvent` nào được phát.

**Bước 6: Chuyển event cho caller trong tương lai**

- Input: Mỗi `GameEvent` được detector trả về ở phase tương lai.
- Process: Controller gọi event listener đã đăng ký. Nếu caller là Qt UI, caller phải chuyển event bằng Qt signal với `QueuedConnection` trước khi cập nhật widget.
- Output: Gemini Chat có điểm tích hợp rõ ràng, nhưng feature này chưa tự cập nhật UI.

**Bước 7: Dừng runtime**

- Input: Lệnh Stop từ caller.
- Process: Yêu cầu worker dừng, không nhận state mới và hủy runtime context theo lifecycle.
- Output: Không còn state đọc mới hoặc callback event sau khi worker đã dừng hoàn toàn.

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Start khi chưa chọn target**

- Xử lý: Không khởi động worker và trả về trạng thái lỗi rõ ràng cho caller.

**Case 2: Target/window không còn tồn tại khi đang chạy**

- Xử lý: Reader báo lỗi đọc state; controller dừng hoặc chuyển sang trạng thái không chạy, không tạo event giả.

**Case 3: Start lặp lại trong khi runtime đang chạy**

- Xử lý: Không tạo worker thứ hai; trả về trạng thái đang chạy cho caller.

**Case 4: Stop lặp lại hoặc Stop trước Start**

- Xử lý: Idempotent; không lỗi và không để lại worker chạy nền.

**Case 5: Event listener chưa được đăng ký**

- Xử lý: Controller vẫn duy trì pipeline state; khi future detector có event thì event được bỏ qua an toàn, không làm dừng worker.

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: Không đọc được window hoặc OCR thất bại**

- Nguyên nhân: Window handle không hợp lệ, game đã đóng hoặc adapter OCR gặp lỗi.
- Xử lý: Không ghi `GameState` không hợp lệ, không gọi detector với state lỗi và trả lỗi có ngữ cảnh cho caller.

**Lỗi 2: Event listener phát sinh exception**

- Nguyên nhân: Code tích hợp Gemini Chat xử lý event lỗi.
- Xử lý: Cô lập exception tại điểm callback để worker không dừng; báo lỗi cho caller/log runtime khi logging được bổ sung ở phase sau.

**Lỗi 3: Worker không dừng trong khoảng thời gian chờ hợp lý**

- Nguyên nhân: Reader hoặc OCR adapter đang bị block.
- Xử lý: Controller đánh dấu trạng thái dừng không hoàn tất và không tạo worker mới cho đến khi runtime cũ được giải phóng.

---

## 4. PHÁC THẢO UI

Không có UI trong feature này. Gemini Chat là caller ở phase tích hợp sau và nằm ngoài phạm vi của requirements hiện tại.

---

## 5. TIÊU CHÍ HOÀN THÀNH

- Feature nằm hoàn toàn trong `samples/ai_game_controller/` và có thể được khởi tạo độc lập.
- Caller có thể cấu hình target, scenario, Start, Stop và event listener qua controller API.
- State mới nhất được giữ riêng cho từng target theo cách thread-safe.
- `EventDetector` được gọi với previous/current state nhưng không emit event khi chưa có rule.
- Không có thay đổi tới UI hiện có, Gemini API, MCP hoặc feature hiện tại.
- Không có automated test được thêm ở feature này theo yêu cầu đã chốt.

---

## 6. TASK VÀ CÁC BƯỚC THỰC THI

Các task dưới đây là thứ tự triển khai của feature. `Process selector` trong tài liệu này là API/service
chọn process/window cho controller, không phải dropdown hoặc bất kỳ UI nào.

### Task 1: Hoàn thiện AIProcessController và runtime context

**Yêu cầu:**

`AIProcessController` phải nhận target, scenario đã chọn, event listener và các lệnh lifecycle từ nơi tích hợp sau này.

**Mô tả chi tiết:**

Hoàn thiện class `AIProcessController` trong `samples/ai_game_controller/`. Class này là controller của
feature, được Gemini Chat gọi ở phase tích hợp sau; UI không được gọi trực tiếp reader, store hoặc detector.

**Các bước sẽ làm:**

1. Đổi `ProcessController` thành `AIProcessController` để phản ánh rõ nhiệm vụ AI game process.
2. Xác định API cho cấu hình target, scenario đã chọn, event listener, Start và Stop.
3. Tạo runtime context chỉ chứa dữ liệu in-memory của một lần chạy.
4. Ràng buộc controller chỉ tạo một runtime worker đang hoạt động tại một thời điểm.
5. Trả trạng thái/lỗi có ngữ cảnh cho caller thay vì để exception làm dừng luồng gọi.

**Hoàn thành khi:**

Caller có thể khởi tạo controller và gọi các API lifecycle mà không phải biết chi tiết nội bộ của pipeline.

### Task 2: Tạo process/window selector không có UI

**Yêu cầu:**

Caller phải có cách lấy danh sách process/window game hợp lệ và chọn một target trước khi Start.

**Mô tả chi tiết:**

Tạo model target tối thiểu gồm `target_id`, `hwnd`, tên process và tiêu đề window. Tạo adapter/service
để liệt kê window hợp lệ trên Windows; controller chỉ nhận một target đã được chọn, không render dropdown.

**Các bước sẽ làm:**

1. Xác định tiêu chí một game window hợp lệ: có `hwnd`, còn tồn tại và có client area có thể capture.
2. Tạo model target và API liệt kê target cho caller.
3. Tạo API chọn target theo `target_id` hoặc `hwnd`.
4. Validate lại window được chọn ngay trước Start để tránh dùng handle đã hết hạn.

**Hoàn thành khi:**

Gemini Chat có thể tự dựng dropdown ở phase sau từ danh sách target và truyền target đã chọn vào controller.

### Task 3: Hoàn thiện GameStateReader qua adapter OCR

**Yêu cầu:**

Khi controller chạy, reader phải đọc snapshot chuẩn hóa của target đã chọn theo chu kỳ cấu hình.

**Mô tả chi tiết:**

`GameStateReader` chỉ chịu trách nhiệm capture client area, chuẩn hóa ảnh về 800×600, gọi OCR adapter và
đóng gói kết quả thành `GameState`. Reader không được chứa event rule, callback UI hoặc logic AI.

**Các bước sẽ làm:**

1. Định nghĩa input/output giữa capture adapter, OCR adapter và `GameStateReader`.
2. Capture client area của `hwnd` đã được controller validate.
3. Chuẩn hóa snapshot về kích thước 800×600 trước OCR.
4. Chuyển kết quả OCR thành `main_info` của `GameState` cùng `target_id`, `hwnd` và `captured_at`.
5. Báo lỗi đọc/capture/OCR cho controller; không trả `GameState` thiếu dữ liệu.
6. Chạy reader nền theo `ocr_interval_ms`; reader không gọi code UI.

**Hoàn thành khi:**

Mỗi chu kỳ hợp lệ tạo được một `GameState` bất biến cho đúng target; lỗi đọc không làm worker bị crash.

### Task 4: Hoàn thiện GameStateStore thread-safe

**Yêu cầu:**

Pipeline phải lấy được state trước đó và state mới nhất riêng cho từng target.

**Mô tả chi tiết:**

`GameStateStore` là nơi duy nhất giữ snapshot runtime. Store không suy luận event và không ghi dữ liệu xuống file.

**Các bước sẽ làm:**

1. Lấy state hiện tại của `target_id` trước khi ghi state mới.
2. Ghi `GameState` mới bằng khóa đồng bộ có phạm vi tối thiểu.
3. Cung cấp snapshot đọc ổn định cho controller/detector.
4. Xóa hoặc giải phóng state runtime theo lifecycle Stop; không persist state.

**Hoàn thành khi:**

Controller luôn truyền đúng cặp previous/current state của cùng target cho `EventDetector`.

### Task 5: Hoàn thiện EventDetector dưới dạng extension point rỗng

**Yêu cầu:**

Mỗi state mới phải đi qua `EventDetector`, nhưng feature này không được định nghĩa hoặc emit event.

**Mô tả chi tiết:**

`EventDetector.detect(previous_state, current_state)` là contract sẵn sàng cho phase sau. Nó nhận state,
giữ API ổn định và trả về danh sách `GameEvent` rỗng cho đến khi bạn cung cấp rule emit cụ thể.

**Các bước sẽ làm:**

1. Hoàn thiện signature, type hints và docstring của `EventDetector`.
2. Validate hai state thuộc cùng target trước khi xử lý.
3. Trả về danh sách rỗng khi chưa có rule.
4. Không thêm heuristic, cooldown, so sánh OCR hoặc event type mặc định.

**Hoàn thành khi:**

Luồng gọi detector đã tồn tại và không phát `GameEvent` nào ngoài ý muốn.

### Task 6: Tạo ScenarioManager và ScenarioRepository có persistence

**Yêu cầu:**

Caller phải tạo, sửa, xóa, liệt kê và chọn scenario; dữ liệu phải còn lại sau khi ứng dụng khởi động lại.

**Mô tả chi tiết:**

`ScenarioManager` chứa rule CRUD và validation. `ScenarioRepository` chỉ chịu trách nhiệm lưu/đọc JSON;
scenario được tách theo `target_id` và không dùng file mẫu trong `config/` làm dữ liệu runtime.

**Các bước sẽ làm:**

1. Xác định JSON schema có `schemaVersion`, `scenario_id`, `target_id`, instruction và các trường scenario hiện có.
2. Tạo API create, update, delete, get và list trong `ScenarioManager`.
3. Validate `target_id`, `scenario_id` và dữ liệu bắt buộc trước khi ghi.
4. Lưu JSON vào thư mục dữ liệu runtime bằng thao tác ghi an toàn.
5. Đọc lại JSON khi khởi tạo repository và trả scenario theo `target_id`.
6. Không để thay đổi scenario đang lưu tự động thay đổi runtime đang chạy; lần Start tiếp theo dùng scenario đã lưu mới nhất.

**Hoàn thành khi:**

Scenario CRUD hoạt động qua code API, dữ liệu còn lại sau khi khởi động lại và target chỉ nhìn thấy scenario của chính nó.

### Task 7: Nối ScenarioEngine và event listener boundary

**Yêu cầu:**

Controller phải có điểm chuyển tiếp rõ ràng để gửi event cho Gemini Chat sau này, nhưng không gọi Gemini Chat
hoặc bất kỳ QWidget nào trong feature này.

**Mô tả chi tiết:**

`ScenarioEngine` nhận event từ detector và chuyển cho listener đã đăng ký thông qua controller. AI execution,
Prompt Builder, MCP và verification đều không được gọi.

**Các bước sẽ làm:**

1. Nối output `GameEvent` của detector với `ScenarioEngine`.
2. Đăng ký, thay thế và hủy đăng ký event listener theo lifecycle controller.
3. Cô lập lỗi từ listener để worker đọc state tiếp tục chạy.
4. Ghi rõ contract: caller Qt phải emit signal với `QueuedConnection` trước khi cập nhật chat box.
5. Giữ hành vi hiện tại là không callback vì detector trả danh sách rỗng.

**Hoàn thành khi:**

Không có dependency từ feature sang Gemini Chat; future UI chỉ cần đăng ký listener để nhận event.

### Task 8: Hoàn thiện Start, Stop và shutdown an toàn

**Yêu cầu:**

Runtime phải dừng sạch, không tạo worker trùng và không callback event sau khi Stop hoàn tất.

**Mô tả chi tiết:**

`AIProcessController` sở hữu worker lifecycle. Đây là lớp duy nhất được phép Start/Stop reader và phối hợp
với store/detector/engine.

**Các bước sẽ làm:**

1. Validate target và các dependency trước Start.
2. Chặn Start lặp lại khi runtime đang chạy.
3. Khởi động worker đọc state với cancellation signal rõ ràng.
4. Dừng worker, chờ worker kết thúc và giải phóng runtime context khi Stop.
5. Làm Stop idempotent và không tạo callback sau khi runtime đã dừng.
6. Trả trạng thái lỗi nếu worker không thể dừng an toàn.

**Hoàn thành khi:**

Caller có thể gọi Start/Stop nhiều lần an toàn và chỉ có tối đa một worker hoạt động.

### Task 9: Compose feature độc lập và ghi rõ điểm tích hợp tương lai

**Yêu cầu:**

Feature phải chạy/khởi tạo độc lập trong sample và không sửa code hiện tại của ứng dụng chính.

**Mô tả chi tiết:**

`AIGameControllerApp` compose các dependency của sample. Gemini Chat không được import ở phase này; tài liệu
public API sẽ chỉ rõ cách tab đó sẽ gọi controller sau khi phase tích hợp được duyệt.

**Các bước sẽ làm:**

1. Khởi tạo reader, store, detector, scenario manager, scenario repository, scenario engine và AI process controller trong composition root của sample.
2. Giữ mọi import và thay đổi trong `samples/ai_game_controller/`.
3. Không thêm widget, tab, dropdown hoặc Qt signal trong feature này.
4. Ghi nhận API caller cần dùng ở phase Gemini Chat: list target, select target, set scenario, register listener,
   Start và Stop.

**Hoàn thành khi:**

Feature có thể được import/khởi tạo độc lập và không tạo thay đổi hành vi cho ứng dụng hiện tại.

### Task 10: Hạng mục được hoãn rõ ràng

**Yêu cầu:**

Không tự mở rộng phạm vi ngoài yêu cầu đã chốt.

**Các hạng mục hoãn:**

1. Viết rule emit event và các `event_type` cụ thể.
2. Hiển thị Event Bot hoặc bất kỳ UI nào trong Gemini Chat.
3. Prompt Builder, AI agent, MCP call, execution policy và xác minh state sau hành động.
4. Lưu target, state hoặc event xuống file/settings ngoài persistence dành riêng cho scenario.
5. Unit test, integration test và manual test plan theo yêu cầu hiện tại.

**Hoàn thành khi:**

Implementation dừng đúng ở controller/event boundary và không có hành vi ngoài phạm vi.
