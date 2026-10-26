---
inclusion: auto
---

# CHANGE WORKFLOW - QUY TRÌNH THÊM / SỬA / XÓA TRÊN FEATURE ĐÃ CÓ

**QUAN TRỌNG:** Quy trình này áp dụng cho các thay đổi trên feature đã tồn tại nhằm giảm effort so với `feature-development-workflow.md`, nhưng vẫn phải kiểm soát impact, regression, persistence, và compatibility. Nếu thay đổi đủ lớn hoặc đủ rủi ro, phải quay lại full 5-step workflow.

---

## MỤC TIÊU

Quy trình này dùng để xử lý các thay đổi kiểu:

- Thêm option/setting vào feature đã có
- Sửa behavior trong feature đã có
- Xóa behavior, setting, hoặc flow cũ
- Điều chỉnh persistence, validation, UI flow, hoặc test của feature hiện hữu

Mục tiêu:

- Giảm effort tài liệu và quy trình so với feature mới hoàn toàn
- Giữ trace rõ giữa change intent, impact, tests, implementation, và verification
- Tránh phá vỡ behavior cũ đang chạy ổn định

---

## KHI NÀO ÁP DỤNG

### Áp dụng change workflow khi:

- Change nằm trên một feature đã tồn tại
- Có thể mô tả change như add / modify / remove trên behavior hiện có
- Không tạo ra một nghiệp vụ hoàn toàn mới với flow độc lập
- Không thay đổi lớn architecture hoặc shared contract

### KHÔNG áp dụng change workflow khi:

- Tạo feature mới hoàn toàn
- Thêm sub-feature lớn có flow riêng, settings riêng, hoặc lifecycle riêng
- Thay đổi shared service / shared contract ảnh hưởng nhiều feature
- Có migration dữ liệu hoặc schema change lớn
- Có background thread / async / subscription lifecycle mới với rủi ro cao

Các trường hợp trên phải dùng lại `feature-development-workflow.md`.

---

## PHÂN LOẠI MỨC ĐỘ THAY ĐỔI

### Level 1 - Safe Change

Ví dụ:

- Đổi label, text, log
- Chỉnh default value nhỏ
- Bổ sung test
- Chỉnh docs
- Fix nhỏ không đổi business flow

Yêu cầu:

- Có change intent ngắn
- Có impact note ngắn
- Có verify phù hợp

### Level 2 - Behavior Change

Ví dụ:

- Thêm option/setting mới
- Sửa validation
- Sửa điều kiện xử lý
- Đổi UI flow nhỏ
- Đổi persistence của feature hiện có
- Xóa một behavior đã có nhưng không đổi architecture tổng thể

Yêu cầu:

- Có change intent
- Có impact analysis
- Có targeted tests
- Có regression verification
- Update spec/design nếu contract thay đổi

### Level 3 - Risky Change

Ví dụ:

- Đổi module interaction
- Đổi shared service/base component
- Đổi background thread / callback / subscription flow
- Đổi serialization/schema có compatibility risk
- Xóa behavior cũ mà nhiều module khác có thể phụ thuộc

Yêu cầu:

- Mặc định **không dùng quy trình nhẹ**
- Phải nâng lên full `feature-development-workflow.md`, hoặc chỉ dùng change workflow nếu user chấp thuận rõ ràng và impact đã được mô tả đầy đủ

---

## QUY TRÌNH 5 BƯỚC NHẸ

## BƯỚC 1: CHANGE INTENT

**Mục tiêu:** Làm rõ thay đổi gì trên feature đang có.

LLM phải mô tả ngắn:

- Change type: `add` / `modify` / `remove`
- Target feature
- Mục đích thay đổi
- Hành vi nào phải giữ nguyên
- Cái gì nằm ngoài scope

**Output Format:**

```markdown
## 1. CHANGE INTENT

**Change type:** [add/modify/remove]

**Target feature:**
[Tên feature]

**Change:**
[Mô tả ngắn thay đổi]

**Reason:**
[Vì sao cần thay đổi]

**Keep unchanged:**
- [Behavior 1]
- [Behavior 2]

**I/O affected:**
- [add/modify/remove] [Tác nhân]: [Input/Output nghiệp vụ, kể cả lỗi] (hoặc `None`)

**Out of scope:**
- [Item 1]
- [Item 2]
```

