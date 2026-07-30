# Manual Test: Special Event Tracking Mode

## TC-01: Select Special Event Tracking mode

**Purpose:** Verify UI correctly switches to Special Event Tracking mode
**Preconditions:** 
- App is running
- Have an existing READ_PASSIVE action or create new one
**Execution:**
1. Open settings dialog of a READ_PASSIVE action
2. Dropdown "Mode" -> select "Special Event Tracking"
3. Observe UI layout changes
**Expected Results:** Section "Special Events" displays, other sections hide
**Settings to verify:** passive_mode = "special_event_tracking"

## TC-02: Tick/untick Imperial Guardian checkbox

**Purpose:** Verify Imperial Guardian section expand/collapse correctly
**Preconditions:** 
- In Special Event Tracking mode (TC-01 completed)
**Execution:**
1. Tick checkbox "Imperial Guardian"
2. Observe section expansion
3. Untick checkbox
4. Observe section collapse
**Expected Results:** 
- Step 2: Collapsible section expands, displays SpinBox delay and Teaching image widget
- Step 4: Collapsible section collapses, hides completely
**Settings to verify:** imperial_guardian_enabled = True/False

## TC-03: Persist settings

**Purpose:** Verify Imperial Guardian settings persist across app restart
**Preconditions:** 
- In Special Event Tracking mode
- Imperial Guardian checkbox ticked
**Execution:**
1. Enter delay = 15, select Teaching image
2. Click Save -> close app -> reopen
3. Reopen settings dialog of that action
**Expected Results:** Checkbox still ticked, delay = 15, Teaching image path correct
**Settings to verify:** 
- imperial_guardian_enabled = True
- imperial_guardian_no_player_alert_delay = 15
- imperial_guardian_teaching_corner_x1/y1/x2/y2 = valid coordinates

## TC-04: Subscribe when running action

**Purpose:** Verify subscription setup when action starts
**Preconditions:** 
- Imperial Guardian enabled
- ROI configured (valid teaching image coordinates)
- Telegram notifier configured
**Execution:**
1. Run action
2. Monitor log output
**Expected Results:** Log displays "[Special Event] Imperial Guardian: subscribed"
**Settings to verify:** ScreenScanService subscription created

## TC-05: Unsubscribe when stopping action

**Purpose:** Verify subscription cleanup when action stops
**Preconditions:** 
- Action is running with Imperial Guardian enabled (TC-04 completed)
**Execution:**
1. Stop action
2. Monitor log output
**Expected Results:** Log displays "[Special Event] Imperial Guardian: unsubscribed"
**Settings to verify:** ScreenScanService subscription removed

## TC-06: ROI not configured warning

**Purpose:** Verify graceful handling when ROI not configured
**Preconditions:** 
- Imperial Guardian checkbox ticked
- Teaching image NOT configured
**Execution:**
1. Run action
2. Monitor log output
**Expected Results:** Log warns "ROI not configured, skipping", no subscription
**Settings to verify:** No subscription created, graceful error handling

## TC-07: Backward compatibility

**Purpose:** Verify old actions work without new fields
**Preconditions:** 
- Have existing action JSON without imperial_guardian_* fields
**Execution:**
1. Open old action
2. Open settings dialog
3. Check Imperial Guardian section state
**Expected Results:** Checkbox untick (default false), delay = 10, no crash
**Settings to verify:** 
- imperial_guardian_enabled = False (default)
- imperial_guardian_no_player_alert_delay = 10 (default)
- imperial_guardian_teaching_corner_* = 0 (default)

## TC-08: Match threshold setting

**Purpose:** Verify match threshold is saved and used for OCR matching
**Preconditions:**
- Imperial Guardian enabled, ROI configured
**Execution:**
1. Set Match threshold to 85%
2. Click Save -> close app -> reopen
3. Reopen settings dialog
**Expected Results:** Match threshold = 85% persists
**Settings to verify:**
- imperial_guardian_match_threshold = 85.0

## TC-09: Test Algorithms button

**Purpose:** Verify Test Algorithms button opens algorithm testing dialog
**Preconditions:**
- Imperial Guardian enabled
- ROI configured (valid coordinates)
**Execution:**
1. Click "Test Algorithms" button
2. Select some algorithms in the dialog
3. Close dialog
4. Observe Selected Algorithms list
**Expected Results:**
- Dialog opens with ROI of Imperial Guardian
- After closing, Selected Algorithms list updates
**Settings to verify:** imperial_guardian_ocr_algorithms saved

## TC-10: Backward compatibility for new fields

**Purpose:** Verify old actions without match_threshold/ocr_algorithms use defaults
**Preconditions:**
- Have existing action JSON without imperial_guardian_match_threshold/ocr_algorithms
**Execution:**
1. Open old action
2. Open settings dialog
3. Check Imperial Guardian section
**Expected Results:** match_threshold = 70 (default), algorithms list empty, no crash
**Settings to verify:**
- imperial_guardian_match_threshold = 70.0 (default)
- imperial_guardian_ocr_algorithms = [] (default)
