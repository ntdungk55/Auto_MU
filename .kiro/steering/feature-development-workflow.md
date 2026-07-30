---
inclusion: auto
---

# QUY TRÌNH PHÁT TRIỂN FEATURE MỚI - BẮT BUỘC TUÂN THỦ

**QUAN TRỌNG:** LLM phải tuân thủ nghiêm ngặt quy trình 5 bước này khi phát triển feature mới. Không được bỏ qua bất kỳ bước nào. Chỉ được sang bước tiếp theo khi hỏi người dùng đồng ý với kết quả của từng bước.

---

## BƯỚC 1: PHÂN TÍCH YÊU CẦU (Requirement Analysis)

**Mục tiêu:** Làm rõ ý tưởng của user về mặt NGHIỆP VỤ, chưa quan tâm đến cách triển khai kỹ thuật.

**LLM phải làm:**
1. Đọc yêu cầu của user
2. Mô tả lại ý hiểu về yêu cầu bằng ngôn ngữ của mình:
   - Feature này làm gì?
   - Giải quyết vấn đề gì?
   - Input/Output mong đợi là gì?
3. Kiểm tra độ rõ ràng:
   - ✅ Đã rõ ràng: Kiểm tra tính khả thi, các vấn đề gặp phải, các bước làm cần để giải quyết. Đưa ra thêm các phần để cải tiến ý tưởng của người hỏi
   - ❌ Chưa rõ ràng: Hỏi các câu hỏi cụ thể
   - Sau khi người dùng đã thỏa mãn xuất ra bản nháp của step 1 dựa vào output format bên dưới rồi chờ xem người dùng đã thỏa mãn kết quả chưa.

**Nếu chưa rõ ràng, LLM hỏi:**
- Use cases chính là gì? Ví dụ cụ thể?
- Edge cases nào cần xử lý?
- Performance requirements? (tốc độ, memory)
- UI/UX mong đợi như thế nào?
- Có ràng buộc kỹ thuật nào không?

**Output Format:**

```markdown
## 1. SPEC (Đặc tả)

**Vấn đề:**
[Mô tả vấn đề cần giải quyết]

**Mục tiêu:**
[Mô tả mục tiêu của feature]

**Input/Output:**

| Loại | Mô tả | Ví dụ |
|------|-------|-------|
| Input | [Mô tả input] | [Ví dụ cụ thể] |
| Output | [Mô tả output] | [Ví dụ cụ thể] |

**Parameters (Tham số):**

| Tham số | Kiểu | Mô tả | Giá trị mặc định |
|---------|------|-------|------------------|
| [Tên param] | [Kiểu dữ liệu] | [Mô tả] | [Default] |

---

## 2. SƠ ĐỒ HOẠT ĐỘNG

[Flowchart dạng box và arrow - dễ trace cho người đọc]

Ví dụ:
┌─────────────────┐
│  Bắt đầu        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Bước 1: ...    │
└────────┬────────┘
         │
         ▼
    ┌────┴────┐
    │ Điều    │
    │ kiện?   │
    └─┬────┬──┘
      │    │
   YES│    │NO
      │    │
      ▼    ▼
   [...]  [...]

---

## 3. MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: [Tên bước trong flowchart]**
- Input: [Dữ liệu đầu vào]
- Process: [Xử lý gì]
- Output: [Kết quả]

**Bước 2: [Tên bước tiếp theo]**
- Input: [Dữ liệu đầu vào]
- Process: [Xử lý gì]
- Output: [Kết quả]

[Tiếp tục cho tất cả các bước trong flowchart...]

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: [Mô tả tình huống]**
- Xử lý: [Cách xử lý]

**Case 2: [Mô tả tình huống]**
- Xử lý: [Cách xử lý]

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: [Loại lỗi]**
- Nguyên nhân: [Tại sao xảy ra]
- Xử lý: [Cách xử lý]

**Lỗi 2: [Loại lỗi]**
- Nguyên nhân: [Tại sao xảy ra]
- Xử lý: [Cách xử lý]

---

## 4. PHÁC THẢO UI (nếu có)

[ASCII art UI mockup]

Ví dụ:
┌─────────────────────────────────────────┐
│  [Tiêu đề Dialog]                    [X]│
├─────────────────────────────────────────┤
│                                         │
│  Label 1: [Input field 1            ]  │
│                                         │
│  Label 2: [Input field 2            ]  │
│                                         │
│  ☐ Checkbox option                     │
│                                         │
│  [Button 1]  [Button 2]                │
│                                         │
└─────────────────────────────────────────┘

**Mô tả các thành phần:**
- Input field 1: [Mô tả chức năng]
- Input field 2: [Mô tả chức năng]
- Checkbox: [Mô tả chức năng]
- Button 1: [Mô tả chức năng]
- Button 2: [Mô tả chức năng]
```

