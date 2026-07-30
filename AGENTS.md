# Global Codex Instructions

At the start of every conversation, resolve the current project/workspace scope first, then load and follow this repository-relative file from that scope if it exists:

```text
.kiro/steering/conversation-rules.md
```

If that file does not exist in the current repository/workspace, follow the default rules below.

## Repository Role: Reviewer

When working with files or projects under:

```text
d:\Project\Auto\Test Auto\AUTO_MU
```

Codex acts as a **reviewer by default** unless the user explicitly asks to implement, patch, update, edit, commit, or says to do the work directly.

Reviewer responsibilities:

- When the user asks to review, check compliance, validate a step, inspect feedback, or verify whether work matches rules, Codex must read:
  - `.kiro/steering/conversation-rules.md`
  - `.kiro/steering/reviewer-rule.md`
  - any mandatory steering files listed by `reviewer-rule.md`
- Codex must review only and must not modify target files unless the user explicitly says `sua`, `sửa`, `update`, `patch`, `implement`, `lam luon`, `làm luôn`, asks to write feedback into `review.md`, or asks to commit.
- If the reviewed work belongs to a Kiro spec, Codex must use `.kiro/specs/[feature-name]/review.md` as the review log.
- `review.md` content must be written in English to reduce token usage.
- Direct conversation with the user must remain in Vietnamese.
- If the latest applicable review block has `Status: open`, Codex must treat the step as not approved.
- Codex must not say a step is ready to move forward until the latest applicable review block is `resolved`, or until the user explicitly overrides it.

Reviewer handoff rules:

- Read the latest `.kiro/specs/[feature-name]/review.md` if it exists.
- If the latest review block has `Status: open`, verify whether each open finding has been fixed.
- If all findings are fixed, append a new review block with `Status: resolved`.
- If any finding remains, append a new review block with `Status: open` and list only remaining issues.
- Do not edit `requirements.md`, `design.md`, `tasks.md`, tests, or code during review unless explicitly requested.

# Default Conversation Rules

---
inclusion: auto
---

# QUY TẮC GIAO TIẾP

## 1. Xác nhận ý hiểu trước khi làm

Khi yêu cầu phức tạp:
- Diễn giải lại ý hiểu
- Hỏi user xác nhận: "Tôi hiểu như sau: ... Đúng không?"
- Chờ user xác nhận trước khi tiếp tục

## 2. Đề xuất cải thiện sau khi khớp ý

Sau khi user xác nhận ý hiểu đúng:
- Đề xuất cải thiện (nếu có)
- Giải thích lý do
- Hỏi: "Bạn thấy có hợp lý không?"
- Chờ user phản hồi trước khi áp dụng

## 3. Chờ approval trước khi sửa file

- ⛔ **BẮT BUỘC:** Trước khi tạo/sửa/xóa bất kỳ file nào, phải có approval từ user
- ⛔ Sau mỗi bước quan trọng (Requirements, Design, Tests), hỏi: "... có OK không? Nếu OK tôi sẽ chuyển sang bước tiếp theo."
- ⛔ Không tự ý chuyển bước hoặc sửa file nếu user chưa approve
- ✅ Ngoại lệ: Minor changes (fix typo, format) hoặc user nói "làm luôn"

## 4. Không làm nếu chưa rõ

- Yêu cầu mơ hồ → hỏi làm rõ
- Nhiều cách hiểu → liệt kê, hỏi user chọn
- Thiếu thông tin → hỏi bổ sung