**Checkpoint:** LLM hỏi user: `Change intent này có OK không? Nếu OK tôi sẽ chuyển sang Bước 2.`

---

## BƯỚC 2: IMPACT & RISK

**Mục tiêu:** Xác định thay đổi này có thể làm hỏng cái gì.

LLM phải kiểm tra:

- File nào sẽ bị chạm
- Behavior cũ nào có nguy cơ bị ảnh hưởng
- Có đụng persistence không
- Có đụng UI/thread/shared logic không
- Có cần update requirements/design hiện có không
- Change này còn đủ nhẹ để ở change workflow hay phải nâng lên full workflow

**Output Format:**

```markdown
## 2. IMPACT & RISK

**Level:** [1/2/3]

**Files expected to change:**
- [File 1]: [Impact]
- [File 2]: [Impact]

**Existing behavior at risk:**
- [Risk 1]
- [Risk 2]

**Persistence impact:**
[None / Mô tả cụ thể]

**UI/thread/shared-module impact:**
[None / Mô tả cụ thể]

**Spec update needed:**
- Requirements: [yes/no] (bắt buộc `yes` nếu I/O affected khác `None`)
- Design/technical requirements: [yes/no] - [mục kỹ thuật tương ứng với I/O thay đổi]
- Tasks: [yes/no]

**Workflow decision:**
- [Keep change workflow / Escalate to full 5-step]
```

### Rule escalation

Nếu có một trong các điều kiện sau, phải dừng và dùng full workflow:

- Thêm sub-feature mới có flow riêng
- Đổi contract giữa modules
- Đổi shared service
- Có migration data/schema
- Có background thread / async risk đáng kể
- Không thể mô tả impact ngắn gọn, rõ ràng

**Checkpoint:** LLM hỏi user: `Impact này có OK không? Nếu OK tôi sẽ chuyển sang Bước 3.`

---

## BƯỚC 3: TARGETED TESTS

**Mục tiêu:** Viết phần test đủ để chứng minh change mới an toàn.

LLM phải xác định tối thiểu 3 nhóm kiểm tra:

1. **Change tests**
   - Test đúng phần được thêm/sửa/xóa

2. **Regression tests**
   - Test behavior cũ dễ bị ảnh hưởng

3. **Manual / persistence checks** nếu có
   - Nếu đụng setting/UI/data thì phải có save/load/manual verification

**Output Format:**

```markdown
## 3. TARGETED TESTS

**Change tests:**
- [Test 1]
- [Test 2]

**Regression tests:**
- [Test 1]
- [Test 2]

**Manual / persistence checks:**
- [Check 1]
- [Check 2]

**Out-of-scope tests:**
- [Không cần test gì thêm và vì sao]
```

### Rules

- Đổi logic -> phải có regression test
- Đổi setting -> phải có persistence check
- Đổi UI flow -> phải có manual checklist ngắn
- Xóa behavior -> phải có test xác nhận old behavior không còn và phần liên quan vẫn ổn
- Không mock subject under test

**Checkpoint:** LLM hỏi user: `Targeted tests này có OK không? Nếu OK tôi sẽ chuyển sang Bước 4.`

---

## BƯỚC 4: IMPLEMENTATION

**Mục tiêu:** Implement change theo scope hẹp nhất có thể.

LLM phải tuân thủ:

- Chỉ sửa file thực sự cần
- Không refactor lan rộng nếu không cần
- Không đổi contract ngoài scope đã chốt ở Bước 2
- Nếu change đụng spec/design thì update đúng file tương ứng
- Nếu change là remove, phải xóa sạch trace không còn hợp lệ trong spec/design/tests/docs liên quan
- Nếu I/O affected khác `None`, cập nhật bảng Input/Output trong `requirements.md` theo quy tắc của
  `feature-development-workflow.md` và cập nhật cột Chi tiết kỹ thuật; khi remove phải xóa cả dòng I/O và phần kỹ thuật

### Checklist implementation

- [ ] Code đúng scope
- [ ] Không over-engineer
- [ ] Có type hints nếu chạm code Python
- [ ] Có docstrings cho public API / logic không hiển nhiên
- [ ] Không phá persistence
- [ ] Không update UI trực tiếp từ background thread