**Output:** Mô tả yêu cầu đã được làm rõ theo format trên, chờ user xác nhận.

**Lưu vào:** `.kiro/specs/[feature-name]/requirements.md`

**Checklist kiểm tra format requirements.md:**
- [ ] File có đúng path `.kiro/specs/[feature-name]/requirements.md`?
- [ ] Có section "SPEC (Đặc tả)" với Vấn đề, Mục tiêu?
- [ ] Có bảng Input/Output với ví dụ cụ thể?
- [ ] Có bảng Parameters với kiểu dữ liệu và giá trị mặc định?
- [ ] Có sơ đồ hoạt động (flowchart)?
- [ ] Có mô tả hoạt động chi tiết cho từng bước?
- [ ] Có xử lý edge cases?
- [ ] Có xử lý lỗi (Error Handling)?
- [ ] Có phác thảo UI (nếu có)?
- [ ] Tất cả thông tin đã đầy đủ và rõ ràng?

**Checkpoint:** LLM hỏi user: "Requirements này có OK không? Nếu OK tôi sẽ chuyển sang Bước 2."

---

## BƯỚC 2: PHÂN TÍCH KỸ THUẬT & THIẾT KẾ (Technical Analysis & Design)

**Mục tiêu:** Phân tích cách triển khai kỹ thuật để đáp ứng yêu cầu từ Bước 1, bao gồm thư viện, mô hình, architecture.

**LLM phải làm:**

### 2.1. Phân tích tác động (Impact Analysis)
1. **Tác động đến code hiện tại:**
   - Files nào cần sửa?
   - Classes/methods nào bị ảnh hưởng?
   - Có breaking changes không?

2. **Dependencies:**
   - Cần thêm thư viện mới không?
   - Phụ thuộc vào modules nào?

3. **Khó khăn kỹ thuật:**
   - Vấn đề kỹ thuật nào có thể gặp?
   - Có conflict với logic hiện tại không?
   - Cần refactor code cũ không?

4. **Rủi ro:**
   - Có thể gây lỗi ở đâu?
   - Cần test kỹ phần nào?

### 2.2. Thiết kế kỹ thuật (Technical Design)
1. **Architecture:**
   - Cấu trúc code như thế nào?
   - Classes/modules nào được tạo/sửa?
   - Design patterns nào được sử dụng? (Builder, Factory, etc.)

2. **Xây dựng mô hình:**
   - Data models cần thiết
   - Interfaces/APIs design
   - Database schema (nếu có)

3. **Thư viện & Tools:**
   - Thư viện nào cần sử dụng?
   - Tools nào cần tích hợp?

### 2.3. Tuân thủ Steering Files (BẮT BUỘC)
**LLM PHẢI tuân thủ các file trong thư mục `.kiro/steering/` theo thứ tự ưu tiên từ Master Rules:**

1. **`00-MASTER-RULES.md`** (QUYỀN CAO NHẤT):
   - ⛔ Tất cả giao tiếp với user PHẢI bằng **TIẾNG VIỆT**
   - ⛔ Tuân thủ 5 bước phát triển feature
   - ⛔ Viết minimal code, không mock subject under test
   - ⛔ Dùng signals cho thread-safe UI updates

