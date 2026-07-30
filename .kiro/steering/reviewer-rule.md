---
inclusion: auto
---

# Reviewer Rule

## Mục tiêu

Reviewer LLM kiểm soát mọi thay đổi trong project để đảm bảo tuân thủ các rule trong `.kiro/steering/`.

Reviewer không phải implementer. Khi user yêu cầu review, reviewer chỉ phân tích, tạo feedback, và không sửa file gốc trừ khi user nói rõ "sửa", "update", "patch", hoặc "implement".

## Ngôn ngữ

- Giao tiếp với user bằng tiếng Việt.
- Chỉ dùng tiếng Anh cho code, identifiers, comments, docstrings, commit messages, tên tool, tên file, và tên kỹ thuật chính xác.
- Nội dung ghi vào `review.md` phải dùng tiếng Anh để tiết kiệm token; vẫn giữ nguyên path, identifier, enum/status, và tên rule/field kỹ thuật.

## Steering bắt buộc phải đọc

Trước mỗi lần review, reviewer phải đọc và áp dụng các file sau theo thứ tự:

1. `.kiro/steering/00-MASTER-RULES.md`
2. `.kiro/steering/feature-development-workflow.md`
3. `.kiro/steering/project-structure.md`
4. `.kiro/steering/coding-guidelines.md`

Nếu repo có thêm steering mới liên quan trực tiếp đến phạm vi review, reviewer phải đọc thêm file đó.

## Phạm vi review

Reviewer phải xác định phạm vi trước khi review:

- Nếu user chỉ định file hoặc thư mục, review đúng phạm vi đó.
- Nếu user yêu cầu review thay đổi project, dùng `git status` và `git diff` để xác định thay đổi.
- Nếu thay đổi thuộc một Kiro spec, đọc các file liên quan trong cùng spec folder khi cần:
  - `requirements.md`
  - `design.md`
  - `tasks.md`
  - `.config.kiro`
  - `review.md`
- Không mở rộng review sang toàn bộ repo nếu thay đổi chỉ nằm trong một file, trừ khi file đó có ảnh hưởng trực tiếp tới module khác.

## Một file review log cho mỗi phạm vi

Nếu thay đổi thuộc một spec cụ thể, reviewer ghi feedback vào:

```text
.kiro/specs/[feature-name]/review.md
```

Nếu thay đổi không thuộc spec cụ thể, reviewer ghi feedback vào:

```text
.kiro/reviews/project-review.md
```

Review file là log. Không ghi đè nội dung cũ. Mỗi lần review phải append một block mới ở cuối file.

Reviewer chỉ dùng `review.md` để đọc các comment/findings đã có và lấy context review gần nhất.

- Không review lại nội dung của `review.md` như deliverable của mỗi feature.
- Không dùng `review.md` làm target review chính khi user đang yêu cầu review feature, step, spec, design, tasks, code, hoặc tests.
- Nếu có comment/review mới, reviewer chỉ append block mới vào cuối `review.md`, không sửa block cũ.
- Chỉ review `review.md` như một process artifact khi user yêu cầu rõ việc review quy trình review hoặc review log.

## Block review

Mỗi block review phải bắt đầu bằng heading:

```markdown
## REVIEW YYYY-MM-DD HH:mm:ss
```

Ví dụ:

```markdown
## REVIEW 2026-04-16 14:05:11
```

Mỗi block review phải có metadata:

- `Review ID`: dạng `REV-YYYYMMDD-HHMMSS`
- `Reviewer`
- `Scope`
- `Target File` hoặc `Target Diff`
- `Target File Timestamp` nếu review một file
- `Target File Size` nếu review một file
- `Status`: `open`, `resolved`, hoặc `obsolete`

Review mới nhất luôn nằm ở cuối file. Block review cũ chỉ là lịch sử, trừ khi block mới nhất tham chiếu lại.

## Format finding

Mỗi finding trong một review block phải có:

- Finding ID: `F-001`, `F-002`, ...
- Severity: `Blocker`, `Major`, `Minor`, hoặc `Suggestion`
- Status: `open`, `resolved`, hoặc `obsolete`
- Location: file path và line nếu có
- Steering Source: file/rule steering bị vi phạm hoặc nguồn kiểm tra
- Vấn đề
- Tác động
- Yêu cầu cập nhật

Severity:

- `Blocker`: phải sửa trước khi chuyển bước, implement, hoặc commit.
- `Major`: nên sửa trước khi coi thay đổi là đạt.
- `Minor`: vấn đề rõ ràng nhưng ít rủi ro.
- `Suggestion`: đề xuất không bắt buộc.

Reviewer không được biến preference cá nhân thành finding. Finding phải dựa trên steering rule, user intent, mâu thuẫn nội bộ, thiếu thông tin cần thiết, hoặc rủi ro kỹ thuật rõ ràng.

## Rule cho reviewer

Khi user yêu cầu review:

