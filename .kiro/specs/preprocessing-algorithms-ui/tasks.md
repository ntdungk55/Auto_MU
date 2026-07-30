# Implementation Plan: Preprocessing Algorithms UI

## Overview

Triển khai feature cho phép user cấu hình preprocessing algorithms cho template matching và OCR thông qua settings dialogs với ListView read-only và integration với Multi-Image Algorithm Testing Dialog.

## Tasks

- [x] 1. Extend AutoAction data model with new algorithm fields
  - Add `template_matching_algorithms: list[dict] = field(default_factory=list)` to AutoAction
  - Add `ocr_algorithms: list[dict] = field(default_factory=list)` to AutoAction
  - _Requirements: 5.1, 5.2_

- [x] 1.1 Write unit tests for AutoAction extensions
  - Test default values for new fields
  - Test field types and structure
  - _Requirements: 5.1, 5.2_

- [x] 2. Implement algorithm display formatting utilities
  - Create `format_algorithm_display(algorithm: dict) -> str` function
  - Create `update_algorithms_display(list_widget: QListWidget, algorithms: list[dict])` function
  - Handle empty algorithms list case
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 2.1 Write unit tests for algorithm display formatting
  - Test formatting with parameters: "Algorithm_Name (param1: value1, param2: value2)"
  - Test formatting without parameters: "Algorithm_Name"
  - Test empty algorithms list: "Không có thuật toán"
  - _Requirements: 3.1, 3.2, 3.3_

- [x] 3. Extend ImageDetectSettingsDialog with Template Matching Preprocessing section
  - Add `_add_template_matching_preprocessing_section()` method
  - Create Template Matching Preprocessing GroupBox
  - Add read-only ListView for template algorithms
  - Add "⚙️ Cấu hình Template Matching Algorithms" button
  - Position section after Teaching Image section
  - _Requirements: 1.1, 1.2, 1.3, 7.1_

- [x] 3.1 Implement template matching configuration dialog integration
  - Add `_open_template_matching_config()` method
  - Open Multi-Image Algorithm Testing Dialog
  - Pass current template_matching_algorithms to dialog
  - _Requirements: 1.4_

- [x] 3.2 Implement template algorithms display update
  - Add `_update_template_algorithms_display()` method
  - Load template_matching_algorithms from action
  - Update ListView using display formatting utilities
  - Call from `_load_settings()` method
  - _Requirements: 1.2, 1.5_

- [x] 3.3 Write unit tests for ImageDetectSettingsDialog extensions
  - Test Template Matching Preprocessing section creation
  - Test ListView and button presence
  - Test algorithms display update
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 4. Extend PassiveReadSettingsDialog with OCR Preprocessing section
  - Add `_add_ocr_preprocessing_section()` method to left column
  - Create OCR Preprocessing GroupBox
  - Add read-only ListView for OCR algorithms
  - Add "⚙️ Cấu hình OCR Algorithms" button
  - Show only when mode = "Đọc dữ liệu"
  - _Requirements: 2.1, 2.2, 2.3, 7.2_

- [x] 4.1 Implement OCR configuration dialog integration
  - Add `_open_ocr_config()` method
  - Open Multi-Image Algorithm Testing Dialog
  - Pass current ocr_algorithms to dialog
  - _Requirements: 2.4_

- [x] 4.2 Implement OCR algorithms display update
  - Add `_update_ocr_algorithms_display()` method
  - Load ocr_algorithms from action
  - Update ListView using display formatting utilities
  - Call from `_load_settings()` and `_on_passive_mode_changed()`
  - _Requirements: 2.2, 2.5_

- [x] 4.3 Write unit tests for PassiveReadSettingsDialog extensions
  - Test OCR Preprocessing section creation
  - Test ListView and button presence
  - Test algorithms display update
  - Test visibility based on passive mode
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 5. Extend MultiImageAlgorithmTestingDialog with Apply buttons
  - Add `_add_apply_buttons()` method to UI initialization
  - Create "📤 Apply to Template Matching" button
  - Create "📤 Apply to OCR Mode" button
  - Position buttons in bottom area before OK/Close buttons
  - _Requirements: 4.1, 4.2_

