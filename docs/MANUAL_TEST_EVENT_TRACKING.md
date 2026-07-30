# Manual Test Plan: Event Tracking

## Expected Behavior

- `READ_PASSIVE` with `passive_mode = "event_tracking"` keeps scanning continuously by the existing scan cycle.
- If OCR text does not match `event_ocr_pattern`, the action keeps scanning.
- If OCR text matches `event_ocr_pattern`, the action ends immediately and the tool moves to the next action.
- `special_event_tracking` is not covered by this document.

## Test Case 1: Save basic event tracking settings

1. Open a `READ_PASSIVE` action.
2. Set mode to `Event Tracking`.
3. Configure:
   - OCR Engine
   - OCR Pattern
   - Match Threshold
   - Teaching image / ROI
4. Save and reopen the dialog.

Expected:
- Settings persist correctly.
- There are no fields for delay/reset/telegram message.

## Test Case 2: Keep scanning while not matched

1. Configure `event_ocr_pattern` to a text that is not currently visible.
2. Run the tool.
3. Observe logs for multiple scan cycles.

Expected:
- The action does not finish.
- OCR continues to run on each scan cycle.

## Test Case 3: Finish action when pattern matches

1. Configure pattern:
   - `{event_name} sẽ bắt đầu sau {minutes} phút`
2. Run the tool with a following action after this `READ_PASSIVE`.
3. Make the target window show matching text such as:
   - `Sự kiện Imperial Guardian sẽ bắt đầu sau 5 phút`

Expected:
- Log shows an event tracking match with extracted variables.
- Current `READ_PASSIVE` action ends immediately.
- Tool continues to the next action.

## Test Case 4: Pattern mismatch does not advance tool

1. Configure a pattern that does not match the visible OCR text.
2. Run the tool.

Expected:
- Tool stays on the current `READ_PASSIVE` action.
- It does not advance until a match happens or the execution is stopped manually.
