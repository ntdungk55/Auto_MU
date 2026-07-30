# Requirements Document: Responsive Layout cho Multi-Image Algorithm Testing Dialog

## Introduction

Cải thiện responsive layout của Multi-Image Algorithm Testing Dialog để chỉ Window Capture preview area được dãn ra khi user resize dialog, các components khác giữ nguyên kích thước.

## Glossary

- **Dialog**: Multi-Image Algorithm Testing Dialog
- **Window_Capture_Preview**: Vùng hiển thị ảnh window capture được chọn (bên phải)
- **Teaching_Image_Preview**: Vùng hiển thị teaching image (bên trái, kích thước cố định)
- **Responsive_Layout**: Layout tự động điều chỉnh khi resize window

## Requirements

### Requirement 1: Responsive Window Capture Preview

**User Story:** Là người dùng, tôi muốn chỉ có Window Capture preview được dãn ra khi resize dialog, để tôi có thể xem ảnh lớn hơn mà không làm rối layout.

#### Acceptance Criteria

1. WHEN user resize dialog window, THE Window_Capture_Preview SHALL tự động điều chỉnh kích thước theo dialog
2. THE Teaching_Image_Preview SHALL giữ nguyên kích thước cố định (max 400px width)
3. THE Window_Captures_List SHALL giữ nguyên height cố định
4. THE Algorithm_Controls SHALL giữ nguyên kích thước cố định
5. THE Bottom_Buttons SHALL giữ nguyên kích thước cố định

### Requirement 2: Layout Stability

**User Story:** Là người dùng, tôi muốn các controls không bị dãn ra khi resize, để interface luôn gọn gàng và dễ sử dụng.

#### Acceptance Criteria

1. THE Buttons SHALL có fixed width, không stretch theo dialog width
2. THE ComboBoxes SHALL có minimum width, không stretch quá mức
3. THE Lists SHALL có fixed/maximum height, không stretch theo dialog height
4. THE Labels và Text SHALL giữ nguyên kích thước font và padding