- [x] 5.1 Implement Apply to Template Matching functionality
  - Add `_apply_to_template_matching()` method
  - Get current algorithms from algorithms_list
  - Save to action.template_matching_algorithms
  - Show success message with algorithm count
  - _Requirements: 4.3_

- [x] 5.2 Implement Apply to OCR Mode functionality
  - Add `_apply_to_ocr_mode()` method
  - Get current algorithms from algorithms_list
  - Save to action.ocr_algorithms
  - Show success message with algorithm count
  - _Requirements: 4.4_

- [x] 5.3 Implement get current algorithms helper
  - Add `_get_current_algorithms()` method
  - Extract algorithms from algorithms_list widget
  - Include algorithm data with parameters
  - Validate algorithm structure before return
  - _Requirements: 4.3, 4.4_

- [x] 5.4 Write unit tests for MultiImageAlgorithmTestingDialog extensions
  - Test Apply buttons creation
  - Test Apply to Template Matching functionality
  - Test Apply to OCR Mode functionality
  - Test algorithm extraction and validation
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6. Update ToolManager for data persistence
  - Add template_matching_algorithms to `_action_to_dict()` method
  - Add ocr_algorithms to `_action_to_dict()` method
  - Add template_matching_algorithms to `from_dict()` method
  - Add ocr_algorithms to `from_dict()` method
  - Handle missing fields for backward compatibility
  - _Requirements: 5.3, 5.4_

- [x] 6.1 Write unit tests for ToolManager persistence
  - Test template_matching_algorithms serialization/deserialization
  - Test ocr_algorithms serialization/deserialization
  - Test backward compatibility with missing fields
  - Test data integrity after save/load cycle
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 7. Implement algorithm validation utilities
  - Create `validate_algorithm(algorithm: dict) -> tuple[bool, str]` function
  - Create `validate_algorithms_list(algorithms: list[dict]) -> tuple[bool, str]` function
  - Validate required fields: id, name, config
  - Validate parameters structure if present
  - _Requirements: 6.4, 6.5_

- [x] 7.1 Write unit tests for algorithm validation
  - Test valid algorithm structure
  - Test missing required fields
  - Test invalid parameters structure
  - Test algorithms list validation
  - _Requirements: 6.4, 6.5_

- [x] 8. Update settings dialogs get_settings() methods
  - Add template_matching_algorithms to ImageDetectSettingsDialog.get_settings()
  - Add ocr_algorithms to PassiveReadSettingsDialog.get_settings()
  - Ensure algorithms are included in returned settings dict
  - _Requirements: 5.1, 5.2_

- [x] 8.1 Write integration tests for settings persistence
  - Test template matching algorithms save/load in Image Detect dialog
  - Test OCR algorithms save/load in Passive Read dialog
  - Test data persistence across dialog open/close cycles
  - _Requirements: 5.1, 5.2, 5.5_

- [x] 9. Checkpoint - Ensure all tests pass
  - Run all unit tests and verify they pass
  - Test basic functionality manually
  - Verify no regressions in existing features
  - Ask user if questions arise

- [x] 10. Final integration and UI polish
  - Adjust ListView heights and scroll behavior
  - Ensure proper GroupBox titles and icons
  - Test UI layout in different dialog sizes
  - Verify button styling consistency
  - _Requirements: 7.3, 7.4, 7.5_

- [x] 10.1 Write manual test execution
  - Execute Manual Test Case 1: Template Matching Algorithms Configuration
  - Execute Manual Test Case 2: OCR Algorithms Configuration
  - Document any issues found during manual testing
  - _Requirements: All requirements_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Run complete test suite
  - Verify all manual test cases pass
  - Confirm feature works end-to-end
  - Ask user if questions arise

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Unit tests validate specific functionality
- Manual tests validate end-to-end user workflows