2. **`project-structure.md`** (Cấu trúc project):
   - ⛔ **`src/logic/`**: Pure business logic, KHÔNG có UI dependencies
   - ⛔ **`src/ui/`**: PyQt UI components, minimal logic
   - ⛔ **`tests/`**: Test files riêng biệt
   - ⛔ **`docs/`**: Documentation riêng biệt
   - ⛔ File size: Logic files < 500 lines, UI files < 400 lines

3. **`coding-guidelines.md`** (Coding standards):
   - ⛔ **Minimal Code:** Chỉ viết code tối thiểu cần thiết
   - ⛔ **No Mocking:** Không mock subject under test; có thể mock external dependencies khi cần
   - ⛔ **Type Hints:** Tất cả functions phải có type hints
   - ⛔ **Docstrings:** Ưu tiên cho public APIs, module phức tạp và hành vi không hiển nhiên
   - ⛔ **Builder Pattern:** Dùng cho complex object construction
   - ⛔ **Factory Pattern:** Dùng cho object creation với multiple implementations
   - ⛔ **Thread-Safe UI Updates:** KHÔNG update UI widgets trực tiếp từ background threads (phải dùng signals!)

4. **Persistence Rules** (QUAN TRỌNG!):
   Khi thêm settings mới vào action/tool, **BẮT BUỘC** đảm bảo:
   - ✅ Add field to UI dialog
   - ✅ Save to object in `get_settings()` method
   - ✅ Load from object in `_load_settings()` method
   - ✅ Verify field exists in `_action_to_dict()` in `tool_manager.py`
   - ✅ Verify field exists in `from_dict()` in `tool_manager.py`
   - ✅ Test: Save → close app → reopen → verify data persists

### 2.4. Viết code skeleton
- Viết code skeleton (không phải implementation đầy đủ)
- Chỉ viết class definitions, method signatures, type hints
- Không viết implementation logic

**Output Format cho design.md:**

```markdown
# Feature Design: [Tên Feature]

## 1. Impact Analysis

### 1.1. Tác động đến code hiện tại
- **Files cần sửa:**
  - [File 1]: [Mô tả thay đổi]
  - [File 2]: [Mô tả thay đổi]

- **Classes/methods bị ảnh hưởng:**
  - [Class 1]: [Mô tả ảnh hưởng]
  - [Method 1]: [Mô tả ảnh hưởng]

- **Breaking changes:** [Có/Không] - [Giải thích]

### 1.2. Dependencies
- **Thư viện mới cần thêm:**
  - [Library 1]: [Version] - [Mục đích]
  - [Library 2]: [Version] - [Mục đích]

- **Phụ thuộc modules:**
  - [Module 1]: [Mô tả phụ thuộc]
  - [Module 2]: [Mô tả phụ thuộc]

### 1.3. Khó khăn kỹ thuật
- [Khó khăn 1]: [Mô tả] - [Giải pháp đề xuất]
- [Khó khăn 2]: [Mô tả] - [Giải pháp đề xuất]

### 1.4. Rủi ro
- [Rủi ro 1]: [Mô tả] - [Cách giảm thiểu]
- [Rủi ro 2]: [Mô tả] - [Cách giảm thiểu]

## 2. Technical Design

### 2.1. Architecture
[Diagram hoặc mô tả architecture]

### 2.2. Design Patterns
- [Pattern 1]: [Tên pattern] - [Lý do sử dụng]
- [Pattern 2]: [Tên pattern] - [Lý do sử dụng]

### 2.3. Code Organization
- **Files được tạo:**
  - [New file 1]: [Mô tả chức năng]
  - [New file 2]: [Mô tả chức năng]

- **Files được sửa:**
  - [Modified file 1]: [Mô tả thay đổi]
  - [Modified file 2]: [Mô tả thay đổi]

## 3. Code Skeleton

### 3.1. [Tên Class 1]
```python
class ClassName1:
    """Docstring cho class."""
    
    def __init__(self, param1: type, param2: type = default):
        """Initialize."""
        pass
    
    def method1(self, param: type) -> return_type:
        """Docstring cho method."""
        pass
```

### 3.2. [Tên Class 2]
```python
class ClassName2:
    """Docstring cho class."""
    
    def method1(self, param: type) -> return_type:
        """Docstring cho method."""
        pass
