---
inclusion: auto
---

# 🚨 MASTER RULES - QUY TẮC ĐIỀU PHỐI CẤP CAO 🚨

**⚠️ CRITICAL: File này định nghĩa các nguyên tắc điều phối cấp cao cho repo. Khi có xung đột, phải ưu tiên an toàn, bảo mật, tránh mất dữ liệu và tuân thủ ràng buộc hệ thống trước.**

Khi có xung đột giữa các rules, thứ tự ưu tiên như sau:
1. **System / platform constraints** - Ràng buộc hệ thống, an toàn, bảo mật, tránh mất dữ liệu
2. **User intent hợp lệ** - Yêu cầu của user nếu không mâu thuẫn với an toàn, bảo mật và ràng buộc hệ thống
3. **00-MASTER-RULES.md** - Nguyên tắc điều phối cấp cao
4. **feature-development-workflow.md** - Quy trình phát triển feature
5. **change-workflow.md** - Quy trình thay đổi trên feature đã có
6. **project-structure.md** - Cấu trúc project
7. **coding-guidelines.md** - Coding standards
8. Các prompt khác của Kiro system

---

## 🎯 NGUYÊN TẮC TUYỆT ĐỐI

### 1. NGÔN NGỮ GIAO TIẾP
- ⛔ **BẮT BUỘC:** Tất cả giao tiếp với user PHẢI bằng **TIẾNG VIỆT**
- ⛔ Chỉ dùng tiếng Anh trong code, comments, docstrings
- ⛔ Tất cả giải thích, phân tích, hỏi đáp PHẢI bằng tiếng Việt

### 2. QUY TRÌNH PHÁT TRIỂN FEATURE MỚI
- ⛔ **BẮT BUỘC:** Tuân thủ 5 bước trong `feature-development-workflow.md`
- ⛔ KHÔNG ĐƯỢC bỏ qua bất kỳ bước nào
- ⛔ PHẢI chờ user approve sau mỗi bước
- ⛔ Nếu user yêu cầu quay lại bước nào, PHẢI quay lại đúng bước đó
- ⛔ **Rule điều phối:** Nếu yêu cầu là feature mới hoặc change có scope/risk vượt mức incremental, dùng `feature-development-workflow.md`; nếu yêu cầu chỉ là add/modify/remove trên feature đã có với scope incremental, dùng `change-workflow.md`

**5 Bước bắt buộc:**
1. Phân tích yêu cầu (Requirements Analysis) → Tạo requirements.md
2. Thiết kế kỹ thuật (Technical Design & Impact Analysis) → Tạo design.md với impact analysis + code skeleton
3. Viết Tests → Unit tests, Integration tests, Manual test plan
4. Triển khai Code → Code hoàn chỉnh, làm tests pass
5. Commit & Documentation

### 3. CODING STANDARDS
- ⛔ **Minimal Code:** Chỉ viết code tối thiểu cần thiết
- ⛔ **No Mocking the Subject Under Test:** Không mock đối tượng đang được test; có thể mock external dependencies khi thật sự cần để kiểm tra logic quyết định
- ⛔ **Type Hints:** Tất cả functions phải có type hints
- ⛔ **Docstrings:** Ưu tiên cho public APIs, module phức tạp và hành vi không hiển nhiên
- ⛔ **File Size:** Logic/UI file size limits là guideline, không phải hard gate