**Output:** Code change hoàn tất, sẵn sàng verify.

Không tự chuyển sang Bước 5 nếu chưa chạy verify phù hợp.

---

## BƯỚC 5: VERIFY & COMMIT

**Mục tiêu:** Xác nhận change mới đúng và không phá feature cũ.

LLM phải verify theo đúng scope:

- Change tests pass
- Regression tests pass
- Persistence/manual check pass nếu có
- Spec/design sync nếu contract đổi
- Bảng Input/Output trong `requirements.md` khớp với behavior sau change
- Không còn `TBD` thuộc phần sẽ implementation trong change hiện tại
- Chỉ commit khi workflow/rule hiện hành cho phép

**Output Format:**

```markdown
## 5. VERIFY

**Tests run:**
- [Command 1]
- [Command 2]

**Result:**
- [Pass/fail summary]

**Verified unchanged behavior:**
- [Behavior 1]
- [Behavior 2]

**Docs/spec/design updated:**
- [File 1]
- [File 2]

**Remaining risk:**
- [Risk 1]
- [Risk 2]
```

Nếu commit:

```markdown
## COMMIT SUMMARY

**Commit message:**
`<type>(<scope>): <mô tả change thực tế>`

**Summary:**
- [Item 1]
- [Item 2]
```

---

## QUY TẮC UPDATE TÀI LIỆU

### Update `requirements.md` khi:

- Có thay đổi user-facing behavior
- Có thêm/xóa setting
- Có đổi input/output
- Có edge case hoặc error handling mới
- Có thay đổi persistence contract nhìn từ góc user/config

### Update `design.md` khi:

- Có đổi data model
- Có đổi module interaction
- Có đổi persistence implementation
- Có đổi runtime flow hoặc technical contract
- Có đổi thread/background/callback behavior

### Update `tasks.md` khi:

- Change đủ lớn để cần theo dõi implementation theo task
- Change đang nằm trong spec workstream chưa hoàn tất
- User muốn track implementation progress rõ

### Không bắt buộc update đủ cả 3 file khi:

- Change nhỏ, không đổi contract
- Chỉ là docs/test/fix nội bộ
- Chỉ chỉnh implementation mà spec/design vẫn còn đúng

---

## QUY TẮC RIÊNG CHO ADD / MODIFY / REMOVE

### Khi `add`

Phải chứng minh:

- Hành vi mới hoạt động
- Default behavior cũ không bị đổi ngoài ý muốn

### Khi `modify`

Phải mô tả rõ:

- Old behavior
- New behavior
- Vì sao đổi
- Behavior nào phải giữ nguyên

### Khi `remove`

Phải mô tả rõ:

- Bỏ cái gì
- Có gì thay thế hay không
- Test/docs/spec nào phải cập nhật theo
- Có backward compatibility risk không

---

## REVIEW CHECKLIST CHO CHANGE WORKFLOW

Reviewer phải ưu tiên kiểm tra:

- Change có đúng là incremental change, không phải feature mới trá hình
- Impact analysis có đủ rõ không
- Có regression coverage phù hợp không
- Có update spec/design đúng mức cần thiết không
- I/O affected có được phản ánh đủ trong bảng Input/Output và phần kỹ thuật tương ứng không
- Có persistence risk không
- Có làm ảnh hưởng feature cũ không
- Có mở rộng scope quá mức không

---

## CHECKPOINT COMPLIANCE

Trước mỗi bước quan trọng, LLM phải tự kiểm tra:

- [ ] Đây có thật sự là change trên feature đã có?
- [ ] Change có đang ở đúng level không?
- [ ] Có cần escalate lên full 5-step không?
- [ ] Đã xác định behavior cũ cần giữ chưa?
- [ ] Đã xác định regression checks chưa?
- [ ] Đã xác định spec/design nào cần update chưa?

Nếu bất kỳ câu trả lời nào là `Không` -> DỪNG LẠI và làm rõ trước khi code.

---

## TÓM TẮT

- Feature mới -> dùng `feature-development-workflow.md`
- Change trên feature đã có -> dùng `change-workflow.md`
- Nếu change đủ rủi ro -> quay lại full workflow
- Mục tiêu của `change-workflow.md` là:
  - ít effort hơn
  - vẫn có trace
  - vẫn có regression control
  - không phá feature đang có