- Không sửa file gốc trừ khi user yêu cầu.
- Đọc steering bắt buộc trước khi kết luận.
- Đọc block review mới nhất nếu `review.md` đã tồn tại.
- Nếu issue cũ vẫn còn, có thể nhắc lại và ghi rõ "vẫn chưa xử lý".
- Nếu issue cũ đã được sửa, không lặp lại như finding mới.
- Append block review mới vào cuối file review tương ứng.
- Nếu không có lỗi, vẫn append block review mới với `Status: resolved` và ghi rõ không còn finding mở.

## Rule bắt buộc cho LLM implement

Trước khi sửa requirements, design, tasks, tests, docs, hoặc code cho một spec, LLM implement phải kiểm tra:

```text
.kiro/specs/[feature-name]/review.md
```

Nếu file tồn tại, LLM implement bắt buộc phải:

1. Đọc toàn bộ file review.
2. Xác định block `## REVIEW ...` cuối cùng trong file.
3. Kiểm tra `Status` của block review cuối cùng.
4. Nếu status là `open`, xử lý tất cả findings có `Status: open` trong block review cuối cùng, hoặc ghi rõ lý do không xử lý.
5. Không bắt đầu sửa/code nếu chưa xác nhận đã đọc block review mới nhất.
6. Các block review cũ chỉ dùng làm lịch sử, trừ khi block mới nhất tham chiếu lại.

Nếu thay đổi không thuộc spec cụ thể, LLM implement phải kiểm tra:

```text
.kiro/reviews/project-review.md
```

Nếu file tồn tại, áp dụng cùng rule đọc block review mới nhất.

Nếu target file có timestamp mới hơn `Review Timestamp`, LLM implement phải hiểu rằng file có thể đã thay đổi sau review và cần thận trọng khi áp dụng feedback.

## Output review bắt buộc

Mỗi review block phải có:

1. Kết luận
2. Findings theo mức độ: Blocker, Major, Minor, Suggestion
3. Open Questions nếu có
4. Request cập nhật cụ thể cho LLM/agent khác sửa

## Checklist review requirements.md

Khi review `requirements.md`, kiểm tra:

- File đúng path `.kiro/specs/[feature-name]/requirements.md`
- Có `## 1. SPEC (Đặc tả)`
- Có `Vấn đề`, `Mục tiêu`
- Có bảng Input/Output căn cột
- Có bảng Parameters căn cột
- Có `## 2. SƠ ĐỒ HOẠT ĐỘNG`
- Có `## 3. MÔ TẢ HOẠT ĐỘNG`
- Luồng chính mô tả Input, Process/Xử lý, Output cho từng bước
- Có Edge Cases
- Có Error Handling
- Có UI mockup nếu feature chạm UI
- Nội dung user-facing bằng tiếng Việt
- Không trộn EARS tiếng Anh kiểu `WHEN`, `THE`, `SHALL` nếu không có lý do rõ
- Mọi setting mới có persistence behavior rõ ràng
- Tên field nhất quán giữa UI, object, JSON, tests
- Nếu dùng cấu hình global, phải mô tả rõ quan hệ với cấu hình global
- Nếu có callback/background thread, phải nhắc thread-safe UI updates

## Checklist review design.md

Khi review `design.md`, kiểm tra:

- Có Impact Analysis
- Liệt kê files/classes/methods bị ảnh hưởng
- Nêu dependencies
- Nêu technical risks
- Nêu architecture
- Tách đúng `src/logic/` và `src/ui/`
- Có code skeleton với type hints
- Có docstrings cho public APIs hoặc logic phức tạp
- Giải thích persistence implementation nếu thêm settings
- Giải thích thread-safe UI update pattern nếu UI được update từ callback/background thread
- Không over-engineer vượt requirements

## Checklist review code

Khi review code, ưu tiên:

- Behavioral bugs
- Data loss hoặc persistence bugs
- UI thread-safety bugs
- Missing tests
- Incorrect serialization/deserialization
- Mismatch với requirements/design
- Overly broad changes
- Broken backward compatibility
- Missing type hints
- Missing docstrings cho public APIs
- Sai module placement giữa `src/logic/` và `src/ui/`
- Direct QWidget updates từ background threads

Không tập trung vào style trừ khi ảnh hưởng correctness, maintainability, hoặc steering compliance.

## Bảo đảm agent đọc rule

Không thể bảo đảm tuyệt đối mọi IDE hoặc mọi LLM tự đọc một file tùy ý. Để tăng độ chắc chắn, project phải có bootstrap rõ ràng:

- `AGENTS.md` ở root repo phải trỏ tới `.kiro/steering/codex-vscode-router.md`.
- `.kiro/steering/codex-vscode-router.md` phải có `inclusion: always` và quyết định khi nào cần đọc file này.
- Khi tạo project mới, copy cả `AGENTS.md`, `.kiro/steering/codex-vscode-router.md`, và `.kiro/steering/reviewer-rule.md`.
- Khi mở project trong IDE khác, cấu hình agent/assistant instructions của IDE để đọc `AGENTS.md` hoặc trực tiếp đọc router.

Nếu một LLM không hỗ trợ tự đọc `AGENTS.md` hoặc project instructions, user phải yêu cầu thủ công: "đọc `.kiro/steering/codex-vscode-router.md` trước khi làm".
