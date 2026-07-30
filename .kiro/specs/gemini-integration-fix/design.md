# Gemini Integration Fix - Design

## Overview

The Gemini integration for READ_PASSIVE actions needs to be fixed to ensure proper configuration validation, prompt persistence, and processing flow. The design follows a builder pattern where Gemini options are configured independently and can be enabled/disabled without affecting other settings.

## Architecture

### Gemini Configuration Flow

```
User configures Gemini in UI
    ↓
Dialog saves: gemini_enabled, prompt, timeout, model
    ↓
Action stores configuration
    ↓
During READ_PASSIVE execution:
    - Check if gemini_enabled = True
    - Validate API key exists
    - Validate prompt is configured
    - Send OCR text to Gemini with prompt
    - Log result or error
    - Continue processing
```

### Components and Interfaces

#### 1. ActionConfigDialog (UI Layer)

**Responsibilities:**
- Display Gemini configuration options
- Save/load Gemini settings from action
- Validate Gemini configuration before saving
- Show Gemini key status

**Key Methods:**
- `on_gemini_changed(state)`: Show/hide Gemini controls based on checkbox
- `_open_gemini_key_dialog()`: Configure API key
- `_open_prompt_dialog()`: Configure prompt template
- `_refresh_gemini_key_status()`: Check if API key is available
- `get_action()`: Save Gemini settings to action

**Gemini UI Elements:**
- `gemini_checkbox`: Enable/disable Gemini
- `gemini_timeout_spin`: Timeout in seconds (1-120)
- `gemini_prompt_btn`: Open prompt editor
- `gemini_key_btn`: Configure API key
- `gemini_key_status`: Show key status
- `notification_checkbox`: Enable Telegram notifications

#### 2. SystemExecutor (Execution Layer)

**Responsibilities:**
- Execute Gemini processing during READ_PASSIVE
- Validate Gemini configuration
- Handle Gemini API calls with timeout
- Log Gemini processing results

**Key Methods:**
- `_gemini_extract_from_ocr(ocr_text, action, overall_timeout_s)`: Main Gemini processing
- `_get_gemini_model(model_name)`: Lazy-load Gemini model with caching
- `_run_passive_read(action, timeout)`: Main passive read loop that calls Gemini

**Gemini Processing Flow:**
1. Check if `gemini_enabled = True`
2. Validate API key from environment or app_state
3. Validate prompt is configured
4. Build prompt by replacing {text} with OCR text
5. Add ISO timestamp to prompt
6. Call Gemini with timeout
7. Log result or error
8. Return Gemini output or None

#### 3. AutoAction (Data Model)

**Gemini Fields:**
- `gemini_enabled: bool` - Enable/disable Gemini processing
- `prompt: str` - Gemini prompt template (supports {text} placeholder)
- `gemini_prompt: str` - Alias for prompt (for backward compatibility)
- `gemini_timeout: float` - Timeout in seconds (default 10.0)
- `gemini_model: str` - Model name (default "gemini-1.5-flash")

## Data Models

### Gemini Configuration in AutoAction

```python
@dataclass
class AutoAction:
    # ... other fields ...
    
    # Gemini post-processing for read_data:
    gemini_enabled: bool = False
    prompt: str = ""
    gemini_prompt: str = ""  # Alias for backward compatibility
    gemini_timeout: float = 10.0  # seconds
    gemini_model: str = "gemini-1.5-flash"  # Optional, can be overridden by env
    
    # Telegram notification (independent of Gemini)
    notification_enabled: bool = False
```

### Gemini Processing Result

```python
{
    "text": "Gemini output text",
    "error": None,
    "timeout": False,
    "duration": 2.5  # seconds
}
```

## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property 1: Gemini Configuration Validation

**For any** READ_PASSIVE action with Gemini enabled, if API key is missing, the system SHALL log an error and skip Gemini processing.

**Validates: Requirements 1.1, 1.4**

### Property 2: Prompt Persistence

**For any** READ_PASSIVE action with a configured prompt, saving and loading the action SHALL preserve the prompt text exactly.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4**

### Property 3: Gemini Processing Flow

**For any** OCR text and valid Gemini configuration, the system SHALL attempt to send the text to Gemini and log the result (success or error).

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

### Property 4: Timeout Enforcement

**For any** Gemini processing request with a configured timeout, if processing exceeds the timeout, the system SHALL cancel the request and log a timeout error.

**Validates: Requirements 4.1, 4.2, 4.3, 4.4**

### Property 5: Logging Completeness

**For any** Gemini processing operation, the system SHALL log at least: operation start, configuration validation, result or error, and operation duration.

**Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

### Property 6: Builder Pattern Independence

**For any** Gemini configuration, changing one option (enabled, prompt, timeout, model) SHALL not affect other options.

**Validates: Requirements 6.1, 6.2, 6.3, 6.4**

## Error Handling

### Gemini API Key Missing
- **Log**: "Chưa có GEMINI_API_KEY (hãy lưu key trong app hoặc set env)."
- **Action**: Skip Gemini processing, use OCR text only
- **Continue**: Yes, processing continues with OCR text

### Gemini Prompt Missing
- **Log**: "Bạn chưa cấu hình prompt cho Gemini."
- **Action**: Skip Gemini processing, use OCR text only
- **Continue**: Yes, processing continues with OCR text

### Gemini Model Initialization Failed
- **Log**: "Không khởi tạo được model: {model_name}"
- **Action**: Skip Gemini processing, use OCR text only
- **Continue**: Yes, processing continues with OCR text

### Gemini Processing Timeout
- **Log**: "Timeout sau {timeout}s"
- **Action**: Cancel Gemini request, use OCR text only
- **Continue**: Yes, processing continues with OCR text

### Gemini API Error
- **Log**: "Lỗi: {error_message}"
- **Action**: Skip Gemini processing, use OCR text only
- **Continue**: Yes, processing continues with OCR text

## Testing Strategy

### Unit Tests

1. **Gemini Configuration Validation**
   - Test API key detection from environment
   - Test API key detection from app_state
   - Test prompt validation
   - Test model name resolution

2. **Prompt Persistence**
   - Test saving prompt to action
   - Test loading prompt from action
   - Test prompt with {text} placeholder
   - Test prompt with special characters

3. **Timeout Handling**
   - Test timeout enforcement
   - Test timeout logging
   - Test timeout with various durations

4. **Error Handling**
   - Test missing API key error
   - Test missing prompt error
   - Test model initialization error
   - Test API error handling

### Property-Based Tests

1. **Configuration Independence** (Property 6)
   - Generate random Gemini configurations
   - Verify changing one option doesn't affect others
   - Verify disabled Gemini preserves options

2. **Prompt Persistence** (Property 2)
   - Generate random prompts with various characters
   - Save and load actions
   - Verify prompt text matches exactly

3. **Timeout Enforcement** (Property 4)
   - Generate random timeout values
   - Verify timeout is enforced
   - Verify timeout is logged

## Implementation Notes

- Gemini integration should be optional and graceful
- All Gemini operations should be logged for debugging
- Gemini timeout should be configurable per action
- Gemini prompt should support {text} placeholder
- Gemini API key should be loaded from environment or app_state.json
- Gemini model should be cacheable to avoid repeated initialization
- Gemini processing should run in a separate thread with timeout
- If Gemini fails, OCR text should still be available