```

[Tiếp tục cho tất cả classes...]
```

**Lưu vào:** `.kiro/specs/[feature-name]/design.md`

**Checklist kiểm tra format design.md:**
- [ ] File có đúng path `.kiro/specs/[feature-name]/design.md`?
- [ ] Có section "Impact Analysis" đầy đủ?
- [ ] Có phân tích tác động đến code hiện tại?
- [ ] Có liệt kê dependencies và thư viện mới?
- [ ] Có xác định khó khăn kỹ thuật và giải pháp?
- [ ] Có đánh giá rủi ro và cách giảm thiểu?
- [ ] Có section "Technical Design" với architecture?
- [ ] Có mô tả design patterns được sử dụng?
- [ ] Có liệt kê files được tạo/sửa?
- [ ] Có code skeleton với class definitions và method signatures?
- [ ] Code skeleton có type hints và docstrings?
- [ ] **Đã tuân thủ Master Rules (giao tiếp tiếng Việt, 5 bước, minimal code, signals cho UI updates)?**
- [ ] **Đã tuân thủ project structure (src/logic/, src/ui/, tests/, docs/)?**
- [ ] **Đã tuân thủ coding guidelines (no mocking, type hints, docstrings, builder/factory patterns)?**
- [ ] **Đã xem xét persistence rules (nếu thêm settings mới)?**
- [ ] Tất cả thông tin đã đầy đủ và rõ ràng?

**Checkpoint:** LLM hỏi user: "Design này có OK không? Nếu OK tôi sẽ chuyển sang Bước 3."

---

## BƯỚC 3: VIẾT TEST TRƯỚC KHI CODE (Test-First Approach)

**Mục tiêu:** Viết tất cả các loại test cần thiết trước khi bắt đầu code implementation.

**LLM phải viết 3 loại test:**

### 3.1. Unit Tests
- Test các use cases chính từ requirements
- Test edge cases
- Test error handling
- **KHÔNG mock subject under test** - có thể mock external dependencies khi cần thiết

**Format:**
```python
# tests/test_[feature_name].py

def test_[scenario_name]():
    """Test [mô tả ngắn gọn]."""
    # Arrange
    [setup data]
    
    # Act
    result = [call function]
    
    # Assert
    assert result == expected

def test_[edge_case_name]():
    """Test [mô tả edge case]."""
    # Arrange
    [setup data]
    
    # Act
    result = [call function]
    
    # Assert
    assert result == expected
```

### 3.2. Integration Tests
- Test interaction giữa các components
- Test end-to-end flow
- Test với real dependencies

**Format:**
```python
# tests/test_[feature_name]_integration.py

def test_[integration_scenario]():
    """Test integration [mô tả]."""
    # Setup
    [setup components]
    
    # Execute
    result = [call integrated flow]
    
    # Verify
    assert result == expected
```

### 3.3. Manual Test Plan
- Test plan để user tự test end-to-end
- Các bước thực hiện cụ thể
- Kết quả mong đợi rõ ràng

**Format:**
```markdown
# Manual Test Plan: [Feature Name]

## Test Case 1: [Tên test case]
**Mục đích:** [Mô tả]

**Điều kiện tiên quyết:**
- [Điều kiện 1]
- [Điều kiện 2]

**Các bước thực hiện:**
1. [Bước 1]
2. [Bước 2]
3. [Bước 3]

**Kết quả mong đợi:**
- [Kết quả 1]
- [Kết quả 2]

**Cài đặt cần kiểm tra:**
- [Setting 1]: [Giá trị]
- [Setting 2]: [Giá trị]

---

## Test Case 2: ...
[Tương tự]
```

**Output:**
- File `tests/test_[feature].py` với unit tests
- File `tests/test_[feature]_integration.py` với integration tests (nếu cần)
- File `docs/MANUAL_TEST_[feature].md` với manual test plan

