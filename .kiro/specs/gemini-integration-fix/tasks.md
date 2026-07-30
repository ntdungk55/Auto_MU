# Gemini Integration Fix - Implementation Tasks

## Overview

Implementation plan for fixing the Gemini integration in READ_PASSIVE actions. Tasks are organized to fix the configuration flow, validation, and processing pipeline.

## Tasks

- [ ] 1. Fix Gemini Configuration Saving in ActionConfigDialog
  - [ ] 1.1 Ensure gemini_enabled checkbox state is properly saved to action
    - Add debug logging to track checkbox state
    - Verify checkbox state is read in get_action()
    - Test saving with Gemini enabled and disabled
    - _Requirements: 2.1, 2.3_

  - [ ] 1.2 Ensure prompt is properly saved from dialog to action
    - Verify _open_prompt_dialog saves to action.prompt
    - Verify _open_prompt_dialog saves to action.gemini_prompt
    - Add debug logging for prompt save/load
    - Test prompt persistence across save/load cycles
    - _Requirements: 2.1, 2.2, 2.3_

  - [ ] 1.3 Ensure gemini_timeout is properly saved
    - Verify timeout spinbox value is saved to action.gemini_timeout
    - Add validation for timeout range (1-120 seconds)
    - Add debug logging for timeout value
    - _Requirements: 4.3_

  - [ ] 1.4 Ensure gemini_model is properly saved (if configurable)
    - Add model selection UI if needed
    - Verify model name is saved to action.gemini_model
    - Add debug logging for model name
    - _Requirements: 6.1_

- [ ] 2. Fix Gemini Configuration Loading in ActionConfigDialog
  - [ ] 2.1 Load gemini_enabled checkbox state from action
    - Verify checkbox is checked/unchecked based on action.gemini_enabled
    - Add debug logging for loaded state
    - Test loading with various action types
    - _Requirements: 2.2, 2.4_

  - [ ] 2.2 Load prompt from action to dialog
    - Verify prompt is loaded from action.prompt or action.gemini_prompt
    - Display prompt in _open_prompt_dialog when opened
    - Add debug logging for loaded prompt
    - _Requirements: 2.2, 2.4_

  - [ ] 2.3 Load gemini_timeout from action
    - Verify timeout spinbox is set to action.gemini_timeout
    - Add debug logging for loaded timeout
    - _Requirements: 4.3_

  - [ ] 2.4 Load gemini_model from action (if configurable)
    - Verify model name is loaded from action.gemini_model
    - Add debug logging for loaded model
    - _Requirements: 6.1_

- [ ] 3. Fix Gemini Processing Validation in SystemExecutor
  - [ ] 3.1 Add comprehensive validation before Gemini processing
    - Check if gemini_enabled is True
    - Check if API key exists (environment or app_state)
    - Check if prompt is configured
    - Log each validation step with clear messages
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 5.1, 5.2, 5.3_

  - [ ] 3.2 Add debug logging for Gemini configuration
    - Log "Gemini enabled, processing..." when starting
    - Log API key status (present/missing)
    - Log prompt status (configured/missing)
    - Log model name being used
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ] 3.3 Fix Gemini model initialization
    - Verify _get_gemini_model returns valid model
    - Add error logging if model initialization fails
    - Verify model caching works correctly
    - _Requirements: 5.4_

  - [ ] 3.4 Fix Gemini API call with proper error handling
    - Verify genai.configure is called with API key
    - Verify generate_content is called with prompt
    - Add try/catch for API errors
    - Log error details if API call fails
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 5.5, 5.6_

- [ ] 4. Fix Gemini Timeout Handling
  - [ ] 4.1 Implement proper timeout enforcement
    - Use threading with timeout for Gemini calls
    - Verify timeout is enforced correctly
    - Log timeout duration when timeout occurs
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 4.2 Cap Gemini timeout to overall passive read timeout
    - If overall_timeout_s is shorter than gemini_timeout, use overall_timeout_s
    - Add debug logging for timeout capping
    - _Requirements: 4.4_

  - [ ] 4.3 Add timeout error logging
    - Log "Timeout sau {timeout}s" when timeout occurs
    - Continue processing with OCR text only
    - _Requirements: 4.1, 4.2_

- [ ] 5. Fix Gemini Result Logging
  - [ ] 5.1 Add comprehensive result logging
    - Log result length and content when successful
    - Log error message when failed
    - Log timeout message when timeout occurs
    - Format output with HTML for UI display
    - _Requirements: 3.2, 5.5, 5.6_

  - [ ] 5.2 Add Gemini result to cache
    - Store Gemini result in _passive_cache
    - Display cached result when frame is unchanged
    - _Requirements: 3.2_

  - [ ] 5.3 Add Gemini result to Telegram notification
    - Send Gemini result if available
    - Fall back to OCR text if Gemini unavailable
    - _Requirements: 3.2_

- [ ] 6. Implement Builder Pattern for Gemini Configuration
  - [ ] 6.1 Verify Gemini options are independent
    - Changing gemini_enabled should not affect other options
    - Changing prompt should not affect other options
    - Changing timeout should not affect other options
    - Changing model should not affect other options
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [ ] 6.2 Verify disabled Gemini preserves options
    - When Gemini is disabled, options should be preserved
    - When Gemini is re-enabled, options should be available
    - _Requirements: 6.3, 6.4_

  - [ ] 6.3 Add debug logging for builder pattern
    - Log each option change
    - Log option values when Gemini is enabled
    - _Requirements: 6.1, 6.2_

- [ ] 7. Add Comprehensive Testing
  - [ ]* 7.1 Write unit tests for Gemini configuration
    - Test saving/loading gemini_enabled
    - Test saving/loading prompt
    - Test saving/loading timeout
    - Test saving/loading model
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ]* 7.2 Write unit tests for Gemini validation
    - Test API key validation
    - Test prompt validation
    - Test model initialization
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 7.3 Write unit tests for Gemini processing
    - Test successful Gemini call
    - Test Gemini error handling
    - Test Gemini timeout handling
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ]* 7.4 Write property tests for builder pattern
    - Test configuration independence
    - Test option preservation
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 8. Checkpoint - Verify Gemini Integration
  - Ensure all Gemini configuration is properly saved/loaded
  - Ensure Gemini validation works correctly
  - Ensure Gemini processing executes when enabled
  - Ensure Gemini timeout is enforced
  - Ensure Gemini errors are logged properly
  - Ensure OCR text is available when Gemini fails
  - Test with actual Gemini API key

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Focus on core Gemini processing first (tasks 1-6)
- Add comprehensive testing after core functionality works
- All Gemini operations should be logged for debugging
- Gemini should be optional and graceful - if it fails, OCR text should still work