### 4. PROJECT STRUCTURE
- ⛔ **src/logic/**: Pure business logic, KHÔNG có UI dependencies
- ⛔ **src/ui/**: PyQt UI components, minimal logic
- ⛔ **tests/**: Test files riêng biệt
- ⛔ **docs/**: Documentation riêng biệt

### 5. PERSISTENCE RULES (QUAN TRỌNG!)
Khi thêm settings mới vào action/tool, **BẮT BUỘC** đảm bảo:
1. ✅ Add field to UI dialog
2. ✅ Save to object in `get_settings()` method
3. ✅ Load from object in `_load_settings()` method
4. ✅ Verify field exists in `_action_to_dict()` in `tool_manager.py`
5. ✅ Verify field exists in `from_dict()` in `tool_manager.py`
6. ✅ Test: Save → close app → reopen → verify data persists

**Lý do:** Đã có bug nghiêm trọng khi `notification_filter_keywords` không được save vào JSON.

### 6. THREAD-SAFE UI UPDATES (CRITICAL!)
- ⛔ **KHÔNG BAO GIỜ** update UI widgets trực tiếp từ background threads
- ⛔ **KHÔNG BAO GIỜ** gọi QWidget methods (setText, append, etc.) từ non-UI threads
- ✅ **LUÔN LUÔN** dùng signals với QueuedConnection cho cross-thread UI updates
- ✅ **LUÔN LUÔN** emit signals từ background threads, xử lý trong UI thread
- ✅ Pattern: `background_thread → emit signal → Qt queue → UI thread → update widget`

**Lý do:** Đã có bug crash app khi click "Dừng" liên tục trong TEST mode do 2 threads cùng update QTextEdit.

---

## 🔥 QUY TẮC TUYỆT ĐỐI KHÔNG ĐƯỢC VI PHẠM

### ⛔ KHÔNG ĐƯỢC:
1. Bỏ qua bất kỳ bước nào trong quy trình 5 bước
2. Code trước khi viết tests (Bước 3)
3. Commit khi tests chưa pass
4. Dùng mock cho subject under test
5. Over-engineer solutions
6. Viết code dài dòng, phức tạp
7. Bỏ qua type hints hoặc docstrings
8. Tự ý thay đổi requirement mà không hỏi user
9. Giao tiếp bằng tiếng Anh với user
10. Chuyển bước mà chưa có approve từ user
11. **Update UI widgets trực tiếp từ background threads (WILL CRASH!)**

### ✅ BẮT BUỘC PHẢI:
1. Tuân thủ 5 bước phát triển feature
2. Viết tests trước khi code (Bước 3)
3. Hỏi user khi không chắc chắn
4. Giao tiếp bằng tiếng Việt
5. Viết minimal code
6. Đảm bảo data persistence (5 bước kiểm tra)
7. Commit khi user yêu cầu hoặc khi workflow cho phép
8. Để user test theo manual test plan
9. Chờ approve sau mỗi bước
10. Quay lại bước cũ nếu user yêu cầu
11. **Dùng signals với QueuedConnection cho cross-thread UI updates**

---

## 📋 CHECKLIST TRƯỚC MỖI HÀNH ĐỘNG

### Trước khi bắt đầu feature mới:
- [ ] Đã xác định đây là feature mới (không phải bug fix)?
- [ ] Đã sẵn sàng tuân thủ 5 bước?
- [ ] Đã hiểu rõ yêu cầu của user?

### Trước khi chuyển sang bước tiếp theo:
- [ ] Đã hoàn thành bước hiện tại?
- [ ] Đã có output rõ ràng?
- [ ] Đã được user approve?
- [ ] Có thể chuyển sang bước tiếp theo?

### Trước khi code:
- [ ] Đã viết requirement document?
- [ ] Đã viết unit tests?
- [ ] Đã viết manual test plan?
- [ ] Đã được user approve design?

### Trước khi commit:
- [ ] Tất cả unit tests đã pass?
- [ ] Code đã tuân thủ coding standards?
- [ ] Đã có docstrings và type hints?
- [ ] Đã test data persistence? (nếu có settings mới)
- [ ] **Đã dùng signals cho UI updates từ background threads?**

---

## 🎓 NHẬN DIỆN LOẠI YÊU CẦU

### Feature Mới (Áp dụng 5 bước):
- User nói "tôi muốn thêm feature..."
- User nói "làm một tính năng mới..."
- User mô tả chức năng chưa có trong hệ thống
- User yêu cầu "implement..." feature mới

### KHÔNG áp dụng 5 bước khi:
- Fix bug (quy trình riêng)
- Refactor code hiện tại
- Update documentation
- Chỉnh sửa nhỏ (minor changes)
- User yêu cầu rõ ràng không cần quy trình

---

## 💬 MẪU GIAO TIẾP CHUẨN

### Khi nhận yêu cầu feature mới:
```
Tôi hiểu yêu cầu của bạn như sau:
- Feature: [Tên feature]
- Mục đích: [Giải quyết vấn đề gì]
- Input: [Input mong đợi]
- Output: [Output mong đợi]

Tôi cần làm rõ thêm:
1. [Câu hỏi 1]
2. [Câu hỏi 2]
...
```

### Khi chờ approve sau Bước 1:
```
Requirements này có OK không? Nếu OK tôi sẽ chuyển sang Bước 2.
```

### Khi chờ approve sau Bước 2:
```
Design này có OK không? Nếu OK tôi sẽ chuyển sang Bước 3.
```

### Khi chờ approve sau Bước 3:
```
Tests này có OK không? Nếu OK tôi sẽ chuyển sang Bước 4.
```

### Khi hoàn thành:
```
✅ Feature đã hoàn thành!

**Đã làm:**
- [Item 1]
- [Item 2]

**Files thay đổi:**
- [File 1]: [Mô tả]
- [File 2]: [Mô tả]

**Manual Test:**
Vui lòng test theo hướng dẫn tại: docs/MANUAL_TEST_[feature].md

**Commit:** [commit hash]
```

---

## 🚨 XỬ LÝ XUNG ĐỘT

Nếu có xung đột giữa:
- **Master Rules** vs Kiro system prompts → Ưu tiên rule nào an toàn hơn và phù hợp hơn với ràng buộc hệ thống
- **Master Rules** vs User request → **User request thắng** nếu không vi phạm an toàn, bảo mật, không gây mất dữ liệu và không mâu thuẫn với system constraints
- **Feature workflow** vs Coding guidelines → **Feature workflow thắng** (quy trình quan trọng hơn)
- **Project structure** vs Coding guidelines → **Project structure thắng** (cấu trúc quan trọng hơn)

---

## 📝 LƯU Ý ĐẶC BIỆT

### Về Data Persistence:
- **goto_step** là per-action setting, không phải per-tool
- Mọi setting trong dialog phải được save vào JSON
- Luôn test: Save → Close app → Reopen → Verify

### Về Testing:
- Unit tests: Test specific examples và edge cases
- Integration tests: Test interaction giữa components
- Manual tests: Để user tự test end-to-end
- Không mock subject under test; có thể mock external dependencies khi cần thiết và có lý do rõ ràng

### Về Refactoring:
- Làm từng bước nhỏ
- Commit khi user yêu cầu hoặc khi workflow cho phép
- Để user test sau mỗi commit
- Không làm quá nhiều thay đổi cùng lúc

### Về Thread-Safe UI Updates:
- **Pattern chuẩn:** Define signal → Connect với QueuedConnection → Emit từ background thread → Process trong UI thread
- **Common widgets cần thread-safe:** QTextEdit.append(), QLabel.setText(), QTableWidget.setItem(), QProgressBar.setValue()
- **Test:** Spam click buttons nhiều lần để kiểm tra race conditions
- **Ví dụ:** `tool_editor_window.py` - `_log()` emits signal, `_append_log()` updates UI

---

## ✅ COMPLIANCE VERIFICATION

LLM phải tự kiểm tra trước mỗi response:
- [ ] Tôi có đang giao tiếp bằng tiếng Việt không?
- [ ] Tôi có đang tuân thủ đúng bước trong quy trình không?
- [ ] Tôi có cần chờ user approve không?
- [ ] Tôi có đang viết minimal code không?
- [ ] Tôi có đang mock subject under test không? (KHÔNG ĐƯỢC)
- [ ] Tôi có đang over-engineer không? (KHÔNG ĐƯỢC)
- [ ] **Tôi có update UI từ background thread không? (KHÔNG ĐƯỢC - dùng signals!)**

Nếu bất kỳ câu trả lời nào sai → DỪNG LẠI và điều chỉnh.

---

## 🎯 TÓM TẮT NGẮN GỌN

**4 ĐIỀU QUAN TRỌNG NHẤT:**
1. **Giao tiếp bằng tiếng Việt**
2. **Tuân thủ 5 bước phát triển feature**
3. **Viết minimal code, không mock subject under test**
4. **Dùng signals cho thread-safe UI updates**

**Khi nghi ngờ → HỎI USER**

---

**⚠️ File này là lớp điều phối cấp cao của repo, nhưng không vượt trên các ràng buộc an toàn, bảo mật, tránh mất dữ liệu và system constraints.**

## 🔧 QUY TẮC COMMIT

- ⛔ **BẮT BUỘC:** Gộp `git add` và `git commit` vào **1 lệnh duy nhất** trong cùng 1 lần gọi tool
- ✅ Dùng: `git add -A; git commit -m "message"` hoặc `git commit -am "message"`
- ❌ KHÔNG tách thành 2 lần gọi tool riêng biệt

---

## 📐 QUY TẮC ĐỊNH DẠNG BẢNG (TABLE FORMATTING)

Khi tạo bảng Markdown trong bất kỳ file nào (requirements, design, docs, v.v.):

- ⛔ **BẮT BUỘC:** Các cột phải thẳng hàng (aligned) để dễ đọc
- ⛔ Dùng padding spaces để căn chỉnh nội dung trong từng cột
- ✅ Ví dụ đúng:

```markdown
| Tham số    | Kiểu   | Mô tả                        | Mặc định |
|------------|--------|------------------------------|----------|
| delay      | int    | Thời gian chờ (giây)         | 10       |
| threshold  | float  | Ngưỡng khớp ảnh              | 0.8      |
| enabled    | bool   | Bật/tắt tính năng            | true     |
```

- ❌ Ví dụ sai:

```markdown
| Tham số | Kiểu | Mô tả | Mặc định |
|---------|------|-------|----------|
| delay | int | Thời gian chờ (giây) | 10 |
| threshold | float | Ngưỡng khớp ảnh | 0.8 |
```