**Checklist kiểm tra tests:**
- [ ] File unit tests có đúng path `tests/test_[feature].py`?
- [ ] Có test các use cases chính từ requirements?
- [ ] Có test edge cases?
- [ ] Có test error handling?
- [ ] **KHÔNG mock subject under test**?
- [ ] Có integration tests (nếu cần)?
- [ ] File manual test plan có đúng path `docs/MANUAL_TEST_[feature].md`?
- [ ] Manual test plan có các test case cụ thể?
- [ ] Mỗi test case có mục đích, điều kiện tiên quyết, các bước thực hiện, kết quả mong đợi?
- [ ] Tất cả tests đã cover đủ các yêu cầu từ Bước 1 và 2?

**Checkpoint:** LLM hỏi user: "Tests này có OK không? Nếu OK tôi sẽ chuyển sang Bước 4."

---

## BƯỚC 4: TRIỂN KHAI CODE & TEST (Implementation & Testing)

**Mục tiêu:** Code implementation hoàn chỉnh theo design từ Bước 2, chạy tests từ Bước 3, và review để đảm bảo đáp ứng yêu cầu.

**LLM phải làm:**

### 4.1. Triển khai code (Implementation)
1. **Minimal Code:**
   - Chỉ viết code tối thiểu cần thiết
   - Không over-engineer
   - Tuân thủ coding guidelines

2. **Tuân thủ Coding Standards:**
   - Type hints cho tất cả functions
   - Docstrings cho public APIs, module phức tạp và hành vi không hiển nhiên
   - Error handling đầy đủ
   - File size limits được xem là guideline, không phải hard gate

3. **Incremental Implementation:**
   - Code từng phần nhỏ
   - Test ngay sau mỗi phần
   - Commit khi user yêu cầu hoặc khi workflow cho phép

### 4.2. Chạy tests
1. Chạy unit tests (từ Bước 3.1)
2. Chạy integration tests (từ Bước 3.2)
3. Nếu test fail → Fix và chạy lại
4. Nếu test pass → Tiếp tục

### 4.3. Review code
1. **Review đáp ứng yêu cầu từ Bước 1:**
   - Code có giải quyết đúng vấn đề không?
   - Input/Output có đúng như requirements?
   - Edge cases có được xử lý đúng?

2. **Review đáp ứng design từ Bước 2:**
   - Code có follow đúng architecture không?
   - Có sử dụng đúng design patterns không?
   - Files được tạo/sửa có đúng như design?

3. **Review coding standards:**
   - Có type hints đầy đủ?
   - Có docstrings đầy đủ?
   - Có error handling đầy đủ?
   - **Có dùng signals cho thread-safe UI updates?** (CRITICAL!)

**Trong quá trình code:**
- Nếu gặp vấn đề → Hỏi user ngay
- Không tự ý thay đổi requirement
- Không tự ý thay đổi design mà không hỏi user

**Output:** Code hoàn chỉnh, tất cả tests pass.

**Checklist kiểm tra implementation:**
- [ ] Code đã implement đầy đủ theo design từ Bước 2?
- [ ] Tất cả unit tests pass?
- [ ] Tất cả integration tests pass?
- [ ] Code có type hints đầy đủ?
- [ ] Code có docstrings đầy đủ?
- [ ] Code có error handling đầy đủ?
- [ ] **UI updates có dùng signals với QueuedConnection?** (CRITICAL!)
- [ ] File size < 500 lines (logic) / < 400 lines (UI)?
- [ ] Code có giải quyết đúng vấn đề từ Bước 1?
- [ ] Input/Output có đúng như requirements?
- [ ] Edge cases có được xử lý đúng?
- [ ] Có follow đúng architecture từ design?
- [ ] Có sử dụng đúng design patterns?

**Checkpoint:** LLM thông báo: "Code đã hoàn thành, tất cả tests pass. Tôi sẽ chuyển sang Bước 5."

---

## BƯỚC 5: COMMIT & BÁO CÁO (Commit & Documentation)

**Mục tiêu:** Commit code, update documentation, và viết báo cáo hoàn thành feature.

**LLM phải làm:**

### 5.1. Commit code

