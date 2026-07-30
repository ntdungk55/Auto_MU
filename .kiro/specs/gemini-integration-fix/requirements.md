# Gemini Integration Fix - Requirements

## Introduction

The Gemini integration for READ_PASSIVE actions is not responding when enabled. Users can configure OCR and enable Gemini, but Gemini processing does not execute or produce output. This spec defines the requirements to fix the Gemini integration flow.

## Glossary

- **Gemini**: Google's generative AI model (gemini-1.5-flash)
- **OCR**: Optical Character Recognition - extracts text from images
- **Prompt**: User-configured template for Gemini input (can include {text} placeholder)
- **API Key**: GEMINI_API_KEY environment variable or saved in app_state.json
- **READ_PASSIVE**: Action type that continuously reads and processes frames
- **Builder Pattern**: Configuration pattern where options are set incrementally

## Requirements

### Requirement 1: Gemini Configuration Validation

**User Story:** As a user, I want to know if my Gemini configuration is valid before processing starts, so that I can fix issues early.

#### Acceptance Criteria

1. WHEN Gemini is enabled but no API key is configured, THE system SHALL log a clear error message
2. WHEN Gemini is enabled but no prompt is configured, THE system SHALL log a clear error message
3. WHEN Gemini is enabled with valid API key and prompt, THE system SHALL attempt to process OCR text
4. WHEN Gemini API key is missing from environment and app_state, THE system SHALL not attempt Gemini processing

### Requirement 2: Prompt Configuration Persistence

**User Story:** As a user, I want my Gemini prompt to be saved and loaded correctly, so that I don't have to reconfigure it each time.

#### Acceptance Criteria

1. WHEN I set a Gemini prompt in the dialog, THE prompt SHALL be saved to action.prompt
2. WHEN I load an action with a saved prompt, THE prompt SHALL be displayed in the dialog
3. WHEN I save an action with Gemini enabled, THE prompt SHALL be included in the saved action
4. WHEN I load an action with Gemini enabled, THE prompt SHALL be available for processing

### Requirement 3: Gemini Processing Flow

**User Story:** As a user, I want Gemini to process OCR text when enabled, so that I can extract structured data from images.

#### Acceptance Criteria

1. WHEN OCR text is available and Gemini is enabled, THE system SHALL send the text to Gemini with the configured prompt
2. WHEN Gemini processes successfully, THE system SHALL log the result with clear formatting
3. WHEN Gemini times out, THE system SHALL log a timeout error and continue processing
4. WHEN Gemini returns an error, THE system SHALL log the error message and continue processing
5. WHEN Gemini is disabled, THE system SHALL skip Gemini processing and use OCR text only

### Requirement 4: Gemini Timeout Handling

**User Story:** As a user, I want Gemini processing to have a reasonable timeout, so that the system doesn't hang indefinitely.

#### Acceptance Criteria

1. WHEN Gemini processing exceeds the configured timeout, THE system SHALL cancel the request
2. WHEN Gemini timeout occurs, THE system SHALL log the timeout duration
3. THE default Gemini timeout SHALL be 10 seconds (configurable per action)
4. WHEN overall passive read timeout is shorter than Gemini timeout, THE Gemini timeout SHALL be capped to overall timeout

### Requirement 5: Gemini Logging and Debugging

**User Story:** As a developer, I want detailed logging of Gemini processing, so that I can debug issues.

#### Acceptance Criteria

1. WHEN Gemini is enabled, THE system SHALL log "Gemini enabled, processing..."
2. WHEN Gemini API key is checked, THE system SHALL log whether key is present
3. WHEN Gemini prompt is checked, THE system SHALL log whether prompt is configured
4. WHEN Gemini model is initialized, THE system SHALL log the model name
5. WHEN Gemini processing completes, THE system SHALL log result length and content
6. WHEN Gemini processing fails, THE system SHALL log the error with full details

### Requirement 6: Builder Pattern for Gemini Configuration

**User Story:** As a developer, I want Gemini configuration to follow a builder pattern, so that options can be set incrementally and independently.

#### Acceptance Criteria

1. THE Gemini configuration SHALL support independent options: enabled, prompt, timeout, model
2. WHEN any Gemini option is changed, THE other options SHALL remain unaffected
3. WHEN Gemini is disabled, THE other Gemini options SHALL be preserved but not used
4. WHEN Gemini is re-enabled, THE previously configured options SHALL be available

## Implementation Notes

- Gemini integration should be optional and graceful - if Gemini fails, OCR text should still be available
- All Gemini operations should be logged for debugging
- Gemini timeout should be configurable per action
- Gemini prompt should support {text} placeholder for OCR text substitution
- Gemini API key should be loaded from environment or app_state.json (DPAPI-protected)
