# Requirements Document

## Introduction

Tính năng phát hiện thao tác người dùng khi tool đang chạy, cho phép tự động dừng hoặc tạm dừng tool khi người dùng can thiệp bằng chuột/bàn phím. Điều này giúp người dùng có thể "chen ngang" khi cần thiết mà không phải manually stop tool.

## Glossary

- **User_Input_Detector**: Module phát hiện thao tác chuột/bàn phím từ người dùng (không phải từ tool)
- **Tool_Runner**: Engine chạy tool automation
- **Mouse_Controller**: Module điều khiển chuột của tool
- **dwExtraInfo**: Trường metadata trong Windows input event, dùng để đánh dấu event từ tool
- **User_Input_Mode**: Chế độ xử lý khi phát hiện thao tác người dùng

## Requirements

### Requirement 1: Phân biệt thao tác người dùng vs tool

**User Story:** Là một hệ thống automation, tôi muốn phân biệt được thao tác chuột/bàn phím từ người dùng và từ tool, để có thể phản ứng phù hợp khi người dùng can thiệp.

#### Acceptance Criteria

1. WHEN the Mouse_Controller sends a click event, THE System SHALL mark the event with a unique dwExtraInfo value (0xAUT0)
2. WHEN the Mouse_Controller sends a mouse move event, THE System SHALL mark the event with the same dwExtraInfo value
3. WHEN a keyboard event is sent by the tool, THE System SHALL mark the event with the unique dwExtraInfo value
4. WHEN the User_Input_Detector receives an input event, THE System SHALL check the dwExtraInfo field to determine the source
5. IF the dwExtraInfo matches the tool's marker, THEN THE User_Input_Detector SHALL ignore the event
6. IF the dwExtraInfo does not match the tool's marker, THEN THE User_Input_Detector SHALL treat it as user input

### Requirement 2: Hook global input events

**User Story:** Là một hệ thống, tôi muốn hook được các sự kiện chuột/bàn phím toàn cục, để phát hiện khi người dùng thao tác.

#### Acceptance Criteria

1. WHEN the Tool_Runner starts, THE User_Input_Detector SHALL start listening for global mouse events
2. WHEN the Tool_Runner starts, THE User_Input_Detector SHALL start listening for global keyboard events
3. WHEN the Tool_Runner stops, THE User_Input_Detector SHALL stop listening for input events
4. THE User_Input_Detector SHALL run on a separate thread to avoid blocking the main UI
5. WHEN a user mouse click is detected, THE User_Input_Detector SHALL emit a signal to the Tool_Runner
6. WHEN a user keyboard press is detected, THE User_Input_Detector SHALL emit a signal to the Tool_Runner

### Requirement 3: Tool settings cho User Input Mode

**User Story:** Là một người dùng, tôi muốn cấu hình cách tool phản ứng khi tôi thao tác chuột/bàn phím, để có thể tùy chỉnh theo nhu cầu sử dụng.

#### Acceptance Criteria

1. THE Tool_Settings_Dialog SHALL display a "User Input Mode" section
2. THE User_Input_Mode section SHALL provide three options:
   - "Vẫn chạy" (Ignore): Tool tiếp tục chạy bình thường (DEFAULT)
   - "Tạm dừng X giây" (Pause): Tool tạm dừng X giây sau khi phát hiện user input
   - "Dừng hẳn" (Stop): Tool dừng hoàn toàn khi phát hiện user input
3. THE default User_Input_Mode SHALL be "Vẫn chạy" (Ignore)
3. THE default User_Input_Mode SHALL be "Vẫn chạy" (Ignore)
4. WHEN "Tạm dừng X giây" is selected, THE System SHALL display a number input for pause duration (default: 5 seconds)
5. THE pause duration input SHALL accept values from 1 to 300 seconds
6. THE User_Input_Mode setting SHALL be saved per-tool (not per-action)
7. WHEN the tool is saved, THE User_Input_Mode settings SHALL persist to JSON

### Requirement 4: Xử lý khi phát hiện user input

**User Story:** Là một tool runner, tôi muốn xử lý đúng khi phát hiện user input, để đảm bảo trải nghiệm người dùng mượt mà.

#### Acceptance Criteria

1. WHEN user input is detected AND mode is "Ignore", THE Tool_Runner SHALL continue running normally
2. WHEN user input is detected AND mode is "Pause", THE Tool_Runner SHALL:
   - Pause the current action execution
   - Wait for the configured pause duration
   - Resume execution after the pause
3. WHEN user input is detected AND mode is "Stop", THE Tool_Runner SHALL stop completely
4. WHEN the tool is paused due to user input, THE System SHALL display a status message in the log
5. WHEN the tool resumes after pause, THE System SHALL display a status message in the log
6. WHILE the tool is paused, THE System SHALL show "Paused (user input)" status in the running table

### Requirement 5: Chỉ detect input trong target window

**User Story:** Là một người dùng, tôi muốn tool chỉ phản ứng khi tôi thao tác trong cửa sổ game, để tôi có thể làm việc khác mà không ảnh hưởng tool.

#### Acceptance Criteria

1. WHEN user input is detected, THE System SHALL check if the input is within the target window
2. IF the input is outside the target window, THEN THE System SHALL ignore it
3. IF the input is inside the target window, THEN THE System SHALL process it according to User_Input_Mode
4. THE System SHALL use the target window's client area to determine input boundaries

### Requirement 6: Performance và stability

**User Story:** Là một hệ thống, tôi muốn đảm bảo việc hook input không ảnh hưởng performance, để tool chạy mượt mà.

#### Acceptance Criteria

1. THE User_Input_Detector SHALL NOT cause noticeable lag in mouse/keyboard response
2. THE User_Input_Detector SHALL handle exceptions gracefully without crashing
3. WHEN the application closes, THE User_Input_Detector SHALL properly unhook all listeners
4. THE User_Input_Detector SHALL use minimal CPU resources when idle