**Quy tắc commit message — BẮT BUỘC:**
- Commit message phải mô tả đúng công việc đã làm, không dùng message chung chung
- Format chuẩn:
  ```
  <type>(<scope>): <mô tả ngắn gọn>

  - <chi tiết thay đổi 1>
  - <chi tiết thay đổi 2>
  ```
- `<type>`: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`
- `<scope>`: tên feature hoặc module bị ảnh hưởng (ví dụ: `special-event-tracking`, `tool-manager`)
- **Khi commit fix review findings: BẮT BUỘC ghi Review ID vào body của commit message**
- Ví dụ đúng (fix review):
  ```
  fix(special-event-tracking): sua subscription identity theo dung format spec

  Fixes: REV-20260421-105721/F-002
  - Doi special_event_imperial_guardian_{key} thanh special_event:{key}:imperial_guardian
  - Dong bo voi requirements.md, design.md va manual test plan
  ```
- Ví dụ đúng (step thường):
  ```
  feat(special-event-tracking): Buoc 4 - implement ImperialGuardianHandler va UI

  - Them ImperialGuardianHandler voi state machine WAITING/OPEN/CLOSED
  - Them 7 fields imperial_guardian_* vao AutoAction
  - Cap nhat persistence trong tool_manager.py
  - Them UI Special Event Tracking vao PassiveReadSettingsDialog
  ```
- Ví dụ sai: `update`, `fix bug`, `[Feature] special event`

**Thời điểm commit bắt buộc:**
1. Sau khi hoàn thành và được approve mỗi bước (Bước 1, 2, 3, 4)
2. Sau khi fix xong tất cả findings trong một review block — **phải ghi Review ID**
3. Bước 5 là commit tổng kết cuối cùng

```bash
git add -A
git commit -m "<type>(<scope>): <mô tả công việc thực tế>"
```

### 5.2. Update documentation
1. **Update README** nếu cần
2. **Thêm docstrings** đầy đủ cho code mới
3. **Ghi chú technical notes** quan trọng
4. **Update project structure documentation** nếu có thay đổi

### 5.3. Tạo báo cáo hoàn thành
**Format:**
```markdown
## Tóm tắt Feature: [Tên Feature]

**Đã hoàn thành:**
- [Item 1]: [Mô tả ngắn]
- [Item 2]: [Mô tả ngắn]
- [Item 3]: [Mô tả ngắn]

**Files thay đổi:**
- [File 1]: [Mô tả thay đổi]
- [File 2]: [Mô tả thay đổi]
- [File 3]: [Mô tả thay đổi]

**Tests:**
- ✅ Unit tests: [Số lượng] tests pass
- ✅ Integration tests: [Số lượng] tests pass
- 📋 Manual test plan: `docs/MANUAL_TEST_[feature].md`

**Commit:** [commit hash]

**Manual Test:**
Vui lòng test theo hướng dẫn tại: `docs/MANUAL_TEST_[feature].md`
```

### 5.4. User tự test
- User tự test theo manual test plan từ Bước 3.3
- LLM chờ feedback từ user

**Output:**
- Code đã được commit
- Documentation đã được update
- Báo cáo hoàn thành feature
- User đã test theo manual test plan

**Checklist kiểm tra Bước 5:**
- [ ] Code đã được commit với message rõ ràng?
- [ ] Documentation đã được update đầy đủ?
- [ ] Có báo cáo hoàn thành feature?
- [ ] Báo cáo có liệt kê đầy đủ các items hoàn thành?
- [ ] Báo cáo có liệt kê files thay đổi?
- [ ] Báo cáo có thông tin về tests?
- [ ] Báo cáo có commit hash?
- [ ] Báo cáo có hướng dẫn manual test?
- [ ] User đã được thông báo để test theo manual test plan?

**LLM thông báo:** "✅ Feature đã hoàn thành! Vui lòng test theo hướng dẫn tại: `docs/MANUAL_TEST_[feature].md`"

---

## QUY TẮC BẮT BUỘC

1. ⛔ **LLM KHÔNG ĐƯỢC BỎ QUA BẤT KỲ BƯỚC NÀO**
2. ⛔ **Mỗi bước phải có output rõ ràng**
3. ⛔ **Phải chờ user approve trước khi chuyển bước (Bước 1, 2, 3)**
4. ⛔ **Nếu user yêu cầu quay lại bước nào, LLM phải quay lại đúng bước đó**
5. ⛔ **LLM phải hỏi khi không chắc chắn, không tự ý đoán**
6. ⛔ **Tất cả communication bằng tiếng Việt**
7. ⛔ **Không được code trước khi có tests (Bước 3)**
8. ⛔ **Không được commit nếu tests chưa pass**
9. ⛔ **KHÔNG được mock subject under test trong tests**
10. ⛔ **KHÔNG được update UI widgets trực tiếp từ background threads (phải dùng signals!)**
11. ⛔ **BẮT BUỘC commit sau mỗi bước được approve và sau mỗi lần fix xong review findings**
12. ⛔ **Commit message PHẢI mô tả đúng công việc thực tế — không dùng message chung chung**

---

## NHẬN DIỆN FEATURE MỚI

LLM phải áp dụng quy trình này khi:
- User nói "tôi muốn thêm feature..."
- User nói "làm một tính năng mới..."
- User mô tả một chức năng chưa có trong hệ thống
- User yêu cầu "implement..." một feature mới

**Không áp dụng khi:**
- Fix bug (dùng quy trình fix bug riêng)
- Refactor code hiện tại
- Update documentation
- Chỉnh sửa nhỏ (minor changes)

---

## CHECKPOINT COMPLIANCE

Trước mỗi bước quan trọng, LLM phải tự kiểm tra:
- [ ] Đã hoàn thành bước trước chưa?
- [ ] Đã có output rõ ràng chưa?
- [ ] Đã được user approve chưa? (nếu cần)
- [ ] Có thể chuyển sang bước tiếp theo không?

Nếu bất kỳ câu trả lời nào là "Không" → DỪNG LẠI và hoàn thành bước hiện tại.

---

## VÍ DỤ CONVERSATION

**User:** "Tôi muốn thêm feature export tool ra file JSON"

**LLM (Bước 1):**
```
Tôi hiểu yêu cầu của bạn như sau:
- Feature: Export tool configuration ra file JSON
- Input: Tool object hiện tại
- Output: File JSON chứa toàn bộ cấu hình tool

Tôi cần làm rõ thêm:
1. File JSON này có format đặc biệt không? Hay giống format hiện tại trong tools/ folder?
2. User chọn đường dẫn save file hay tự động save?
3. Có cần import ngược lại từ JSON không?
```

**User:** "Format giống hiện tại, user chọn đường dẫn, không cần import"

**LLM (Bước 1 - tiếp):**
```
[Viết requirements.md với format đầy đủ...]

Requirements này có OK không? Nếu OK tôi sẽ chuyển sang Bước 2.
```

**User:** "OK"

**LLM (Bước 2):**
```
[Viết design.md với impact analysis + technical design + code skeleton...]

Design này có OK không? Nếu OK tôi sẽ chuyển sang Bước 3.
```

**User:** "OK"

**LLM (Bước 3):**
```
[Viết tests...]

Tests này có OK không? Nếu OK tôi sẽ chuyển sang Bước 4.
```

**User:** "OK"

**LLM (Bước 4):**
```
[Code implementation...]

Code đã hoàn thành, tất cả tests pass. Tôi sẽ chuyển sang Bước 5.
```

**LLM (Bước 5):**
```
✅ Feature đã hoàn thành!

**Đã hoàn thành:**
- Thêm button "Export" vào tool editor window
- Implement logic export tool ra file JSON
- User có thể chọn đường dẫn save file

**Files thay đổi:**
- src/ui/tool_editor_window.py: Thêm button "Export" và handler
- src/logic/tool_manager.py: Thêm method export_tool_to_json()

**Tests:**
- ✅ Unit tests: 5 tests pass
- 📋 Manual test plan: `docs/MANUAL_TEST_EXPORT_TOOL.md`

**Commit:** abc123def456

**Manual Test:**
Vui lòng test theo hướng dẫn tại: `docs/MANUAL_TEST_EXPORT_TOOL.md`
```

