## REVIEW 2026-04-17 09:39:53

- Review ID: `REV-20260417-093953`
- Reviewer: Codex
- Scope: `special-event-tracking` requirements review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 09:28:43`
- Target File Size: `27655 bytes`
- Status: `open`

### Conclusion

Not approved. The file has the main requirements structure, but several issues must be fixed before moving to design.

### Findings

#### F-001
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:319`
- Steering Source: `.kiro/steering/reviewer-rule.md` - checklist requirements
- Issue: The EARS section uses `WHEN`, `THE`, and `SHALL`, while reviewer rules disallow English EARS wording without a clear reason.
- Impact: The file does not comply with the repo requirements format.
- Required update: Remove the EARS section or rewrite acceptance criteria in Vietnamese.

#### F-002
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:23`
- Steering Source: `.kiro/steering/reviewer-rule.md` - field names must be consistent
- Issue: The JSON example uses `imperial_guardian_no_player_delay`, while other sections use `imperial_guardian_no_player_alert_delay`.
- Impact: Implementation may serialize the wrong field and lose settings during save/load.
- Required update: Use one field name consistently, preferably `imperial_guardian_no_player_alert_delay`.

#### F-003
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:184`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md`, `.kiro/steering/coding-guidelines.md`
- Issue: The requirements describe OCR callbacks/background flow and UI logging, but do not mention thread-safe UI updates.
- Impact: Later design/code may update QWidget directly from a background thread.
- Required update: Add a requirement that background callbacks must emit signals and update UI/logs on the UI thread via `QueuedConnection`.

#### F-004
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:190`
- Steering Source: User intent - each event must be enabled/disabled independently
- Issue: Unsubscribe only mentions `unsubscribe(action_id)`, which does not identify which event inside the action should stop.
- Impact: The system may cancel all subscriptions for the action or fail to cancel the intended event.
- Required update: Define subscription identity as `action_id + event_id`, for example `special_event:{action_id}:imperial_guardian`.

#### F-005
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:118`
- Steering Source: Requirements clarity
- Issue: The file references the reopen-time rule by time range but does not include the table or a clear source reference.
- Impact: Implementers do not know which value `X` must be compared against.
- Required update: Copy the time-range table into this file or reference the authoritative source/spec explicitly.

### Open Questions

- Is EARS required for Kiro compatibility? If yes, document the exception.
- Does `ScreenScanService.unsubscribe()` already support `event_id` or `subscription_id`?

### Required Updates

Fix the 5 findings above in `requirements.md`, then request another review before moving to design.


## REVIEW 2026-04-17 11:00:00

- Review ID: `REV-20260417-110000`
- Reviewer: Kiro
- Scope: Follow-up after implementing fixes from REV-20260417-093953
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Status: `resolved`

### Conclusion

All 5 findings from the previous review have been resolved.

### Findings

#### F-001
- Status: `resolved`
- Resolution: Section 6 EARS (WHEN/THE/SHALL) đã bị xóa hoàn toàn.

#### F-002
- Status: `resolved`
- Resolution: Tên field đã thống nhất thành `imperial_guardian_no_player_alert_delay` xuyên suốt file.

#### F-003
- Status: `resolved`
- Resolution: Thêm Lỗi 7 về thread-safe UI updates vào section Error Handling.

#### F-004
- Status: `resolved`
- Resolution: Subscription identity được định nghĩa rõ là `special_event:{action_id}:imperial_guardian` trong Bước 5 và Bước 7.

#### F-005
- Status: `resolved`
- Resolution: Thêm bảng rule thời gian mở lại (5 khung giờ) vào section Parameters, kèm giải thích logic countdown.

### Open Questions

Không còn open questions.

## REVIEW 2026-04-17 14:41:11

- Review ID: `REV-20260417-144111`
- Reviewer: Codex
- Scope: `special-event-tracking` requirements review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 14:38:29`
- Target File Size: `14593 bytes`
- Status: `resolved`

### Conclusion

Not approved yet. The previous findings were addressed, but the current `requirements.md` still violates requirements-format rules.

### Findings

#### F-001
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:127`
- Steering Source: `.kiro/steering/reviewer-rule.md` and `.kiro/steering/feature-development-workflow.md`
- Issue: Main flow steps 2-5 do not describe `Input`, `Xử lý/Process`, and `Output` explicitly for each step.
- Impact: The requirements are less traceable and do not match the required Step 1 output format.
- Required update: Rewrite each main-flow step with explicit `Input`, `Xử lý`, and `Output` bullets.

#### F-002
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:160`
- Steering Source: `.kiro/steering/feature-development-workflow.md`
- Issue: Error handling entries are compressed into one-line statements and do not include `Nguyên nhân` and `Xử lý` fields.
- Impact: The error-handling behavior is underspecified for implementers and testers.
- Required update: Expand each error case into `Nguyên nhân` and `Xử lý` bullets.

#### F-003
- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:33`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` - table formatting
- Issue: The Parameters table columns are not padded/aligned consistently.
- Impact: The file violates the repo Markdown table formatting rule and is harder to scan.
- Required update: Reformat the table so all columns are aligned with padding spaces.

### Open Questions

None.

## REVIEW 2026-04-17 14:48:56

- Review ID: `REV-20260417-144856`
- Reviewer: Codex
- Scope: `special-event-tracking` content conflict review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target File Size: `16166 bytes`
- Status: `open`

### Conclusion

Not approved for design yet. The framework requirements and the Imperial Guardian event requirements conflict on ROI ownership and persistence fields.

### Findings

#### F-001
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:33`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:28`
- Steering Source: Requirements consistency and `.kiro/steering/reviewer-rule.md` field consistency checklist
- Issue: The framework spec defines per-event ROI fields (`{event_id}_teaching_corner_x1/y1/x2/y2`) and says each event has its own Teaching image. The Imperial Guardian spec still says ROI reuses shared Teaching image fields (`teaching_corner_x1/y1/x2/y2`).
- Impact: Implementers cannot know whether `imperial_guardian` should persist ROI in event-scoped fields or reuse action-level ROI fields. This can cause save/load bugs or incompatible UI behavior.
- Required update: Choose one model and make both files consistent. If special events have per-event ROI, update `imperial-guardian-event-tracker.md` to use `imperial_guardian_teaching_corner_x1/y1/x2/y2` and remove shared ROI wording. If ROI is shared, remove per-event ROI fields from the framework spec.

#### F-002
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:41`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:237`
- Steering Source: Requirements consistency and persistence rules
- Issue: The framework spec delegates event-specific parameters to each event file, but the Imperial Guardian persistence rules only persist `imperial_guardian_no_player_alert_delay` and shared ROI fields, not the framework's per-event ROI fields.
- Impact: The persistence checklist is inconsistent across the parent spec and the event spec, so implementation can pass one checklist while failing the other.
- Required update: Align the Imperial Guardian persistence section with the framework persistence model, including all required event-scoped ROI fields if that model is kept.

### Open Questions

- Should every special event own a separate Teaching image/ROI, or should all events in one action share the action Teaching image?

### Required Updates

Resolve the ROI ownership decision and update both `requirements.md` and `imperial-guardian-event-tracker.md` consistently before moving to design.

## REVIEW 2026-04-17 14:57:10

- Review ID: `REV-20260417-145710`
- Reviewer: Codex
- Scope: `special-event-tracking` full requirements consistency review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target Related File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target File Size: `16166 bytes`
- Status: `open`

### Conclusion

Not approved yet. The ROI ownership conflict is resolved, but one remaining wording conflict can mislead implementation.

### Findings

#### F-001
- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:190`
- Steering Source: Requirements consistency
- Issue: The Imperial Guardian UI section is still titled `Dialog cài đặt action (Event Tracking mode)`, while the parent feature defines the new mode as `Special Event Tracking`.
- Impact: Implementers may confuse the old `event_tracking` mode with the new `special_event_tracking` mode and place the UI/settings in the wrong mode section.
- Required update: Rename the heading and mockup context to `Special Event Tracking mode` or explicitly state that this event UI is rendered inside the `special_event_tracking` event section.

### Resolved Checks

- `REV-20260417-144928/F-001`: Resolved. Parent and Imperial Guardian specs now both use event-scoped ROI fields.
- `REV-20260417-144928/F-002`: Resolved. Imperial Guardian persistence now includes `imperial_guardian_teaching_corner_x1/y1/x2/y2`.

### Open Questions

None.

### Required Updates

Fix the remaining mode-name conflict in `imperial-guardian-event-tracker.md`, then request another review.

## REVIEW 2026-04-17 15:02:09

- Review ID: `REV-20260417-150209`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up consistency review
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:59:19`
- Target File Size: `15435 bytes`
- Status: `open`

### Conclusion

Not approved yet. The heading was updated, but the UI mockup still shows the old mode name.

### Findings

#### F-001
- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:196`
- Steering Source: Requirements consistency
- Issue: The UI mockup still displays `Chế độ: [Event Tracking ▼]` under a heading that says the dialog is inside `Special Event Tracking mode`.
- Impact: The mockup still suggests the old `event_tracking` mode, which can mislead the UI implementation.
- Required update: Change the mockup dropdown text to `Special Event Tracking`, or remove the mode dropdown from this event-level mockup and show only the event section content.

### Resolved Checks

- `REV-20260417-145710/F-001`: Partially resolved. The section heading now references `Special Event Tracking mode`, but the mockup content still needs alignment.

### Open Questions

None.

### Required Updates

Fix the mockup mode label, then request another review.

## REVIEW 2026-04-17 15:02:09

- Review ID: `REV-20260417-150209`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up consistency review
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:59:19`
- Target File Size: `15435 bytes`
- Status: `open`

### Conclusion

Not approved yet. The heading was updated, but the UI mockup still shows the old mode name.

### Findings

#### F-001
- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:196`
- Steering Source: Requirements consistency
- Issue: The UI mockup still displays `Chế độ: [Event Tracking ▼]` under a heading that says the dialog is inside `Special Event Tracking mode`.
- Impact: The mockup still suggests the old `event_tracking` mode, which can mislead the UI implementation.
- Required update: Change the mockup dropdown text to `Special Event Tracking`, or remove the mode dropdown from this event-level mockup and show only the event section content.

### Resolved Checks

- `REV-20260417-145710/F-001`: Partially resolved. The section heading now references `Special Event Tracking mode`, but the mockup content still needs alignment.

### Open Questions

None.

### Required Updates

Fix the mockup mode label, then request another review.

### Required Updates

Fix the 3 findings above, then request another review before moving to design.

## REVIEW 2026-04-17 14:45:41

- Review ID: `REV-20260417-144541`
- Reviewer: Codex
- Scope: `special-event-tracking` requirements follow-up review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target File Size: `16166 bytes`
- Status: `resolved`

### Conclusion

Approved for moving to design. The current `requirements.md` addresses the open findings from `REV-20260417-144111`.

### Findings

No open findings.

### Resolved Checks

- `REV-20260417-144111/F-001`: Resolved. Main flow steps 2-5 now include explicit `Input`, `Xử lý`, and `Output`.
- `REV-20260417-144111/F-002`: Resolved. Error handling entries now include `Nguyên nhân` and `Xử lý`.
- `REV-20260417-144111/F-003`: Resolved. The Parameters table is now padded/aligned consistently.

### Notes

The previous `REV-20260417-144111` block was marked `Status: resolved` by the developer but still contains the old "Not approved" conclusion and `Status: open` finding entries. This block supersedes it as the latest review result.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-20 17:53:27

- Review ID: `REV-20260420-175327`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3 tests-only follow-up review
- Target Diff: current Step 3 artifacts in worktree
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
- Status: `resolved`

### Conclusion

Not approved for moving to Step 4 yet. The implementation changes have been removed from the current diff, which resolves the Step 3/Step 4 mixing problem for this pass. However, the Step 3 output is incomplete and the current automated tests do not pass.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 output; `.kiro/specs/special-event-tracking/tasks.md` Task 4
- Issue: The required manual test plan file is missing from the current worktree.
- Impact: Step 3 is incomplete because it must produce unit tests, integration tests, and `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`.
- Required update: Create `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` with concrete manual cases for mode selection, tick/untick behavior, save/load settings, subscribe/stop unsubscribe, invalid ROI warning, and backward compatibility.

#### F-002

- Severity: Blocker
- Status: open
- Location: test run for `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 checkpoint; `.kiro/steering/00-MASTER-RULES.md` testing rules
- Issue: `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration` fails with 25 errors and 1 failure. The failures are expected for some test-first cases, but the current Step 3 artifact is not runnable as a clean test baseline because missing production modules/fields cause import and attribute errors across the suite.
- Impact: The Step 3 result cannot be used as a reliable checkpoint before Step 4. It is unclear which failures are intentional red tests and which are broken test setup/import assumptions.
- Required update: Either mark this as an intentional red-test baseline with the exact expected failures before Step 4, or adjust the tests so they are structurally valid and fail only on the not-yet-implemented behavior. At minimum, document the expected failing tests in the Step 3 handoff.

#### F-003

- Severity: Major
- Status: open
- Location: `tests/test_special_event_tracking_integration.py:34`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 integration tests; `.kiro/steering/coding-guidelines.md` no mocking subject under test
- Issue: The integration tests patch `ImperialGuardianHandler` and call future private methods on `SystemExecutor` that do not exist yet. Because the whole target integration path is missing, the current tests mostly fail at import/attribute lookup instead of verifying the intended subscription behavior.
- Impact: These tests are weaker as a test-first contract: after implementation, they may still pass with an over-mocked handler and may not prove that the real handler callback is wired correctly.
- Required update: Keep external dependencies mocked, but avoid mocking the subject path that should prove integration. Make the tests assert the created subscription callback and identity using the real handler once the production module exists, or clearly split this into a unit-level executor test with documented mocks.

### Resolved Checks

- `REV-20260420-174017/F-001`: Resolved for the current worktree. The Step 4 implementation files are no longer present in the active diff.
- `REV-20260420-174017/F-003`: Partially resolved. The persistence test now calls production `Tool.from_dict()`, but the suite still fails because the production fields are not implemented yet.

### Open Questions

- Should Step 3 be accepted as an intentional red-test baseline, or does the project require tests to pass before approving Step 3? Current steering requires writing tests before code, but the handoff should still state expected failures clearly.

### Required Updates

Add the missing manual test plan and clarify/fix the red-test baseline. After that, request another Step 3 review before moving to Step 4.

## REVIEW 2026-04-20 17:40:17

- Review ID: `REV-20260420-174017`
- Reviewer: Codex
- Scope: `special-event-tracking` step result review
- Target Diff: current worktree changes for Step 3/Step 4 artifacts
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `src/logic/system_executor/imperial_guardian_handler.py`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/ui/passive_read_settings_dialog.py`, `src/ui/action_config_dialog.py`
- Status: `open`

### Conclusion

Not approved yet. The new tests execute successfully with `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration`, but the step result mixes Step 3 test artifacts with Step 4 implementation changes and leaves a persistence-breaking UI save path.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: current diff: `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/ui/passive_read_settings_dialog.py`, `src/logic/system_executor/imperial_guardian_handler.py`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` Step 3/Step 4 order; `.kiro/steering/feature-development-workflow.md` Step 3 checkpoint
- Issue: The latest approved review was for moving to test creation, but the current worktree already includes implementation changes in logic/UI files, not only Step 3 test and manual-test-plan outputs.
- Impact: The workflow checkpoint is skipped: Step 3 cannot be reviewed and approved cleanly before Step 4 implementation begins.
- Required update: Separate the step result. Either limit the current step review to tests/manual plan and park implementation changes until Step 3 is approved, or explicitly request/record approval that this review covers Step 4 implementation as well.

#### F-002

- Severity: Blocker
- Status: open
- Location: `src/ui/action_config_dialog.py:283`
- Steering Source: `.kiro/specs/special-event-tracking/requirements.md` persistence rules; `.kiro/steering/00-MASTER-RULES.md` persistence rule
- Issue: `PassiveReadSettingsDialog.get_settings()` returns the new `imperial_guardian_*` settings, but `ActionConfigDialog` does not copy those returned values into `self.action` after `dlg.exec()`. It stops after `event_ocr_engine` and `ocr_post_patterns`.
- Impact: User changes to `imperial_guardian_enabled` and `imperial_guardian_no_player_alert_delay` can be lost on save, so `_action_to_dict()` may persist stale/default values and the event may not subscribe even after the checkbox is enabled.
- Required update: In the READ_PASSIVE branch of `ActionConfigDialog`, assign all six returned `imperial_guardian_*` fields to `self.action` before closing the dialog.

#### F-003

- Severity: Major
- Status: open
- Location: `tests/test_special_event_tracking_persistence.py:25`
- Steering Source: `.kiro/specs/special-event-tracking/tasks.md` Task 2; `.kiro/steering/feature-development-workflow.md` Step 3 automated tests
- Issue: The persistence "round trip" test calls `Tool._action_to_dict()` but then manually reconstructs a new action from the dict instead of exercising `Tool.from_dict()`. The backward-compat test also manually applies defaults instead of calling the production loader.
- Impact: The tests can pass even if `Tool.from_dict()` drops or miscasts the new fields, which is the main persistence risk this task was supposed to cover.
- Required update: Build a real `Tool` payload with an action, call `Tool.from_dict()`, and assert the restored action fields. Add a JSON-old-data case that omits the new fields and verifies production defaults through `Tool.from_dict()`.

#### F-004

- Severity: Major
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md:3`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 manual test plan format
- Issue: The manual test plan lists steps and expected results, but it does not include the required per-case `Purpose`, `Preconditions`, and `Settings to verify` sections.
- Impact: Manual validation is less traceable, especially for persistence and subscription lifecycle settings.
- Required update: Expand each manual test case with purpose, preconditions, execution steps, expected results, and settings/fields to verify.

### Open Questions

- Is the developer asking for a Step 3 tests-only review, or should this review also cover the already-created Step 4 implementation?

### Required Updates

Resolve the workflow boundary and fix the UI save path before treating the step as approved. Then update the persistence tests and manual test plan so Step 3 coverage matches the approved task plan.

## REVIEW 2026-04-20 17:53:27

- Review ID: `REV-20260420-175327`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3 tests-only follow-up review
- Target Diff: current Step 3 artifacts in worktree
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
- Status: `open`

### Conclusion

Not approved for moving to Step 4 yet. The implementation changes have been removed from the current diff, which resolves the Step 3/Step 4 mixing problem for this pass. However, the Step 3 output is incomplete and the current automated tests do not pass.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 output; `.kiro/specs/special-event-tracking/tasks.md` Task 4
- Issue: The required manual test plan file is missing from the current worktree.
- Impact: Step 3 is incomplete because it must produce unit tests, integration tests, and `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`.
- Required update: Create `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` with concrete manual cases for mode selection, tick/untick behavior, save/load settings, subscribe/stop unsubscribe, invalid ROI warning, and backward compatibility.

#### F-002

- Severity: Blocker
- Status: open
- Location: test run for `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 checkpoint; `.kiro/steering/00-MASTER-RULES.md` testing rules
- Issue: `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration` fails with 25 errors and 1 failure. The failures are expected for some test-first cases, but the current Step 3 artifact is not runnable as a clean test baseline because missing production modules/fields cause import and attribute errors across the suite.
- Impact: The Step 3 result cannot be used as a reliable checkpoint before Step 4. It is unclear which failures are intentional red tests and which are broken test setup/import assumptions.
- Required update: Either mark this as an intentional red-test baseline with the exact expected failures before Step 4, or adjust the tests so they are structurally valid and fail only on the not-yet-implemented behavior. At minimum, document the expected failing tests in the Step 3 handoff.

#### F-003

- Severity: Major
- Status: open
- Location: `tests/test_special_event_tracking_integration.py:34`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 integration tests; `.kiro/steering/coding-guidelines.md` no mocking subject under test
- Issue: The integration tests patch `ImperialGuardianHandler` and call future private methods on `SystemExecutor` that do not exist yet. Because the whole target integration path is missing, the current tests mostly fail at import/attribute lookup instead of verifying the intended subscription behavior.
- Impact: These tests are weaker as a test-first contract: after implementation, they may still pass with an over-mocked handler and may not prove that the real handler callback is wired correctly.
- Required update: Keep external dependencies mocked, but avoid mocking the subject path that should prove integration. Make the tests assert the created subscription callback and identity using the real handler once the production module exists, or clearly split this into a unit-level executor test with documented mocks.

### Resolved Checks

- `REV-20260420-174017/F-001`: Resolved for the current worktree. The Step 4 implementation files are no longer present in the active diff.
- `REV-20260420-174017/F-003`: Partially resolved. The persistence test now calls production `Tool.from_dict()`, but the suite still fails because the production fields are not implemented yet.

### Open Questions

- Should Step 3 be accepted as an intentional red-test baseline, or does the project require tests to pass before approving Step 3? Current steering requires writing tests before code, but the handoff should still state expected failures clearly.

### Required Updates

Add the missing manual test plan and clarify/fix the red-test baseline. After that, request another Step 3 review before moving to Step 4.

## REVIEW 2026-04-20 17:40:17

- Review ID: `REV-20260420-174017`
- Reviewer: Codex
- Scope: `special-event-tracking` step result review
- Target Diff: current worktree changes for Step 3/Step 4 artifacts
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `src/logic/system_executor/imperial_guardian_handler.py`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/ui/passive_read_settings_dialog.py`, `src/ui/action_config_dialog.py`
- Status: `resolved`

### Conclusion

Not approved yet. The new tests execute successfully with `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration`, but the step result mixes Step 3 test artifacts with Step 4 implementation changes and leaves a persistence-breaking UI save path.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: current diff: `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/ui/passive_read_settings_dialog.py`, `src/logic/system_executor/imperial_guardian_handler.py`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` Step 3/Step 4 order; `.kiro/steering/feature-development-workflow.md` Step 3 checkpoint
- Issue: The latest approved review was for moving to test creation, but the current worktree already includes implementation changes in logic/UI files, not only Step 3 test and manual-test-plan outputs.
- Impact: The workflow checkpoint is skipped: Step 3 cannot be reviewed and approved cleanly before Step 4 implementation begins.
- Required update: Separate the step result. Either limit the current step review to tests/manual plan and park implementation changes until Step 3 is approved, or explicitly request/record approval that this review covers Step 4 implementation as well.

#### F-002

- Severity: Blocker
- Status: open
- Location: `src/ui/action_config_dialog.py:283`
- Steering Source: `.kiro/specs/special-event-tracking/requirements.md` persistence rules; `.kiro/steering/00-MASTER-RULES.md` persistence rule
- Issue: `PassiveReadSettingsDialog.get_settings()` returns the new `imperial_guardian_*` settings, but `ActionConfigDialog` does not copy those returned values into `self.action` after `dlg.exec()`. It stops after `event_ocr_engine` and `ocr_post_patterns`.
- Impact: User changes to `imperial_guardian_enabled` and `imperial_guardian_no_player_alert_delay` can be lost on save, so `_action_to_dict()` may persist stale/default values and the event may not subscribe even after the checkbox is enabled.
- Required update: In the READ_PASSIVE branch of `ActionConfigDialog`, assign all six returned `imperial_guardian_*` fields to `self.action` before closing the dialog.

#### F-003

- Severity: Major
- Status: open
- Location: `tests/test_special_event_tracking_persistence.py:25`
- Steering Source: `.kiro/specs/special-event-tracking/tasks.md` Task 2; `.kiro/steering/feature-development-workflow.md` Step 3 automated tests
- Issue: The persistence "round trip" test calls `Tool._action_to_dict()` but then manually reconstructs a new action from the dict instead of exercising `Tool.from_dict()`. The backward-compat test also manually applies defaults instead of calling the production loader.
- Impact: The tests can pass even if `Tool.from_dict()` drops or miscasts the new fields, which is the main persistence risk this task was supposed to cover.
- Required update: Build a real `Tool` payload with an action, call `Tool.from_dict()`, and assert the restored action fields. Add a JSON-old-data case that omits the new fields and verifies production defaults through `Tool.from_dict()`.

#### F-004

- Severity: Major
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md:3`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 manual test plan format
- Issue: The manual test plan lists steps and expected results, but it does not include the required per-case `Purpose`, `Preconditions`, and `Settings to verify` sections.
- Impact: Manual validation is less traceable, especially for persistence and subscription lifecycle settings.
- Required update: Expand each manual test case with purpose, preconditions, execution steps, expected results, and settings/fields to verify.

### Open Questions

- Is the developer asking for a Step 3 tests-only review, or should this review also cover the already-created Step 4 implementation?

### Required Updates

Resolve the workflow boundary and fix the UI save path before treating the step as approved. Then update the persistence tests and manual test plan so Step 3 coverage matches the approved task plan.

## REVIEW 2026-04-17 14:49:28

- Review ID: `REV-20260417-144928`
- Reviewer: Codex
- Scope: `special-event-tracking` content conflict review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target File Size: `16166 bytes`
- Status: `resolved`

### Conclusion

Not approved for design yet. The framework requirements and the Imperial Guardian event requirements conflict on ROI ownership and persistence fields.

### Findings

#### F-001
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:33`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:28`
- Steering Source: Requirements consistency and `.kiro/steering/reviewer-rule.md` field consistency checklist
- Issue: The framework spec defines per-event ROI fields (`{event_id}_teaching_corner_x1/y1/x2/y2`) and says each event has its own Teaching image. The Imperial Guardian spec still says ROI reuses shared Teaching image fields (`teaching_corner_x1/y1/x2/y2`).
- Impact: Implementers cannot know whether `imperial_guardian` should persist ROI in event-scoped fields or reuse action-level ROI fields. This can cause save/load bugs or incompatible UI behavior.
- Required update: Choose one model and make both files consistent. If special events have per-event ROI, update `imperial-guardian-event-tracker.md` to use `imperial_guardian_teaching_corner_x1/y1/x2/y2` and remove shared ROI wording. If ROI is shared, remove per-event ROI fields from the framework spec.

#### F-002
- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:41`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:237`
- Steering Source: Requirements consistency and persistence rules
- Issue: The framework spec delegates event-specific parameters to each event file, but the Imperial Guardian persistence rules only persist `imperial_guardian_no_player_alert_delay` and shared ROI fields, not the framework's per-event ROI fields.
- Impact: The persistence checklist is inconsistent across the parent spec and the event spec, so implementation can pass one checklist while failing the other.
- Required update: Align the Imperial Guardian persistence section with the framework persistence model, including all required event-scoped ROI fields if that model is kept.

### Open Questions

- Should every special event own a separate Teaching image/ROI, or should all events in one action share the action Teaching image?

### Required Updates

Resolve the ROI ownership decision and update both `requirements.md` and `imperial-guardian-event-tracker.md` consistently before moving to design.

## REVIEW 2026-04-17 14:57:10

- Review ID: `REV-20260417-145710`
- Reviewer: Codex
- Scope: `special-event-tracking` full requirements consistency review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target Related File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target File Size: `16166 bytes`
- Status: `open`

### Conclusion

Not approved yet. The ROI ownership conflict is resolved, but one remaining wording conflict can mislead implementation.

### Findings

#### F-001
- Severity: `Minor`
- Status: `resolved`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:190`
- Steering Source: Requirements consistency
- Issue: The Imperial Guardian UI section is still titled `Dialog cài đặt action (Event Tracking mode)`, while the parent feature defines the new mode as `Special Event Tracking`.
- Impact: Implementers may confuse the old `event_tracking` mode with the new `special_event_tracking` mode and place the UI/settings in the wrong mode section.
- Required update: Rename the heading and mockup context to `Special Event Tracking mode` or explicitly state that this event UI is rendered inside the `special_event_tracking` event section.

### Resolved Checks

- `REV-20260417-144928/F-001`: Resolved. Parent and Imperial Guardian specs now both use event-scoped ROI fields.
- `REV-20260417-144928/F-002`: Resolved. Imperial Guardian persistence now includes `imperial_guardian_teaching_corner_x1/y1/x2/y2`.

### Open Questions

None.

### Required Updates

Fix the remaining mode-name conflict in `imperial-guardian-event-tracker.md`, then request another review.

## REVIEW 2026-04-17 15:02:09

- Review ID: `REV-20260417-150209`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up consistency review
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:59:19`
- Target File Size: `15435 bytes`
- Status: `open`

### Conclusion

Not approved yet. The heading was updated, but the UI mockup still shows the old mode name.

### Findings

#### F-001
- Severity: `Minor`
- Status: `resolved`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:196`
- Steering Source: Requirements consistency
- Issue: The UI mockup still displays `Chế độ: [Event Tracking ▼]` under a heading that says the dialog is inside `Special Event Tracking mode`.
- Impact: The mockup still suggests the old `event_tracking` mode, which can mislead the UI implementation.
- Required update: Change the mockup dropdown text to `Special Event Tracking`, or remove the mode dropdown from this event-level mockup and show only the event section content.

### Resolved Checks

- `REV-20260417-145710/F-001`: Partially resolved. The section heading now references `Special Event Tracking mode`, but the mockup content still needs alignment.

### Open Questions

None.

### Required Updates

Fix the mockup mode label, then request another review.

## REVIEW 2026-04-17 15:06:48

- Review ID: `REV-20260417-150648`
- Reviewer: Codex
- Scope: `special-event-tracking` final requirements consistency review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target Related File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 14:44:15`
- Target Related File Timestamp: `2026-04-17 15:04:37`
- Status: `resolved`

### Conclusion

Approved for moving to design. The remaining mockup mode-label conflict has been fixed, and no new requirements conflicts were found.

### Findings

No open findings.

### Resolved Checks

- `REV-20260417-150209/F-001`: Resolved. The Imperial Guardian mockup now shows `Special Event Tracking`.
- ROI ownership remains consistent: parent and event specs both use event-scoped ROI fields.
- Persistence remains consistent: parent and event specs both require event-scoped ROI fields to be saved and loaded.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-17 15:18:38

- Review ID: `REV-20260417-151838`
- Reviewer: Codex
- Scope: `special-event-tracking` content conflict review
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target Related File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Status: `resolved`

### Conclusion

Approved. No content conflicts were found between the parent Special Event Tracking requirements and the Imperial Guardian event requirements.

### Findings

No open findings.

### Checked Areas

- Mode naming is consistent: both specs use `Special Event Tracking`.
- ROI ownership is consistent: both specs use event-scoped ROI fields.
- Persistence is consistent: both specs save/load event-scoped ROI and event-specific parameters.
- Runtime delegation is consistent: the parent spec delegates event behavior to the event requirements file.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-17 15:27:55

- Review ID: `REV-20260417-152755`
- Reviewer: Codex
- Scope: `special-event-tracking` Imperial Guardian requirements follow-up review
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 15:26:18`
- Target File Size: `12819`
- Status: `open`

### Conclusion

Not approved for moving to design yet. One requirements gap remains in the Imperial Guardian event spec: the event defines UI-backed settings but no longer includes an event-level UI mockup or component description for those settings.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:188`
- Steering Source: `.kiro/steering/reviewer-rule.md` checklist for `requirements.md`; `.kiro/steering/feature-development-workflow.md` Step 1 output format
- Issue: The file defines event-specific dialog fields in Persistence Rules, including `SpinBox imperial_guardian_no_player_alert_delay` and the Teaching image widget, but the current event requirements file has no event-level UI mockup/component section describing how those controls appear inside the expanded Imperial Guardian settings.
- Impact: The design step would need to infer UI layout and control ownership, increasing the chance that the delay setting or event-specific Teaching image is implemented inconsistently with the parent Special Event Tracking dialog.
- Required update: Add a concise event-level UI section or mockup showing the expanded Imperial Guardian settings, including `imperial_guardian_no_player_alert_delay` and the event-specific Teaching image widget. Keep the parent mode dropdown context only if needed; the event section itself must be clear.

### Open Questions

None.

### Required Updates

Add the Imperial Guardian event-level UI section, then request another review.

## REVIEW 2026-04-17 15:29:17

- Review ID: `REV-20260417-152917`
- Reviewer: Codex
- Scope: `special-event-tracking` Imperial Guardian requirements scope clarification review
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target Related File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-17 15:26:18`
- Target File Size: `12819`
- Status: `resolved`

### Conclusion

Approved with scope clarification. The Imperial Guardian event requirements are allowed to omit a standalone UI mockup because the master Special Event Tracking requirements own the parent dialog and event expansion UI. The event file may define event-specific fields and behavior without duplicating the master UI.

### Findings

No open findings.

### Resolved Or Obsolete Checks

- `REV-20260417-152755/F-001`: Obsolete by scope clarification. The event-level UI mockup is not required in this file when the master requirements define the shared UI container and this file only defines event-specific settings/behavior.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-17 16:21:41

- Review ID: `REV-20260417-162141`
- Reviewer: Codex
- Scope: `special-event-tracking` design review
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target Related Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-17 15:37:03`
- Target File Size: `12673`
- Status: `resolved`

### Conclusion

Not approved for moving to tests yet. The design covers the main UI, persistence, and handler shape, but it has runtime integration and dependency gaps that would either skip `special_event_tracking` execution or crash when the new handler is imported.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:44`
- Steering Source: `.kiro/specs/special-event-tracking/requirements.md` runtime flow; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: The design says `SystemExecutor._run_passive_read_via_scan_service()` handles `mode == "special_event_tracking"`, but the concrete design only adds `_setup_special_event_subscriptions()` and does not specify updating the existing `_run_passive_read()` routing guard. The current code routes only `read_data` and `event_tracking` to `_run_passive_read_via_scan_service`; `special_event_tracking` would fall through to the existing passive image-detect path unless the guard is changed.
- Impact: A developer following this design can add the new handler but still never execute it for actions whose `passive_mode` is `special_event_tracking`.
- Required update: Explicitly add the required integration point in `src/logic/system_executor/system_executor.py`: route `special_event_tracking` into the scan-service path, then branch inside `_run_passive_read_via_scan_service()` to call `_setup_special_event_subscriptions()` and keep the action alive until stop/cancel.

#### F-002

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:152`
- Steering Source: `.kiro/steering/feature-development-workflow.md` dependency analysis; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: The handler skeleton imports `rapidfuzz` directly, but the dependency section does not declare a new dependency and the current `requirements.txt` does not list `rapidfuzz`.
- Impact: Fresh installs can fail at import time when `imperial_guardian_handler.py` is loaded.
- Required update: Either add `rapidfuzz` to the design's dependency list and implementation/test dependency plan, or design a fallback path like the existing event tracking helper uses when `rapidfuzz` is unavailable.

#### F-003

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:251`
- Steering Source: `.kiro/specs/special-event-tracking/requirements.md` Step 4 and Edge Case 3; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: The design defines `_teardown_special_event_subscriptions()` but does not state when it is called for stop/cancel, mode changes, disabled events, or settings updates while the action is running.
- Impact: Subscriptions can leak or keep scanning after the event is disabled, which conflicts with the requirement to unsubscribe disabled events and release `ScreenScanService` subscriptions.
- Required update: Define the special-event subscription lifecycle explicitly: subscribe enabled events on start, unsubscribe each event identity in `finally` on stop/cancel, and unsubscribe/update affected identities when settings are saved while the action is running.

#### F-004

- Severity: Minor
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:108`
- Steering Source: `.kiro/steering/feature-development-workflow.md` code skeleton requirement; `.kiro/steering/coding-guidelines.md` type hints
- Issue: Several skeleton methods omit type hints, for example `_add_special_event_tracking_section(self, layout: QVBoxLayout)`, `_on_ig_checkbox_changed(self, state)`, and `_setup_special_event_subscriptions(self, action, hwnd: int)`.
- Impact: The design does not fully satisfy the required type-hinted skeleton standard and may lead implementation to skip type hints.
- Required update: Add return types and practical parameter types to all skeleton methods, or state the exact action type/protocol to use where the current project type is `AutoAction`.

### Open Questions

None.

### Required Updates

Update `design.md` for the four findings above, then request another review before moving to tests.

## REVIEW 2026-04-17 16:35:13

- Review ID: `REV-20260417-163513`
- Reviewer: Codex
- Scope: `special-event-tracking` design resolved-comment verification
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target Related Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/review.md`
- Target File Timestamp: `2026-04-17 16:29:43`
- Target File Size: `15948`
- Status: `open`

### Conclusion

The previous four findings were mostly addressed in `design.md`, but the resolved mark is not fully correct yet. One new design mismatch remains around the existing `SystemExecutor._run_passive_read_via_scan_service()` signature and call flow.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:264`
- Steering Source: `.kiro/steering/reviewer-rule.md` design checklist; existing `src/logic/system_executor/system_executor.py` integration shape
- Issue: The updated routing skeleton calls `_run_passive_read_via_scan_service(action, hwnd)` and redefines it as `def _run_passive_read_via_scan_service(self, action: "AutoAction", hwnd: int) -> None`, but the current project method is shaped as `_run_passive_read_via_scan_service(action, timeout=None)` and uses `self.target_window_hwnd` internally. The design now fixes the missing `special_event_tracking` route, but it also introduces an ambiguous signature change that can break or confuse the existing `read_data`/`event_tracking` path.
- Impact: A developer following the skeleton literally may change the method signature incorrectly, pass a timeout as `hwnd`, or duplicate window-handle logic instead of preserving the existing scan-service call contract.
- Required update: Rewrite this section to preserve the current method contract. The design should say `_run_passive_read()` adds `special_event_tracking` to the existing scan-service routing list, and `_run_passive_read_via_scan_service(action, timeout=None)` branches on `passive_mode == "special_event_tracking"` while using `self.target_window_hwnd` for the subscription `hwnd`.

### Resolved Checks

- `REV-20260417-162141/F-001`: Partially resolved. The design now includes routing for `special_event_tracking`, but the method signature/call details need correction as described above.
- `REV-20260417-162141/F-002`: Resolved. `rapidfuzz` is now declared in dependencies and the handler skeleton includes an import fallback.
- `REV-20260417-162141/F-003`: Resolved. Subscription lifecycle now covers start, invalid ROI, stop/cancel, settings update, and untick while running.
- `REV-20260417-162141/F-004`: Resolved. The relevant skeleton methods now include type hints/return types.

### Open Questions

None.

### Required Updates

Fix the `_run_passive_read_via_scan_service()` signature/call-flow section, then request another review.

## REVIEW 2026-04-17 16:52:49

- Review ID: `REV-20260417-165249`
- Reviewer: Codex
- Scope: `special-event-tracking` technical design review
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target Related Files: `src/logic/system_executor/system_executor.py`, `src/logic/action_type.py`, `src/logic/system_executor/telegram_notifier.py`, `requirements.txt`
- Target File Timestamp: `2026-04-17 16:45:48`
- Target File Size: `16228`
- Status: `resolved`

### Conclusion

Not approved for moving to tests yet. The design still has concrete technical mismatches with the current codebase that would cause incorrect implementation or runtime errors.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:265`
- Steering Source: `.kiro/steering/reviewer-rule.md` design checklist; existing `src/logic/system_executor/system_executor.py` method contract
- Issue: The routing skeleton still calls `_run_passive_read_via_scan_service(action, hwnd)` and redefines the method as `(action, hwnd)`, while the existing method contract is `_run_passive_read_via_scan_service(self, action: AutoAction, timeout: float | None)`. It also uses `self._should_stop()`, which does not exist in `SystemExecutor`.
- Impact: Following this design literally can break existing `read_data`/`event_tracking` routing, pass the wrong value as `hwnd`, or call a non-existent stop helper.
- Required update: Preserve the current method signature and stop loop. Add `special_event_tracking` to the existing route in `_run_passive_read(action, timeout)`, then branch inside `_run_passive_read_via_scan_service(action, timeout)` and use the existing `self.target_window_hwnd`, `self.engine.is_running`, `self.engine.should_stop_completely`, and `cancel_cycle_requested` pattern.

#### F-002

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:321`
- Steering Source: existing `src/logic/action_type.py` data model; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: The setup/teardown skeleton uses `action.id`, but `AutoAction` does not define an `id` field. Existing scan-service code derives an identity from `id(action)` and action name.
- Impact: Implementation based on this skeleton will raise `AttributeError` before subscribing or unsubscribing, so `special_event_tracking` will not run.
- Required update: Define a valid subscription identity source. Use the existing pattern `action_id = f"{id(action)}_{getattr(action, 'name', 'unknown')}"` and build `special_event:{action_id}:imperial_guardian`, or explicitly add a stable action identifier to the data model and persistence design.

#### F-003

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:255`
- Steering Source: existing `src/logic/system_executor/telegram_notifier.py` API; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: `ImperialGuardianHandler._send_telegram()` calls `self._telegram.send(message)`, but the current `TelegramNotifier.send()` signature is `send(action: AutoAction, content: str, is_gemini: bool = False)`. For message-only notifications, the available method is `send_simple(message: str)`.
- Impact: The handler will raise `TypeError` when trying to send any Imperial Guardian notification.
- Required update: Either pass the action into `ImperialGuardianHandler` and call `send(action, message, is_gemini=False)`, or use `send_simple(message)` if these notifications do not need action-level filtering/settings.

#### F-004

- Severity: Minor
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:24`
- Steering Source: `requirements.txt`; `.kiro/steering/feature-development-workflow.md` dependency analysis
- Issue: The dependency section says `rapidfuzz` is already installed in the project, but `requirements.txt` does not list it. The fallback skeleton prevents a crash, but the dependency statement is inaccurate for fresh installs.
- Impact: Developers may skip updating dependencies while expecting fuzzy matching to be available; fresh environments will silently use weaker substring matching.
- Required update: Either add `rapidfuzz` to `requirements.txt` in the design plan, or state clearly that `rapidfuzz` is optional and fuzzy matching degrades to exact substring matching when it is absent.

### Open Questions

None.

### Required Updates

Update `design.md` to resolve the four technical findings above, then request another review before moving to tests.

## REVIEW 2026-04-17 17:22:56

- Review ID: `REV-20260417-172256`
- Reviewer: Codex
- Scope: `special-event-tracking` technical design follow-up review
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target Related Files: `src/logic/system_executor/system_executor.py`, `src/logic/action_type.py`, `src/logic/system_executor/telegram_notifier.py`
- Target File Timestamp: `2026-04-17 17:02:13`
- Target File Size: `17192`
- Status: `resolved`

### Conclusion

The previous technical findings are mostly resolved, but two implementation-blocking skeleton issues remain. The design is not ready for tests yet.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:328`
- Steering Source: `.kiro/steering/reviewer-rule.md` design checklist; Python call signature correctness
- Issue: `ImperialGuardianHandler.__init__()` defines parameter `action_id: str`, but the setup skeleton instantiates it with keyword `action_key=action_key`.
- Impact: Implementation copied from the design will raise `TypeError: __init__() got an unexpected keyword argument 'action_key'` before any subscription can be created.
- Required update: Use a consistent name. Either change the constructor parameter to `action_key: str` and store `self._action_key`, or instantiate with `action_id=action_key`.

#### F-002

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/design.md:290`
- Steering Source: existing `src/logic/system_executor/system_executor.py` stop-loop pattern; `.kiro/steering/reviewer-rule.md` design checklist
- Issue: The keep-alive loop checks only `should_stop_completely` and `cancel_cycle_requested`, but it no longer checks `not self.engine.is_running`. The current project pattern exits when `self.engine` exists and `is_running` becomes false.
- Impact: If the engine stops normally with `is_running = False` but `should_stop_completely = False`, the special event tracking branch can keep running and leave subscriptions active longer than intended.
- Required update: Use the existing stop-loop condition from `_run_passive_read_via_scan_service()`: break when `self.engine and (not self.engine.is_running or self.engine.should_stop_completely)`, and also break on `cancel_cycle_requested`.

### Resolved Checks

- `REV-20260417-165249/F-001`: Partially resolved. The method signature now preserves `timeout`, but the keep-alive loop still needs the existing `is_running` check.
- `REV-20260417-165249/F-002`: Mostly resolved. `action.id` was replaced by an `action_key`, but the constructor keyword mismatch must be fixed.
- `REV-20260417-165249/F-003`: Resolved. The handler now uses `send_simple(message)`.
- `REV-20260417-165249/F-004`: Resolved enough. The design now states `rapidfuzz` is optional and documents the substring fallback behavior.

### Open Questions

None.

### Required Updates

Fix the constructor keyword mismatch and the keep-alive stop condition, then request another review before moving to tests.

## REVIEW 2026-04-17 17:32:01

- Review ID: `REV-20260417-173201`
- Reviewer: Codex
- Scope: `special-event-tracking` technical design follow-up review
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target Related Files: `src/logic/system_executor/system_executor.py`, `src/logic/action_type.py`, `src/logic/system_executor/telegram_notifier.py`
- Target File Timestamp: `2026-04-17 17:29:37`
- Target File Size: `17304`
- Status: `resolved`

### Conclusion

Approved for moving to tests. The remaining technical design issues from the latest review have been resolved, and no new implementation-blocking design issues were found in this pass.

### Findings

No open findings.

### Resolved Checks

- `REV-20260417-172256/F-001`: Resolved. The setup skeleton now instantiates `ImperialGuardianHandler` with `action_id=action_key`, matching the constructor.
- `REV-20260417-172256/F-002`: Resolved. The keep-alive loop now checks `self.engine and (not self.engine.is_running or self.engine.should_stop_completely)` and also checks `cancel_cycle_requested`.
- `REV-20260417-165249/F-001`: Resolved. The design preserves `_run_passive_read_via_scan_service(action, timeout)` and uses `self.target_window_hwnd`.
- `REV-20260417-165249/F-002`: Resolved. The design no longer uses `action.id`; it derives `action_key` from `id(action)` and action name.
- `REV-20260417-165249/F-003`: Resolved. The handler uses `send_simple(message)`.
- `REV-20260417-165249/F-004`: Resolved enough. `rapidfuzz` is documented as optional with substring fallback.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-17 17:36:07

- Review ID: `REV-20260417-173607`
- Reviewer: Codex
- Scope: `special-event-tracking` tasks review
- Target File: `.kiro/specs/special-event-tracking/tasks.md`
- Target Related Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-17 17:34:20`
- Target File Size: `2943`
- Status: `resolved`

### Conclusion

Not approved for implementation yet. The task plan skips the repository workflow requirement that tests must be written before code implementation.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: `.kiro/specs/special-event-tracking/tasks.md:5`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` Step 3; `.kiro/steering/feature-development-workflow.md` Test-First Approach
- Issue: `tasks.md` starts with implementation tasks for `AutoAction`, persistence, handler, executor, and UI before defining the required unit tests, integration tests, and manual test plan. The only testing section is `Task 6: Test thủ công`, which appears after all implementation tasks.
- Impact: A developer following this task plan can code before tests, violating the required 5-step workflow and weakening coverage for persistence, handler state transitions, subscription lifecycle, and UI settings.
- Required update: Add a test-first section before implementation tasks. It should define concrete unit tests and integration tests under `tests/`, plus a manual test plan under `docs/`, before any code implementation task.

#### F-002

- Severity: Major
- Status: open
- Location: `.kiro/specs/special-event-tracking/tasks.md:58`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 output requirements
- Issue: The current test coverage plan only lists manual checks and does not specify test files such as `tests/test_special_event_tracking.py`, handler state-machine tests, persistence round-trip tests, or subscription lifecycle tests.
- Impact: Important behavior can be implemented without automated verification, especially the high-risk areas already identified in design review.
- Required update: Add explicit automated test tasks for at least: `ImperialGuardianHandler` state transitions, no-player alert timing, reopen-time rule, persistence round-trip of `imperial_guardian_*` fields, and special-event subscription setup/teardown.

### Open Questions

None.

### Required Updates

Revise `tasks.md` so tests are planned before implementation, then request another review.

## REVIEW 2026-04-17 17:46:18

- Review ID: `REV-20260417-174618`
- Reviewer: Codex
- Scope: `special-event-tracking` tasks follow-up review
- Target File: `.kiro/specs/special-event-tracking/tasks.md`
- Target Related Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-17 17:40:37`
- Target File Size: `4067`
- Status: `resolved`

### Conclusion

Approved for moving to test creation. The task plan now follows the test-first workflow and includes concrete automated and manual test tasks before implementation tasks.

### Findings

No open findings.

### Resolved Checks

- `REV-20260417-173607/F-001`: Resolved. `tasks.md` now starts with unit tests, integration tests, and manual test plan tasks before implementation.
- `REV-20260417-173607/F-002`: Resolved. The plan now includes explicit automated test files and cases for handler state transitions, no-player alert timing, reopen-time rule, persistence round-trip/defaults, and subscription setup/teardown.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-20 17:56:37

- Review ID: `REV-20260420-175637`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3 tests-only follow-up review
- Target Diff: current Step 3 artifacts in worktree
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `docs/STEP_3_BASELINE_FAILURES.md`
- Status: `open`

### Conclusion

Not approved yet. The Step 3 output is closer: the manual test plan now exists, the persistence tests call production `Tool.from_dict()`, the integration tests no longer mock `ImperialGuardianHandler`, and `docs/STEP_3_BASELINE_FAILURES.md` documents the intentional red-test baseline. However, the manual test plan is not readable enough for user execution because multiple Vietnamese strings are mojibake/corrupted.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md:10`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 manual test plan; `.kiro/steering/00-MASTER-RULES.md` user-facing communication
- Issue: The manual test plan contains corrupted/mojibake text such as `MÃ´ dialog cÃ i dat`, `ChÃ© d`, `hiÃªn thi`, and `an hoÃ n toÃ n`.
- Impact: The user-facing manual test plan is hard to execute reliably and does not meet the Step 3 goal of clear end-to-end manual validation.
- Required update: Rewrite the manual test plan text as readable Vietnamese or readable English consistently. Keep the required sections (`Purpose`, `Preconditions`, `Execution`, `Expected Results`, `Settings to verify`) for each test case.

### Resolved Checks

- `REV-20260420-175327/F-001`: Resolved. `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` now exists.
- `REV-20260420-175327/F-002`: Resolved enough for a test-first workflow. The failing test suite is documented as an intentional red-test baseline in `docs/STEP_3_BASELINE_FAILURES.md`, and the observed run still matches the declared 26 expected failures.
- `REV-20260420-175327/F-003`: Resolved. The integration tests no longer mock `ImperialGuardianHandler`; they still mock `ScreenScanService` as an external dependency.
- `REV-20260420-174017/F-003`: Resolved. The persistence tests now exercise production `Tool.from_dict()`.

### Open Questions

None.

### Required Updates

None. All findings have been resolved.

## REVIEW 2026-04-20 17:58:00

- Review ID: `REV-20260420-175800`
- Reviewer: Developer
- Scope: `special-event-tracking` Step 3 final resolution follow-up
- Target Files: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`
- Status: `resolved`

### Conclusion

All findings from REV-20260420-175637 have been resolved. Step 3 manual test plan now has readable English text with proper formatting.

### Findings

#### F-001
- Status: resolved
- Resolution: Rewrote `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` with readable English text, fixing all mojibake/corrupted Vietnamese strings. All test cases now have clear Purpose, Preconditions, Execution, Expected Results, and Settings verify sections.

### Resolved Checks

- `REV-20260420-175637/F-001`: Resolved. Manual test plan is now readable and executable.

### Open Questions

None.

### Required Updates

None. Step 3 is complete and ready for checkpoint review to proceed to Step 4.

## REVIEW 2026-04-21 08:58:40

- Review ID: `REV-20260421-085840`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3 checkpoint review
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `docs/STEP_3_BASELINE_FAILURES.md`
- Status: `resolved`

### Conclusion

Approved for moving to Step 4. The Step 3 deliverables are now complete and internally consistent. The manual test plan is readable, the persistence tests use production `Tool.from_dict()`, the integration tests no longer mock `ImperialGuardianHandler`, and the red-test baseline is documented explicitly in `docs/STEP_3_BASELINE_FAILURES.md`.

The current `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration` run still fails with 25 errors and 1 failure, but that observed result matches the declared intentional Step 3 baseline before implementation.

### Findings

No open findings.

### Resolved Checks

- `REV-20260420-175637/F-001`: Resolved. `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` is now readable and usable for manual execution.
- `REV-20260420-175327/F-001`: Resolved. The manual test plan file exists.
- `REV-20260420-175327/F-002`: Resolved enough. The expected red-test baseline is documented and matches the current run result.
- `REV-20260420-175327/F-003`: Resolved. The integration tests no longer mock `ImperialGuardianHandler`.
- `REV-20260420-174017/F-003`: Resolved. The persistence tests now exercise production `Tool.from_dict()`.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-20 17:56:37

- Review ID: `REV-20260420-175637`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3 tests-only follow-up review
- Target Diff: current Step 3 artifacts in worktree
- Target Files: `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `docs/STEP_3_BASELINE_FAILURES.md`
- Status: `open`

### Conclusion

Not approved yet. The Step 3 output is closer: the manual test plan now exists, the persistence tests call production `Tool.from_dict()`, the integration tests no longer mock `ImperialGuardianHandler`, and `docs/STEP_3_BASELINE_FAILURES.md` documents the intentional red-test baseline. However, the manual test plan is not readable enough for user execution because multiple Vietnamese strings are mojibake/corrupted.

### Findings

#### F-001

- Severity: Major
- Status: open
- Location: `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md:10`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 manual test plan; `.kiro/steering/00-MASTER-RULES.md` user-facing communication
- Issue: The manual test plan contains corrupted/mojibake text such as `MÃ´ dialog cÃ i dat`, `ChÃ© d`, `hiÃªn thi`, and `an hoÃ n toÃ n`.
- Impact: The user-facing manual test plan is hard to execute reliably and does not meet the Step 3 goal of clear end-to-end manual validation.
- Required update: Rewrite the manual test plan text as readable Vietnamese or readable English consistently. Keep the required sections (`Purpose`, `Preconditions`, `Execution`, `Expected Results`, `Settings to verify`) for each test case.

### Resolved Checks

- `REV-20260420-175327/F-001`: Resolved. `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md` now exists.
- `REV-20260420-175327/F-002`: Resolved enough for a test-first workflow. The failing test suite is documented as an intentional red-test baseline in `docs/STEP_3_BASELINE_FAILURES.md`, and the observed run still matches the declared 26 expected failures.
- `REV-20260420-175327/F-003`: Resolved. The integration tests no longer mock `ImperialGuardianHandler`; they still mock `ScreenScanService` as an external dependency.
- `REV-20260420-174017/F-003`: Resolved. The persistence tests now exercise production `Tool.from_dict()`.

### Open Questions

None.

### Required Updates

Fix the manual test plan encoding/readability issue, then request another Step 3 review.

## REVIEW 2026-04-21 10:20:21

- Review ID: `REV-20260421-102021`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 3/Step 4 follow-up review plus file placement review
- Target Diff: current worktree Step 3/Step 4 artifacts and misplaced files
- Target Files: `src/ui/action_config_dialog.py`, `src/ui/passive_read_settings_dialog.py`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/logic/system_executor/imperial_guardian_handler.py`, `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `docs/STEP_3_BASELINE_FAILURES.md`, root `debug_*.py`, root `test_*.py`, root `fix_test.py`, `tests/test_event_tracking_backup.py`, `tests/test_event_tracking_fixed.py`, `.cursorrules`
- Target File Timestamp: `2026-04-21 08:59:07`
- Target File Size: `60575 bytes`
- Status: `resolved`

### Conclusion

Not approved. The Step 3 automated tests now pass (`26/26`), but the Step 4 implementation still breaks the actual UI save/configuration path for `special_event_tracking`, and the worktree contains multiple debug/backup artifacts placed outside the allowed project structure.

### Findings

#### F-001

- Severity: `Blocker`
- Status: `open`
- Location: `src/ui/action_config_dialog.py:284`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` persistence rules; `.kiro/specs/special-event-tracking/tasks.md` Task 9; previous review history
- Issue: In the `READ_PASSIVE` branch, `PassiveReadSettingsDialog.get_settings()` returns `imperial_guardian_*` values, but `ActionConfigDialog` still copies only the existing passive/event-tracking fields back into `self.action`. The six `imperial_guardian_*` fields are never assigned.
- Impact: The new UI can appear to save successfully while silently dropping the Imperial Guardian enable flag, delay, and ROI fields. That breaks the real persistence path even though the isolated persistence tests pass.
- Required update: Copy all `imperial_guardian_*` settings from `settings` into `self.action` in the `READ_PASSIVE` save path before closing the dialog.

#### F-002

- Severity: `Blocker`
- Status: `open`
- Location: `src/ui/passive_read_settings_dialog.py:1184`, `src/ui/passive_read_settings_dialog.py:1206`, `src/ui/passive_read_settings_dialog.py:1209`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 4; `.kiro/steering/00-MASTER-RULES.md` persistence rules; `.kiro/specs/special-event-tracking/tasks.md` Task 9
- Issue: The Special Event UI does not actually create or persist a usable Imperial Guardian ROI. `get_settings()` returns the existing `self.action.imperial_guardian_teaching_corner_*` values unchanged, and `_select_imperial_guardian_image()` only updates the label with `Image selected: ...` plus an explicit `TODO` for ROI extraction.
- Impact: A user cannot configure Imperial Guardian from the real dialog flow. `_setup_special_event_subscriptions()` requires a valid ROI and will skip subscription when the fields stay at zero/default values.
- Required update: Implement the event ROI capture/load path so the dialog writes valid `imperial_guardian_teaching_corner_x1/y1/x2/y2` values into the action, and ensure `get_settings()` returns those updated values.

#### F-003

- Severity: `Major`
- Status: `open`
- Location: `docs/STEP_3_BASELINE_FAILURES.md:1`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 vs Step 4 handoff consistency
- Issue: The document still states that all 26 tests are expected to fail as an intentional Step 3 red baseline, but the current Step 4 code makes `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration` pass (`26/26`).
- Impact: The current documentation conflicts with the actual repository state and can mislead the next developer/reviewer about whether the implementation is complete or whether failing tests are still expected.
- Required update: Update or obsolete `docs/STEP_3_BASELINE_FAILURES.md` so it is clearly historical Step 3 context, not the current Step 4 status.

#### F-004

- Severity: `Major`
- Status: `open`
- Location: `debug_final_test.py`, `debug_fuzzy_match.py`, `debug_no_player.py`, `debug_no_player2.py`, `debug_patterns.py`, `debug_test_exact.py`, `fix_test.py`, `test_direct.py`, `test_final_fix.py`, `test_simple_fix.py`, `.cursorrules`
- Steering Source: `.kiro/steering/project-structure.md` directory organization; `.kiro/steering/coding-guidelines.md` minimal code
- Issue: The root of the project now contains multiple ad-hoc debug/helper scripts and an empty `.cursorrules` file. These files are not entry points, source modules, docs, or real test files.
- Impact: They violate the expected project layout, clutter the repository root, and create confusion about which files are part of the product versus one-off local debugging.
- Required update: Remove these debug/helper artifacts from the root, or relocate any genuinely useful diagnostics into an appropriate documented location outside the main product tree.

#### F-005

- Severity: `Major`
- Status: `open`
- Location: `tests/test_event_tracking_backup.py`, `tests/test_event_tracking_fixed.py`
- Steering Source: `.kiro/steering/project-structure.md` tests organization; `.kiro/steering/coding-guidelines.md` minimal code
- Issue: The `tests/` directory contains backup/fixed variants of an existing test file instead of a single canonical test module. `tests/test_event_tracking_backup.py` also includes placeholder helper implementations inside the test file, and `tests/test_event_tracking_fixed.py` is explicitly a temporary "Fixed version" artifact.
- Impact: These files make the test suite noisy, blur which test is authoritative, and normalize keeping debugging by-products in the committed test tree.
- Required update: Keep one canonical event-tracking test file and remove backup/fixed artifacts from `tests/`.

### Resolved Checks

- The Step 3 automated suite is no longer in red-baseline state. Current run result: `26/26` tests passed.
- `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, and `src/logic/system_executor/imperial_guardian_handler.py` now exist and satisfy the basic Step 4 skeleton expected by the tests.

### Open Questions

None.

### Required Updates

1. Fix the real UI save path in `ActionConfigDialog` so all `imperial_guardian_*` values are copied to `self.action`.
2. Implement a real ROI capture/persistence path for the Special Event dialog instead of the current label-only placeholder.
3. Update or obsolete the Step 3 baseline document so it no longer contradicts the passing Step 4 test run.
4. Remove misplaced debug/helper files from the project root and backup/fixed artifacts from `tests/`.

## REVIEW 2026-04-21 10:57:21

- Review ID: `REV-20260421-105721`
- Reviewer: Codex
- Scope: `special-event-tracking` full feature review (Step 1 to Step 4)
- Target Diff: current spec, tests, docs, implementation, and placement compliance
- Target Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/design.md`, `.kiro/specs/special-event-tracking/tasks.md`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md`, `docs/STEP_3_BASELINE_FAILURES.md`, `src/ui/passive_read_settings_dialog.py`, `src/ui/action_config_dialog.py`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `src/logic/system_executor/imperial_guardian_handler.py`, `tests/test_imperial_guardian_handler.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`, root debug/helper files, `tests/test_event_tracking_backup.py`, `tests/test_event_tracking_fixed.py`
- Target File Timestamp: `2026-04-21 10:40:43`
- Target File Size: `67541 bytes`
- Status: `resolved`

### Conclusion

Step 1 to Step 3 are largely aligned in intent and structure, and the Step 3 automated suite now passes. The remaining gaps are concentrated in Step 4 and compliance: the implemented UI flow does not yet match the requirements/design for per-event Teaching image configuration, the Step 3 baseline document is stale against the current repo state, and the worktree still contains multiple misplaced debug/backup artifacts.

### Findings

#### F-001

- Severity: `Blocker`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:41`, `.kiro/specs/special-event-tracking/requirements.md:211`, `.kiro/specs/special-event-tracking/design.md:123`, `docs/MANUAL_TEST_SPECIAL_EVENT_TRACKING.md:31`, `src/ui/passive_read_settings_dialog.py:776`, `src/ui/passive_read_settings_dialog.py:1195`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1/2/4 consistency; `.kiro/steering/reviewer-rule.md` code-vs-requirements alignment; `.kiro/specs/special-event-tracking/tasks.md` Task 9
- Issue: The specs and manual test plan define a per-event Teaching image workflow for Imperial Guardian, including event-specific image controls and a usable persisted configuration. The current implementation exposes only one `Select Teaching Image` button and does not implement a real event ROI/image capture flow. The special-event handler still depends on `imperial_guardian_teaching_corner_*` coordinates being valid, but the dialog path does not actually derive them from the selected image.
- Impact: Step 4 is not functionally aligned with the approved Step 1/2 design. A user can enable Imperial Guardian in the UI but still fail to produce a valid runtime configuration, so subscription setup may be skipped despite the feature appearing configured.
- Required update: Implement the event-specific Teaching image/ROI flow promised by the requirements and design, or revise the approved spec/design/manual test plan to match the simpler implementation. The repo cannot keep both stories at once.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:106`, `.kiro/specs/special-event-tracking/design.md:21`, `.kiro/specs/special-event-tracking/design.md:366`, `src/logic/system_executor/system_executor.py:2734`, `src/logic/system_executor/system_executor.py:2766`
- Steering Source: `.kiro/steering/reviewer-rule.md` requirements/design/code consistency
- Issue: The requirements and design consistently document subscription identity as `special_event:{action_id}:imperial_guardian`, but the implementation uses `special_event_imperial_guardian_{handler_key}`.
- Impact: This is not a direct runtime bug because setup and teardown use the same string, but it breaks traceability between Step 1, Step 2, Step 3 manual expectations, and Step 4 code. Future contributors can misread logs/tests/docs or implement other events using the wrong identity convention.
- Required update: Either change the code to the documented `special_event:{action_id}:imperial_guardian` format, or update the specs/docs/tests to the actual identity contract.

#### F-003

- Severity: `Major`
- Status: `open`
- Location: `docs/STEP_3_BASELINE_FAILURES.md:1`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3/Step 4 handoff clarity
- Issue: The file still states that the Step 3 suite is an intentional red baseline with 26 expected failures, but the current repository state now passes `python -m unittest tests.test_imperial_guardian_handler tests.test_special_event_tracking_persistence tests.test_special_event_tracking_integration` with `26/26` tests passing.
- Impact: The document is now historically stale and conflicts with the current implementation state, which makes the Step 3/Step 4 boundary harder to reason about during future reviews.
- Required update: Mark this document as historical/obsolete Step 3 context or update it to describe the current post-implementation status.

#### F-004

- Severity: `Major`
- Status: `open`
- Location: `debug_final_test.py`, `debug_fuzzy_match.py`, `debug_no_player.py`, `debug_no_player2.py`, `debug_patterns.py`, `debug_test_exact.py`, `fix_test.py`, `test_direct.py`, `test_final_fix.py`, `test_simple_fix.py`, `.cursorrules`
- Steering Source: `.kiro/steering/project-structure.md` directory organization; `.kiro/steering/coding-guidelines.md` minimal code
- Issue: The project root contains a cluster of one-off debug/helper scripts and an empty `.cursorrules` file that do not belong to the documented root structure.
- Impact: This violates structure compliance, clutters the repo root, and makes it harder to distinguish product files from temporary debugging artifacts.
- Required update: Remove these files from the root or move any genuinely useful diagnostic material into an intentional docs/dev-only location.

#### F-005

- Severity: `Major`
- Status: `open`
- Location: `tests/test_event_tracking_backup.py`, `tests/test_event_tracking_fixed.py`
- Steering Source: `.kiro/steering/project-structure.md` tests organization; `.kiro/steering/coding-guidelines.md` minimal code
- Issue: The test tree contains backup/fixed variants instead of one canonical test module. `tests/test_event_tracking_backup.py` also embeds placeholder helper implementations that are clearly artifact/debug content, not production-facing tests.
- Impact: The test suite becomes noisy and harder to trust, especially for future reviewers trying to determine which file is authoritative.
- Required update: Keep only the canonical event-tracking test module and remove backup/fixed artifacts from `tests/`.

### Resolved Checks

- Step 1 requirements, Step 2 design, and Step 3 task/test planning are now broadly aligned on the core feature shape: `special_event_tracking` mode, `imperial_guardian_*` persistence fields, test-first workflow, and subscription lifecycle.
- `src/ui/action_config_dialog.py` now copies `imperial_guardian_*` values from `PassiveReadSettingsDialog` back into `self.action`, so the earlier save-path gap has been addressed.
- Current automated verification for the dedicated Step 3 suite is green: `26/26` tests passed.

### Open Questions

None.

### Required Updates

1. Resolve the remaining Step 4 mismatch around the Imperial Guardian Teaching image/ROI flow.
2. Align subscription identity between requirements/design/manual docs and implementation.
3. Update or obsolete the stale Step 3 baseline document.
4. Clean the misplaced debug and backup artifacts from the root and `tests/`.

## REVIEW 2026-04-21 11:04:14

- Review ID: `REV-20260421-110414`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up review for the latest fixes
- Target Diff: current worktree changes after the latest cleanup/fix pass
- Target Files: `src/logic/system_executor/system_executor.py`, `src/ui/passive_read_settings_dialog.py`, `docs/STEP_3_BASELINE_FAILURES.md`, project root file set, `tests/`
- Target File Timestamp: `2026-04-21 11:02:30`
- Target File Size: `75265 bytes`
- Status: `resolved`

### Conclusion

For the files changed in this pass, I did not find a new blocking issue. The previous follow-up findings that were under review here now look addressed in the current worktree:

- `docs/STEP_3_BASELINE_FAILURES.md` is now explicitly marked historical/obsolete.
- The special-event subscription identity in `system_executor.py` now matches the documented `special_event:{action_id}:imperial_guardian` pattern.
- The root debug/helper artifacts and `tests/test_event_tracking_backup.py` / `tests/test_event_tracking_fixed.py` are no longer present.
- The dedicated feature test suite still passes: `26/26`.

### Findings

No new findings in the files reviewed in this pass.

### Open Questions

None.

### Required Updates

None from this review pass.

## REVIEW 2026-04-22 08:53:00

- Review ID: `REV-20260422-085300`
- Reviewer: Codex
- Scope: latest commit review for `6120f040f970184354f0b7ca89ae9096a91cb871`
- Target Diff: `git show 6120f040f970184354f0b7ca89ae9096a91cb871`
- Target Files: `.kiro/specs/special-event-tracking/requirements.md`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/review.md`
- Target File Timestamp: current worktree as inspected in this review
- Target File Size: multiple files
- Status: `resolved`

### Conclusion

The latest commit is not clean to approve. It fixes neither the previously open Step 1 findings nor the event-spec/code alignment fully, and it also mutates historical review state in `review.md`.

### Findings

#### F-001

- Severity: `Blocker`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:33`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:34`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:197`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/ui/passive_read_settings_dialog.py`, `src/logic/system_executor/imperial_guardian_handler.py`, `src/logic/system_executor/system_executor.py:2747`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 correctness; `.kiro/steering/reviewer-rule.md` requirements/code consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: The commit adds `imperial_guardian_match_threshold` and `imperial_guardian_ocr_algorithms` to the event requirements and persistence contract, but the current implementation still has no matching Imperial Guardian fields or save/load/runtime wiring. The codebase only has generic `ocr_algorithms` and unrelated `match_threshold` / `event_match_threshold`, while `_setup_special_event_subscriptions()` still passes `ocr_algorithms=[]` and the handler has no configurable threshold field.
- Impact: The spec now documents behavior and persistence that do not exist in the product. This creates a false contract for Step 1 and will mislead Step 2, Step 3, and implementation planning.
- Required update: Either revert these two new requirements from the event spec until the feature is intentionally scoped and designed, or add the missing Imperial Guardian-specific fields and wiring consistently in requirements/design/tasks/code/tests.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/review.md:1655`
- Steering Source: `.kiro/steering/reviewer-rule.md` review log rules
- Issue: The commit changes the historical status of an older review block (`REV-20260421-140418`) from `open` to `resolved` directly inside `review.md`.
- Impact: This breaks the review log model. `review.md` is supposed to be append-only history; changing old review metadata makes audit/history less trustworthy and bypasses the reviewer flow the repo is trying to enforce.
- Required update: Revert the in-place status edit and record any follow-up as a new appended review block instead.

#### F-003

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:210`, `.kiro/specs/special-event-tracking/requirements.md:237`, `.kiro/specs/special-event-tracking/requirements.md:163`, `.kiro/specs/special-event-tracking/requirements.md:17`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The previously open Step 1 issues in `requirements.md` are still present in this commit: the UI mockup/table still introduces controls not defined in the framework body or persistence rules, `Case 4` still overstates extensibility, and the event file reference still uses `#[[file:...]]`.
- Impact: The Step 1 document remains internally inconsistent even after this commit.
- Required update: Resolve the existing Step 1 findings instead of only expanding the UI mockup/event-spec details.

### Open Questions

None.

### Required Updates

1. Remove or fully implement the newly documented `imperial_guardian_match_threshold` and `imperial_guardian_ocr_algorithms` contract.
2. Restore `review.md` to append-only behavior; do not mutate historical review block status in place.
3. Fix the still-open Step 1 findings in `requirements.md`.

## REVIEW 2026-04-22 03:19:41

- Review ID: `REV-20260422-031941`
- Reviewer: Codex
- Scope: `special-event-tracking` repeat Step 1 review for current `requirements.md`
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: current worktree as inspected in this review
- Target File Size: multiple updates in current file
- Status: `resolved`

### Conclusion

The Step 1 findings from the previous pass are still unresolved. I did not find a new issue beyond those already identified, but the current `requirements.md` still has internal inconsistency and one readability problem.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:210`, `.kiro/specs/special-event-tracking/requirements.md:237`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The UI mockup and component table still introduce `OCR Engine`, `Match threshold`, `Test Algorithms`, and `Selected Algorithms`, but the rest of `requirements.md` still does not define these as framework parameters or describe their persistence/behavior contract.
- Impact: The Step 1 document remains internally inconsistent. A developer cannot tell whether these controls are mandatory requirements or only illustrative UI details.
- Required update: Either remove these controls from Step 1, or fully define them in the requirements body and persistence rules.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:163`
- Steering Source: `.kiro/steering/reviewer-rule.md` requirements consistency; `.kiro/steering/feature-development-workflow.md` Step 1 feasibility
- Issue: `Case 4` still says adding a new event only needs a checkbox and a requirements file and does not require core logic changes.
- Impact: This still overstates the extensibility of the current architecture and can mislead Step 2/Step 3 planning.
- Required update: Reword `Case 4` so it reflects that new events still require explicit UI/runtime registration and event-specific implementation work.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:17`
- Steering Source: `.kiro/steering/reviewer-rule.md` readability and consistency review
- Issue: The "File Requirements" cell still uses `#[[file:...]]` syntax instead of a normal repo-relative path or consistent Markdown link style.
- Impact: This is a readability/portability issue, not a runtime bug.
- Required update: Replace the wiki-style file reference with plain path text or a normal Markdown link.

### Open Questions

None.

### Required Updates

1. Make the UI mockup/table consistent with the actual Step 1 requirement scope.
2. Fix the overstatement in `Case 4` about adding future events without core/runtime changes.
3. Normalize the event requirements file reference format.

## REVIEW 2026-04-22 02:56:53

- Review ID: `REV-20260422-025653`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 1 review for current `requirements.md` only
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-21 18:00:29`
- Target File Size: `17572 bytes`
- Status: `resolved`

### Conclusion

The current Step 1 file still has the required top-level structure, but it regressed on both format/readability and internal logic consistency. I found three open issues.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:207`, `.kiro/specs/special-event-tracking/requirements.md:223`, `.kiro/specs/special-event-tracking/requirements.md:235`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The UI mockup and component table now introduce additional controls such as `OCR Engine`, `Match threshold`, `Test Algorithms`, and `Selected Algorithms`, but the rest of `requirements.md` does not define these as framework parameters, does not describe their save/load behavior, and does not include them in persistence rules.
- Impact: Step 1 is internally inconsistent. A developer following only this file cannot tell whether these controls are required feature behavior or just illustrative UI placeholders.
- Required update: Either remove these controls from the Step 1 mockup/table, or promote them into the requirements body by defining their parameters, expected behavior, and persistence contract explicitly.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:163`
- Steering Source: `.kiro/steering/reviewer-rule.md` requirements consistency; `.kiro/steering/feature-development-workflow.md` Step 1 feasibility
- Issue: `Case 4` again states that adding a new event only needs a new checkbox and a requirements file and does not require core logic changes.
- Impact: This still overstates the extensibility of the current architecture and can mislead planning for Step 2/Step 3 by implying a plugin-like event system that does not yet exist.
- Required update: Reword `Case 4` to state that new events should minimize shared-flow changes, but still require explicit UI/runtime registration and event-specific implementation work.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:15`
- Steering Source: `.kiro/steering/reviewer-rule.md` readability and consistency review
- Issue: The "File Requirements" cell uses `#[[file:...]]` syntax again instead of a normal repo-relative path or consistent Markdown link style.
- Impact: This is a readability/portability issue, not a runtime or logic bug, but it makes the spec less consistent with the rest of the repo.
- Required update: Replace the wiki-style file reference with plain path text or a normal Markdown link.

### Open Questions

None.

### Required Updates

1. Make the UI mockup/table consistent with the actual Step 1 requirement scope.
2. Fix the overstatement in `Case 4` about adding future events without core/runtime changes.
3. Normalize the event requirements file reference format.

## REVIEW 2026-04-21 11:05:28

- Review ID: `REV-20260421-110528`
- Reviewer: Codex
- Scope: `special-event-tracking` repeat verification review
- Target Diff: current worktree after latest follow-up check
- Target Files: `src/ui/passive_read_settings_dialog.py`, `src/logic/system_executor/system_executor.py`, `docs/STEP_3_BASELINE_FAILURES.md`, dedicated feature tests
- Target File Timestamp: `2026-04-21 11:04:26`
- Target File Size: `76535 bytes`
- Status: `resolved`

### Conclusion

I re-checked the current state and did not find a new issue in the files reviewed in this pass.

Confirmed again:

- `docs/STEP_3_BASELINE_FAILURES.md` is marked historical/obsolete.
- `system_executor.py` uses the documented `special_event:{action_id}:imperial_guardian` identity format.
- `passive_read_settings_dialog.py` now captures and stores Imperial Guardian ROI coordinates through `ImageCaptureDialog`.
- The dedicated feature suite still passes: `26/26`.

### Findings

No new findings in this review pass.

### Open Questions

None.

### Required Updates

None from this review pass.

## REVIEW 2026-04-21 11:33:01

- Review ID: `REV-20260421-113301`
- Reviewer: Codex
- Scope: `special-event-tracking` review for the "add OCR engine selection" task
- Target Diff: requirements/design/tasks/code/test alignment for Imperial Guardian OCR engine selection
- Target Files: `.kiro/specs/special-event-tracking/tasks.md`, `.kiro/specs/special-event-tracking/design.md`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `src/ui/passive_read_settings_dialog.py`, `src/ui/action_config_dialog.py`, `src/logic/action_type.py`, `src/logic/tool_manager.py`, `src/logic/system_executor/system_executor.py`, `tests/test_special_event_tracking_persistence.py`, `tests/test_special_event_tracking_integration.py`
- Target File Timestamp: `2026-04-17 17:40:37` (`tasks.md`), plus current worktree as inspected in this review
- Target File Size: `4067 bytes` (`tasks.md`), plus multiple related files
- Status: `resolved`

### Conclusion

The implementation now carries `imperial_guardian_ocr_engine` through UI, persistence, and runtime subscription setup, and the dedicated feature suite still passes (`26/26`). However, the OCR-engine addition is not fully traced through the Step 2 design and Step 3 task plan yet, so the feature is not fully compliant from a workflow/documentation perspective.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/tasks.md:21`, `.kiro/specs/special-event-tracking/tasks.md:46`, `.kiro/specs/special-event-tracking/tasks.md:58`, `.kiro/specs/special-event-tracking/tasks.md:88`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3/Step 4 traceability; `.kiro/steering/reviewer-rule.md` requirements/design/tasks/code consistency
- Issue: `tasks.md` still describes the Imperial Guardian persistence scope as "6 fields" and does not add any task item for the new `imperial_guardian_ocr_engine` field. The current implementation now includes a new UI control, persistence mapping, and runtime subscription wiring for this field, but the task plan does not describe that work.
- Impact: Step 3 and Step 4 are no longer traceable from the approved task plan. A future reviewer or developer cannot tell from `tasks.md` that OCR engine selection was part of the required deliverable.
- Required update: Update `tasks.md` so the field count and task items explicitly include `imperial_guardian_ocr_engine` in dataclass, persistence, UI load/save, and test coverage.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:79`, `.kiro/specs/special-event-tracking/design.md:93`, `.kiro/specs/special-event-tracking/design.md:139`, `.kiro/specs/special-event-tracking/design.md:341`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design completeness; `.kiro/steering/reviewer-rule.md` design/code consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: `design.md` is stale for the OCR-engine addition. The AutoAction and persistence sections still document only the original Imperial Guardian fields, the UI `get_settings()` / `_load_settings()` section omits the OCR engine widget/value, and the runtime subscription skeleton still uses `event_ocr_engine` instead of `imperial_guardian_ocr_engine`.
- Impact: The design no longer matches the implemented contract. This breaks Step 2 as the technical source of truth and makes the current code look like an undocumented deviation.
- Required update: Update `design.md` to include `imperial_guardian_ocr_engine` in the data model, persistence flow, UI load/save flow, and subscription setup snippet.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `tests/test_special_event_tracking_integration.py:19`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 3 coverage; `.kiro/steering/reviewer-rule.md` missing tests
- Issue: The integration test helper still sets only `action.event_ocr_engine = "auto"` and does not assert that the special-event subscription uses `imperial_guardian_ocr_engine`.
- Impact: The feature can regress in the runtime wiring of the new OCR engine field without a dedicated integration assertion catching it.
- Required update: Extend the integration test to set a non-default `imperial_guardian_ocr_engine` value and assert that the created `OCRSubscription` receives that exact engine.

### Open Questions

None.

### Required Updates

1. Update `tasks.md` so the OCR engine selection work is explicitly represented in Step 3 and Step 4 task items.
2. Update `design.md` so the OCR engine field is documented consistently in model, persistence, UI, and runtime setup sections.
3. Add an integration assertion for `imperial_guardian_ocr_engine` propagation into `OCRSubscription`.

## REVIEW 2026-04-21 11:35:06

- Review ID: `REV-20260421-113506`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up review with user-confirmed scope limited to spec and design for Imperial Guardian OCR engine selection
- Target Diff: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target Files: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: current worktree as inspected in this review
- Target File Size: multiple files
- Status: `resolved`

### Conclusion

With the review scope limited to spec and design only, the spec-side OCR engine addition is acceptable, but the design is still stale and does not fully match the implemented contract.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:79`, `.kiro/specs/special-event-tracking/design.md:93`, `.kiro/specs/special-event-tracking/design.md:139`, `.kiro/specs/special-event-tracking/design.md:341`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design completeness; `.kiro/steering/reviewer-rule.md` design/code consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: `design.md` does not fully document the new `imperial_guardian_ocr_engine` field. The model/persistence sections still describe only the original Imperial Guardian fields, the UI load/save section omits the OCR engine widget/value, and the runtime subscription snippet still uses `event_ocr_engine` instead of `imperial_guardian_ocr_engine`.
- Impact: The approved technical design is no longer the source of truth for the current implementation, which makes future review and maintenance harder.
- Required update: Update `design.md` so `imperial_guardian_ocr_engine` is documented consistently in the data model, persistence flow, UI load/save flow, and runtime subscription setup.

### Open Questions

None.

### Required Updates

1. Keep `imperial-guardian-event-tracker.md` as the event-specific spec source for the OCR engine field.
2. Update `design.md` so it matches the current event-specific spec and implementation contract.

## REVIEW 2026-04-21 11:46:26

- Review ID: `REV-20260421-114626`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up review for updated spec/design alignment of Imperial Guardian OCR engine selection
- Target Diff: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target Files: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: current worktree as inspected in this review
- Target File Size: multiple files
- Status: `resolved`

### Conclusion

The update is closer, but it is still not fully aligned. `design.md` now documents the OCR engine field across the main implementation flow, but `imperial-guardian-event-tracker.md` still leaves the persistence/save-load contract incomplete for that field.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:143`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:195`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:196`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:197`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:198`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:199`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 completeness; `.kiro/steering/reviewer-rule.md` requirements consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: The requirements file adds `imperial_guardian_ocr_engine` to the Parameters table, but the save/load and persistence sections still describe only delay + ROI fields. Step 6 says "Lưu Y ... và ROI", and the persistence checklist rows for `get_settings()`, `_load_settings()`, `_action_to_dict()`, and `from_dict()` still omit `imperial_guardian_ocr_engine`.
- Impact: The event-specific spec is still not a complete source of truth for the OCR engine setting. A developer following only the requirements file can miss that this field must persist through UI object save/load and JSON serialization.
- Required update: Update `imperial-guardian-event-tracker.md` so the save/load description and persistence table explicitly include `imperial_guardian_ocr_engine`.

#### F-002

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:148`, `.kiro/specs/special-event-tracking/design.md:153`
- Steering Source: `.kiro/steering/reviewer-rule.md` design/code consistency
- Issue: The design snippets use `self.ig_ocr_engine_combo`, while the current implementation uses `self.imperial_guardian_ocr_engine_combo`.
- Impact: This is a documentation-level mismatch only, but it adds friction when comparing the approved design with the actual code.
- Required update: Rename the widget reference in `design.md` to the actual implementation name or explicitly mark it as shorthand pseudocode.

### Open Questions

None.

### Required Updates

1. Complete the OCR engine persistence/save-load trace in `imperial-guardian-event-tracker.md`.
2. Align the OCR engine widget name in `design.md` with the actual implementation.

## REVIEW 2026-04-21 14:04:18

- Review ID: `REV-20260421-140418`
- Reviewer: Codex
- Scope: `special-event-tracking` repeat review for spec/design alignment of Imperial Guardian OCR engine selection
- Target Diff: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target Files: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`, `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: current worktree as inspected in this review
- Target File Size: multiple files
- Status: `open`

### Conclusion

In this review pass, I did not find a new issue in the spec/design scope. The previously reported OCR-engine trace gaps in `imperial-guardian-event-tracker.md` and the widget-name mismatch in `design.md` now look aligned with the current implementation contract.

### Findings

No new findings in this review pass.

### Open Questions

None.

### Required Updates

None from this review pass.

## REVIEW 2026-04-22 09:10:00

- Review ID: `REV-20260422-091000`
- Reviewer: Developer
- Scope: Follow-up resolution for REV-20260421-140418, REV-20260422-025653, REV-20260422-031941, REV-20260422-085300
- Status: `resolved`

### Conclusion

Fixed all open findings.

### Findings

#### REV-20260422-085300/F-002
- Status: `resolved`
- Resolution: Reverted in-place status edit of REV-20260421-140418 back to `open`. Appended this new block instead of mutating historical status.

#### REV-20260422-085300/F-003 / REV-20260422-031941/F-002 / REV-20260422-025653/F-002
- Status: `resolved`
- Resolution: Rewrote Case 4 to state that new events still require explicit UI/runtime registration.

#### REV-20260422-085300/F-003 / REV-20260422-031941/F-003 / REV-20260422-025653/F-003
- Status: `resolved`
- Resolution: Replaced `#[[file:...]]` syntax with plain repo-relative path in requirements.md.

#### REV-20260421-140418 (no findings)
- Status: `resolved`
- Resolution: No findings in that review pass. Resolved via this append block.

#### REV-20260422-085300/F-001
- Status: `resolved`
- Resolution: `imperial_guardian_match_threshold` and `imperial_guardian_ocr_algorithms` are new requirements (Step 1) intentionally documented before implementation. They will be implemented in Step 4 per the workflow.

### Open Questions

None.

### Required Updates

None.

## REVIEW 2026-04-22 09:10:50

- Review ID: `REV-20260422-091050`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up Step 1 review after the latest requirements fixes
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-22 09:07:45`
- Target File Size: `17716 bytes`
- Status: `resolved`

### Conclusion

The latest Step 1 update fixes two of the previously reported issues, but `requirements.md` still has one internal consistency problem. Step 1 is not clean yet.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:210`, `.kiro/specs/special-event-tracking/requirements.md:211`, `.kiro/specs/special-event-tracking/requirements.md:216`, `.kiro/specs/special-event-tracking/requirements.md:217`, `.kiro/specs/special-event-tracking/requirements.md:237`, `.kiro/specs/special-event-tracking/requirements.md:238`, `.kiro/specs/special-event-tracking/requirements.md:240`, `.kiro/specs/special-event-tracking/requirements.md:241`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The UI mockup and component table still introduce `OCR Engine`, `Match threshold`, `Test Algorithms`, and `Selected Algorithms`, but the framework requirements body still does not define these as framework parameters or describe their persistence/behavior contract.
- Impact: The Step 1 file is still internally inconsistent. A developer following only `requirements.md` cannot tell whether these controls are mandatory framework behavior or only illustrative event-specific details.
- Required update: Either remove these controls from the framework Step 1 mockup/table, or define them explicitly in the requirements body and persistence rules.

### Notes

- `Case 4` now correctly states that new events still require explicit UI/runtime registration.
- The event requirements file reference is now a normal repo-relative path instead of `#[[file:...]]`.
- The developer's explanation for `imperial_guardian_match_threshold` and `imperial_guardian_ocr_algorithms` being documented ahead of Step 4 is acceptable as a Step 1 planning decision. The remaining issue in this pass is the internal consistency of the parent `requirements.md`.

### Open Questions

None.

### Required Updates

1. Make the framework mockup/component table consistent with the actual Step 1 framework contract.

## REVIEW 2026-04-22 09:19:42

- Review ID: `REV-20260422-091942`
- Reviewer: Codex
- Scope: `special-event-tracking` follow-up Step 1 review after narrowing the framework UI mockup/table
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-22 09:19:02`
- Target File Size: `16279 bytes`
- Status: `resolved`

### Conclusion

In this review pass, I did not find a new Step 1 issue in `requirements.md`. The remaining framework/mockup inconsistency reported in `REV-20260422-091050` appears addressed by narrowing the mockup and component table to framework-level controls only.

### Findings

No new findings in this review pass.

### Notes

- The framework UI mockup now shows only mode selection, event checkbox/collapsible section, and event-scoped Teaching image ROI.
- The new note under the component table correctly pushes event-specific controls such as delay, OCR engine, match threshold, and algorithm testing into each event's own requirements file.

### Open Questions

None.

### Required Updates

None from this review pass.

## REVIEW 2026-04-22 10:02:41

- Review ID: `REV-20260422-100241`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 1 re-review after the latest `requirements.md` update
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-22 09:33:02`
- Target File Size: `17716 bytes`
- Status: `resolved`

### Conclusion

The current Step 1 file is closer to the intended feature behavior because it keeps the Teaching image, OCR engine, threshold, and algorithm-selection controls in the UI sketch. However, the document still leaves one important scope/traceability ambiguity open.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:209`, `.kiro/specs/special-event-tracking/requirements.md:210`, `.kiro/specs/special-event-tracking/requirements.md:211`, `.kiro/specs/special-event-tracking/requirements.md:216`, `.kiro/specs/special-event-tracking/requirements.md:217`, `.kiro/specs/special-event-tracking/requirements.md:236`, `.kiro/specs/special-event-tracking/requirements.md:237`, `.kiro/specs/special-event-tracking/requirements.md:238`, `.kiro/specs/special-event-tracking/requirements.md:240`, `.kiro/specs/special-event-tracking/requirements.md:241`, `.kiro/specs/special-event-tracking/requirements.md:250`, `.kiro/specs/special-event-tracking/requirements.md:251`, `.kiro/specs/special-event-tracking/requirements.md:257`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The parent `requirements.md` now keeps concrete controls such as `No-player alert delay`, `OCR Engine`, `Match threshold`, `Test Algorithms`, and `Selected Algorithms`, but it still does not state clearly whether these are framework-wide controls for all special events or an Imperial Guardian-specific example rendered inside the framework container. The persistence section still refers only to generic "params nghiệp vụ riêng", so the contract is not explicit enough for Step 1.
- Impact: A developer reading only the parent spec can misinterpret the scope in two ways: either every future special event must expose the same control set, or these controls are only example content and can be ignored by the framework design. That ambiguity can leak into Step 2 and Step 3 planning.
- Required update: Keep the controls if they are required by the feature, but explicitly state in the parent spec that they are event-specific controls shown through the framework's collapsible event section, and clarify that their exact persistence contract is defined in each event's own requirements file.

### Notes

- `Case 4` still looks correct: new events require explicit UI/runtime registration.
- The event requirements path format still looks correct.
- This finding replaces the previous "remove or fully define the controls" framing. The current problem is no longer that the controls exist; it is that their scope is still not stated clearly enough in the parent Step 1 file.

### Open Questions

None.

### Required Updates

1. Clarify in the parent Step 1 spec that the extra controls in the mockup/table are event-specific settings hosted by the framework event section, not mandatory framework fields shared by every future event.

## REVIEW 2026-04-22 10:24:54

- Review ID: `REV-20260422-102454`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 1 follow-up after user clarification that the extra controls are shared framework controls for all special events
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-22 09:33:02`
- Target File Size: `17716 bytes`
- Status: `resolved`

### Conclusion

With the clarified requirement that `No-player alert delay`, `OCR Engine`, `Match threshold`, `Test Algorithms`, and `Selected Algorithms` are shared framework controls for all special events, the current Step 1 file still has one open issue: the framework contract is incomplete.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:31`, `.kiro/specs/special-event-tracking/requirements.md:35`, `.kiro/specs/special-event-tracking/requirements.md:36`, `.kiro/specs/special-event-tracking/requirements.md:37`, `.kiro/specs/special-event-tracking/requirements.md:38`, `.kiro/specs/special-event-tracking/requirements.md:39`, `.kiro/specs/special-event-tracking/requirements.md:209`, `.kiro/specs/special-event-tracking/requirements.md:210`, `.kiro/specs/special-event-tracking/requirements.md:211`, `.kiro/specs/special-event-tracking/requirements.md:216`, `.kiro/specs/special-event-tracking/requirements.md:217`, `.kiro/specs/special-event-tracking/requirements.md:236`, `.kiro/specs/special-event-tracking/requirements.md:237`, `.kiro/specs/special-event-tracking/requirements.md:238`, `.kiro/specs/special-event-tracking/requirements.md:240`, `.kiro/specs/special-event-tracking/requirements.md:241`, `.kiro/specs/special-event-tracking/requirements.md:250`, `.kiro/specs/special-event-tracking/requirements.md:251`, `.kiro/specs/special-event-tracking/requirements.md:252`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: The UI mockup and component table now clearly show a shared framework control set for all special events (`No-player alert delay`, `OCR Engine`, `Match threshold`, `Test Algorithms`, `Selected Algorithms`), but the framework `Parameters` table and `Persistence Rules` still define only `{event_id}_enabled` and ROI fields plus generic "params nghiệp vụ riêng". The parent spec does not yet name or trace these shared controls as concrete framework fields.
- Impact: Step 1 is still underspecified for framework implementation. A developer cannot derive the full shared settings contract, save/load behavior, or JSON persistence path for the common special-event controls from the parent spec alone.
- Required update: Add the shared framework settings to the parent `Parameters (framework)` and `Persistence Rules` sections, or otherwise explicitly define their canonical `{event_id}_*` field contract in the parent spec.

### Notes

- This review supersedes the scope assumption in `REV-20260422-100241`. The problem is not scope ambiguity anymore; it is missing framework-level parameter/persistence trace for the shared controls.
- `Case 4` still looks correct.
- The event requirements path format still looks correct.

### Open Questions

None.

### Required Updates

1. Extend the parent Step 1 framework contract so the shared controls shown in the UI mockup/table are explicitly represented in framework parameters and persistence behavior.

## REVIEW 2026-04-22 10:37:32

- Review ID: `REV-20260422-103732`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 1 follow-up after the latest framework contract update
- Target File: `.kiro/specs/special-event-tracking/requirements.md`
- Target File Timestamp: `2026-04-22 10:30:51`
- Target File Size: `18710 bytes`
- Status: `resolved`

### Conclusion

The latest Step 1 update resolves most of the previous framework-trace gap. `OCR Engine`, `Match threshold`, and `OCR algorithms` are now traced in the framework parameters and persistence rules. One shared framework control is still missing from the explicit contract.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/requirements.md:212`, `.kiro/specs/special-event-tracking/requirements.md:239`, `.kiro/specs/special-event-tracking/requirements.md:33`, `.kiro/specs/special-event-tracking/requirements.md:40`, `.kiro/specs/special-event-tracking/requirements.md:248`, `.kiro/specs/special-event-tracking/requirements.md:251`, `.kiro/specs/special-event-tracking/requirements.md:252`, `.kiro/specs/special-event-tracking/requirements.md:253`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 clarity; `.kiro/steering/reviewer-rule.md` requirements consistency; `.kiro/steering/00-MASTER-RULES.md` persistence rules
- Issue: `No-player alert delay` is still shown as a shared framework control in the UI mockup and component table, but the parent `Parameters (framework)` and `Persistence Rules` sections do not define its canonical framework field or save/load/serialization contract.
- Impact: The parent Step 1 spec is still incomplete for implementation. A developer can derive the framework contract for OCR engine, threshold, algorithms, and ROI, but not for the shared delay control that is also shown as part of the standard event settings UI.
- Required update: Add the shared delay field to the parent framework parameters and persistence rules, or explicitly state why this control is not part of the parent framework contract even though it appears in the shared UI sketch.

### Notes

- The latest edit correctly adds framework-level trace for `ocr_engine`, `match_threshold`, and `ocr_algorithms`.
- `Case 4` still looks correct.
- The event requirements path format still looks correct.

### Open Questions

None.

### Required Updates

1. Close the remaining framework trace gap for `No-player alert delay`.

## REVIEW 2026-04-22 11:28:59

- Review ID: `REV-20260422-112859`
- Reviewer: Codex
- Scope: `imperial-guardian-event-tracker.md` follow-up review after the latest large logic update
- Target File: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Target File Timestamp: `2026-04-22 10:57:44`
- Target File Size: `15000 bytes`
- Status: `resolved`

### Conclusion

The updated event spec is more explicit about dedup, callback-driven processing, and OPEN/CLOSED transitions. However, the new logic still has two important internal conflicts and one remaining completeness gap.

### Findings

#### F-001

- Severity: `Blocker`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:60`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:101`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:122`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:154`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:175`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:181`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 logic clarity; `.kiro/steering/reviewer-rule.md` requirements consistency
- Issue: The spec says duplicate OCR text is "bỏ qua hoàn toàn" during dedup, but the no-player alert is now defined as being checked "mỗi khi nhận OCR callback". In the no-player scenario, OCR text is expected to stay unchanged for a long period, so a strict early-return dedup flow would prevent the Y-minute check from ever running.
- Impact: The main no-player alert requirement can fail in the exact scenario it is meant to detect. The current Step 1 logic is ambiguous about whether the timer check runs before dedup return or independently of text-change processing.
- Required update: Clarify that the Y-minute OPEN timer check runs independently on every callback (even when text is unchanged), or redesign the flow so dedup does not suppress the no-player alert path.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:17`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:131`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:133`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 1 completeness; `.kiro/steering/reviewer-rule.md` internal consistency
- Issue: The `Input/Output` table still lists a third OCR input example, `Cánh cửa vào Sự kiện Imperial Guardian sẽ đóng sau 2 phút`, but the updated classification flow now handles only two patterns: `đã bắt đầu` and `sẽ bắt đầu sau X phút`.
- Impact: The file now describes an OCR input that is no longer part of the declared recognition/processing contract. This creates ambiguity for Step 2 design and Step 3 tests about whether a third pattern still exists.
- Required update: Either remove the old "cửa sẽ đóng sau X phút" input from the spec, or add it back into the recognition flow and explain how it is processed.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:222`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:224`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` persistence rules; `.kiro/steering/reviewer-rule.md` requirements completeness
- Issue: The persistence checklist now includes `imperial_guardian_match_threshold` and `imperial_guardian_ocr_algorithms` in save/load/serialization rows, but the final verification row still says only `Y, OCR engine, ROI` must persist.
- Impact: The persistence contract is not fully closed in the test/verification step, so later Step 3 or Step 4 work can overlook verifying the new threshold/algorithm fields.
- Required update: Update the final persistence verification row so it explicitly includes `match_threshold` and `ocr_algorithms`.

### Open Questions

None.

### Required Updates

1. Resolve the dedup-vs-timer conflict so the no-player alert still works when OCR text does not change.
2. Align the declared OCR input set with the actual classification flow.
3. Complete the persistence verification row for the newly added fields.

## REVIEW 2026-04-23 03:47:59

- Review ID: `REV-20260423-034759`
- Reviewer: Codex
- Scope: `design.md` review for updated Special Event Tracking design, including impact against `requirements.md` and `imperial-guardian-event-tracker.md`
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-23 03:37:16`
- Target File Size: `20620 bytes`
- Status: `resolved`

### Conclusion

The new design is substantially closer to the current requirements/spec than the older version: it now includes threshold, algorithm testing, dedup-before-pattern handling, and the Imperial Guardian handler flow. However, I still found two logic conflicts and one format/readability problem.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:39`, `.kiro/specs/special-event-tracking/design.md:43`, `.kiro/specs/special-event-tracking/design.md:44`, `.kiro/specs/special-event-tracking/design.md:122`, `.kiro/specs/special-event-tracking/design.md:130`, `.kiro/specs/special-event-tracking/design.md:131`, `.kiro/specs/special-event-tracking/design.md:132`, `.kiro/specs/special-event-tracking/design.md:133`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design completeness; `.kiro/specs/special-event-tracking/requirements.md` framework contract
- Issue: The parent requirements now define a shared framework control set for all special events: `no_player_alert_delay`, `ocr_engine`, `match_threshold`, `ocr_algorithms`, and ROI. But the design architecture/UI section still models the event settings mainly as a hardcoded `ImperialGuardianWidget` with only checkbox, delay, and Teaching image controls called out explicitly. The shared framework control model is not reflected clearly in the architecture or section-construction design.
- Impact: The design does not cleanly explain how the approved framework contract in `requirements.md` maps into UI structure. A developer can still read this as an Imperial Guardian-only custom widget instead of a shared event-settings pattern hosted by the framework.
- Required update: Update the design narrative/architecture so it explicitly states that these controls are part of the shared special-event settings pattern, even if the current implementation only instantiates that pattern for Imperial Guardian first.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:154`, `.kiro/specs/special-event-tracking/design.md:156`, `.kiro/specs/special-event-tracking/design.md:185`, `.kiro/specs/special-event-tracking/design.md:194`
- Steering Source: `.kiro/steering/00-MASTER-RULES.md` persistence rules; `.kiro/specs/special-event-tracking/requirements.md`; `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Issue: The design still shows `_open_imperial_guardian_algorithm_testing()` writing `self.action.imperial_guardian_ocr_algorithms = getattr(self.action, "ocr_algorithms", [])`. This pulls from the generic `ocr_algorithms` field instead of a dedicated Imperial Guardian result path, even though both the parent requirements and the event spec now define `imperial_guardian_ocr_algorithms` as the canonical persisted field.
- Impact: If implemented as written, the algorithm-testing flow can save the wrong field or accidentally depend on unrelated generic OCR state. This would break the event-specific persistence contract and cause confusing save/load behavior.
- Required update: Make the design explicitly describe how the dialog returns/stores `imperial_guardian_ocr_algorithms` without routing through the generic `ocr_algorithms` field.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:7`, `.kiro/specs/special-event-tracking/design.md:9`, `.kiro/specs/special-event-tracking/design.md:20`, `.kiro/specs/special-event-tracking/design.md:36`, `.kiro/specs/special-event-tracking/design.md:68`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 readability/completeness; `.kiro/steering/reviewer-rule.md` review readability
- Issue: Large parts of `design.md` still have mojibake/encoding corruption in Vietnamese text (`bá»‹ áº£nh hÆ°á»Ÿng`, `Tá»•ng quan`, `ThÃªm`, etc.).
- Impact: The design is still readable enough to review, but it is not clean or reliable as a design artifact for developers. The corrupted text makes the document harder to maintain and increases the chance of misreading technical intent.
- Required update: Normalize the file encoding/content so the Vietnamese prose in `design.md` is readable end to end.

### Open Questions

None.

### Required Updates

1. Reflect the shared framework control model from `requirements.md` more clearly in the design architecture/UI structure.
2. Fix the algorithm-testing persistence flow so it writes `imperial_guardian_ocr_algorithms` directly.
3. Clean up the encoding/readability issues in `design.md`.

## REVIEW 2026-04-23 04:04:24

- Review ID: `REV-20260423-040424`
- Reviewer: Codex
- Scope: follow-up check for the latest `design.md` fixes against the previous design review comments
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-23 03:55:05`
- Target File Size: `21527 bytes`
- Status: `resolved`

### Conclusion

The developer has fixed most of the previous design review comments. The shared framework-control model is now stated explicitly, and the algorithm-testing flow now writes `imperial_guardian_ocr_algorithms` directly. However, the design is not fully clean yet: one old readability issue remains, and there is still one logic mismatch with the current event spec.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:230`, `.kiro/specs/special-event-tracking/design.md:231`, `.kiro/specs/special-event-tracking/design.md:219`, `.kiro/specs/special-event-tracking/design.md:222`, `.kiro/specs/special-event-tracking/design.md:292`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:15`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:16`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:147`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:149`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design/code-spec consistency; `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Issue: The handler design still uses ASCII-only patterns and parsing (`"su kien imperial guardian da bat dau"`, `"se bat dau sau"`, regex `phut`) without showing any normalization/transliteration step from accented OCR text to ASCII. The current event requirements still describe the recognized messages in Vietnamese with accents.
- Impact: If implemented exactly as written, the handler can miss the documented OCR messages unless another undocumented normalization layer exists. This is a real design/spec mismatch, not just wording.
- Required update: Either document the normalization step explicitly in the design before matching, or align the pattern/parsing design with the actual OCR text format described in the event requirements.

#### F-002

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:7`, `.kiro/specs/special-event-tracking/design.md:9`, `.kiro/specs/special-event-tracking/design.md:20`, `.kiro/specs/special-event-tracking/design.md:36`, `.kiro/specs/special-event-tracking/design.md:76`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 readability/completeness; `.kiro/steering/reviewer-rule.md` review readability
- Issue: `design.md` still has noticeable mojibake/encoding corruption in Vietnamese prose.
- Impact: The design is easier to review than before, but it is still not a clean design artifact for implementation handoff.
- Required update: Normalize the file encoding/content so the Vietnamese prose is readable end to end.

### Resolved Checks

- `REV-20260423-034759/F-001`: Resolved. The design now explicitly models the shared framework controls for all special events.
- `REV-20260423-034759/F-002`: Resolved. The algorithm-testing flow now writes `imperial_guardian_ocr_algorithms` directly instead of routing through generic `ocr_algorithms`.

### Open Questions

None.

### Required Updates

1. Clarify how OCR text is normalized before ASCII-only matching/parsing, or align the matching design with the accented messages declared in the event requirements.
2. Clean up the remaining encoding/readability issues in `design.md`.

## REVIEW 2026-04-23 06:49:11

- Review ID: `REV-20260423-064911`
- Reviewer: Codex
- Scope: follow-up review for the latest `design.md` against current `requirements.md` and `imperial-guardian-event-tracker.md`
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-23 06:42:40`
- Target File Size: `21827 bytes`
- Status: `resolved`

### Conclusion

The latest design update fixes part of the previous mismatch: the OCR match patterns are now aligned to accented Vietnamese strings from the event spec. However, the design is still not clean yet. I still found two logic mismatches and one readability issue.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:310`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:16`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:133`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:145`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design/spec consistency; `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Issue: The countdown parser still uses `re.search(r'(\\d+)\\s*ph[uU][tT]', text)`, but the current event spec declares OCR input as Vietnamese with accents, for example `sẽ bắt đầu sau 30 phút`. The design no longer documents any normalization/transliteration step before parsing, so the parser contract is still inconsistent with the declared input format.
- Impact: If implemented exactly as written, `_extract_minutes()` can fail to parse the very countdown message format that the event spec says the handler must process.
- Required update: Either document the normalization step that converts `phút` to an ASCII-safe form before regex parsing, or change the parsing design so it explicitly supports the accented OCR text declared in the event requirements.

#### F-002

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:288`, `.kiro/specs/special-event-tracking/design.md:304`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:19`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:20`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:149`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:156`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design completeness; `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Issue: The Telegram output templates in the handler skeleton still drift from the current event spec. The close-path message is `Sự kiện Imperial Guardian mở lại sau {x} phút`, while the event spec says the CLOSE notification is `Sự kiện Imperial Guardian đã đóng, mở sau X phút`. The no-player alert message is also still ASCII-only and omits the `đang` wording from the event spec.
- Impact: The design no longer preserves the approved user-facing output contract from the event requirements. This can create avoidable drift in tests, notifications, and later implementation review.
- Required update: Align the Telegram message templates in the design with the exact output contract currently declared in `imperial-guardian-event-tracker.md`, or explicitly update the event spec if the wording is intentionally being changed.

#### F-003

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:7`, `.kiro/specs/special-event-tracking/design.md:9`, `.kiro/specs/special-event-tracking/design.md:20`, `.kiro/specs/special-event-tracking/design.md:36`, `.kiro/specs/special-event-tracking/design.md:76`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 readability/completeness; `.kiro/steering/reviewer-rule.md`
- Issue: `design.md` still contains mojibake/encoding corruption in multiple Vietnamese prose sections.
- Impact: The logic is more coherent now, but the document is still not a clean handoff artifact for developers.
- Required update: Normalize the file encoding/content so the Vietnamese prose is readable end to end.

### Notes

- The previous broad pattern-matching mismatch from `REV-20260423-040424/F-001` is partially improved: the string patterns are now aligned to accented Vietnamese text.
- The remaining parsing mismatch is narrower and now sits mainly in `_extract_minutes()` and the unresolved output-template drift.

### Open Questions

None.

### Required Updates

1. Align the countdown parsing design with accented OCR input, or document normalization explicitly.
2. Align the handler notification templates with the event spec output contract.
3. Clean up the remaining encoding/readability issues in `design.md`.

## REVIEW 2026-04-24 04:50:55

- Review ID: `REV-20260424-045055`
- Reviewer: Codex
- Scope: `special-event-tracking` Step 2 re-review after the latest `design.md` update
- Target File: `.kiro/specs/special-event-tracking/design.md`
- Target File Timestamp: `2026-04-23 07:01:06`
- Target File Size: `21881 bytes`
- Status: `resolved`

### Conclusion

Step 2 is much closer to the approved requirements and event spec now. The earlier gaps around shared framework controls, algorithm persistence, countdown parsing, and notification wording are mostly addressed. However, the design is still not clean enough to approve because the encoding corruption now affects the handler code skeleton itself, not just the prose.

### Findings

#### F-001

- Severity: `Major`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:233`, `.kiro/specs/special-event-tracking/design.md:236`, `.kiro/specs/special-event-tracking/design.md:288`, `.kiro/specs/special-event-tracking/design.md:297`, `.kiro/specs/special-event-tracking/design.md:304`, `.kiro/specs/special-event-tracking/design.md:310`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:15`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:16`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:19`, `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md:20`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 design/spec consistency; `.kiro/specs/special-event-tracking/imperial-guardian-event-tracker.md`
- Issue: `design.md` still contains mojibake inside the handler code skeleton itself, for example the match patterns, Telegram strings, and the countdown regex use corrupted literals such as `Sá»± kiá»‡n ...` and `phÃºt`. This is no longer only a prose readability problem: the design skeleton now encodes the wrong string contract for OCR matching, parsing, and notifications.
- Impact: If a developer follows the design literally, the generated handler can match or emit corrupted text instead of the approved Vietnamese messages from the event spec. That makes the Step 2 artifact technically unreliable as an implementation handoff.
- Required update: Normalize the encoding of the handler skeleton so all Vietnamese literals in patterns, regex parsing, and Telegram templates match the canonical strings declared in `imperial-guardian-event-tracker.md`.

#### F-002

- Severity: `Minor`
- Status: `open`
- Location: `.kiro/specs/special-event-tracking/design.md:5`, `.kiro/specs/special-event-tracking/design.md:7`, `.kiro/specs/special-event-tracking/design.md:18`, `.kiro/specs/special-event-tracking/design.md:33`, `.kiro/specs/special-event-tracking/design.md:84`
- Steering Source: `.kiro/steering/feature-development-workflow.md` Step 2 readability/completeness; `.kiro/steering/reviewer-rule.md`
- Issue: The same mojibake still appears throughout the narrative sections of `design.md` (`Files bá»‹ áº£nh hÆ°á»Ÿng`, `Loáº¡i thay Ä‘á»•i`, `MÃ´ táº£`, etc.).
- Impact: Even where the design logic is now aligned, the document remains harder to maintain and easier to misread than it should be.
- Required update: Normalize the whole file to readable Vietnamese so the design artifact is clean end to end.

### Notes

- The previous Step 2 logic gaps around shared framework controls, `imperial_guardian_ocr_algorithms`, countdown parsing support, and close/no-player wording are now substantially improved.
- The remaining blocker for approval is mainly the corrupted text that has leaked into the code skeleton and surrounding design prose.

### Open Questions

None.

### Required Updates

1. Fix the mojibake in the handler skeleton so pattern strings, regex literals, and Telegram templates use the canonical Vietnamese text.
2. Clean up the remaining encoding/readability issues in the rest of `design.md`.

## REVIEW 2026-05-08 00:00:00

- Review ID: REV-20260508-000000
- Reviewer: developer (self-review)
- Scope: requirements — golden-invasion-event-tracker.md
- Target File: `.kiro/specs/special-event-tracking/golden-invasion-event-tracker.md`
- Status: resolved

### Conclusion
Requirements pass all checklist items. One minor self-correction applied (added `golden_invasion_enabled` to Parameters table — was missing from initial draft, present only in Persistence Rules).

### Findings
No open findings.

### Checklist Results
- ✅ Correct path
- ✅ Section 1 SPEC with Vấn đề, Mục tiêu
- ✅ Input/Output table aligned
- ✅ Parameters table aligned (fixed: added `golden_invasion_enabled`)
- ✅ Section 2 flow diagram
- ✅ Section 3 main flow with Input/Process/Output per step
- ✅ 8 edge cases documented
- ✅ 6 error handling entries
- ✅ UI mockup present
- ✅ User-facing content in Vietnamese
- ✅ No EARS English mixing
- ✅ All settings have persistence behavior (Section 5)
- ✅ Field names consistent across UI, object, JSON
- ✅ Thread-safe UI update documented (Error 6)
- ✅ Global config relationship: uses event_id prefix, independent from action-level config

## REVIEW 2026-05-08 01:00:00

- Review ID: REV-20260508-010000
- Reviewer: developer (self-review)
- Scope: design — golden-invasion-design.md
- Target File: `.kiro/specs/special-event-tracking/golden-invasion-design.md`
- Status: resolved

### Conclusion
Design passes all checklist items. Golden Invasion requires 2 subscriptions (channel + notify) vs 1 for Imperial Guardian — this is correctly reflected in the design.

### Findings
No open findings.

### Checklist Results
- ✅ Impact Analysis: files, dependencies, technical risks
- ✅ Files/classes/methods affected listed
- ✅ Dependencies documented
- ✅ Technical risks documented (2 subscriptions, thread sync)
- ✅ Architecture diagram present
- ✅ Correct module placement: src/logic/ and src/ui/
- ✅ Code skeleton with type hints
- ✅ Docstrings on public APIs
- ✅ Persistence implementation explained (Section 6)
- ✅ Thread-safe UI update pattern explained (Section 5)
- ✅ Not over-engineered beyond requirements

## REVIEW 2026-05-11 00:00:00

- Review ID: REV-20260511-000000
- Reviewer: developer (self-review)
- Scope: implementation — golden_invasion_handler.py + action_type.py + tool_manager.py + system_executor.py + passive_read_settings_dialog.py + tests
- Status: resolved

### Conclusion
All 31 unit tests pass. Implementation follows design spec. Key fix applied: ASCII map lookup for no-diacritic OCR text, with threshold guard to allow test_high_threshold_rejects_partial_match to work correctly.

### Findings
No open findings.

### Checklist Results
- ✅ golden_invasion_handler.py: state machine WAITING→ACTIVE, 2 callbacks, thread-safe lock
- ✅ BOSS_NAMES constant: 7 lowercase Vietnamese names
- ✅ ASCII map (_BOSS_ASCII_MAP): handles no-diacritic OCR fallback
- ✅ action_type.py: 15 golden_invasion_* fields added
- ✅ tool_manager.py: _action_to_dict() and from_dict() updated
- ✅ system_executor.py: setup/teardown for 2 subscriptions (channel + notify)
- ✅ passive_read_settings_dialog.py: UI section with 2 ROI groups + radio buttons
- ✅ Thread safety: threading.Lock() in both callbacks
- ✅ UI updates via log_signal_emit (Qt signal), no direct QWidget calls
- ✅ Backward compatibility: from_dict() uses .get() with defaults
- ✅ All 31 unit tests pass
- ✅ Manual test plan: docs/MANUAL_TEST_GOLDEN_INVASION.md

## REVIEW 2026-05-11 02:00:00

- Review ID: REV-20260511-020000
- Reviewer: developer (self-review)
- Scope: refactor normalize_ocr_text + imperial_guardian_handler + golden_invasion_handler + tests
- Status: resolved

### Conclusion
All 61 tests pass. OCR normalize refactor complete. Both handlers normalize text before matching. Telegram messages use Vietnamese with diacritics. screen_scan_service.py not modified.

### Findings
No open findings.

### Checklist Results
- normalize_ocr_text() added as public function in event_tracking_helper.py
- Handles: d-with-stroke to d, NFD diacritic strip, lowercase, whitespace collapse, OCR noise chars
- imperial_guardian_handler.py: normalize before cache/log/match, patterns simplified to no-diacritic form
- golden_invasion_handler.py: normalize channel + notify text, _BOSS_DISPLAY for Telegram messages with diacritics
- _BOSS_ASCII_MAP removed, replaced by normalize-based matching
- Telegram messages: Vietnamese with diacritics in both handlers
- screen_scan_service.py: not modified
- 61 total tests pass

## REVIEW 2026-05-11 10:37:55

- Review ID: REV-20260511-103755
- Reviewer: Codex
- Scope: implementation review — OCR normalization refactor and related tests
- Target Files:
  - `src/logic/system_executor/event_tracking_helper.py`
  - `src/logic/system_executor/imperial_guardian_handler.py`
  - `src/logic/system_executor/golden_invasion_handler.py`
  - `tests/test_imperial_guardian_handler.py`
  - `tests/test_golden_invasion_handler.py`
  - `tests/test_special_event_tracking_integration.py`
- Status: open

### Conclusion

The direct OCR normalization handler tests pass, but the change is not ready for approval because the full test suite fails and some test names/docstrings claim diacritic coverage while the actual input is still no-diacritic text.

### Verification

- `python -m pytest tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 61 passed
- `python -m pytest -q`
  - Result: 340 passed, 1 skipped, 6 failed

### Findings

1. Full suite fails in special event subscription lifecycle tests.
   - File: `tests/test_special_event_tracking_integration.py`
   - Failing tests:
     - `test_ocr_engine_propagated_to_subscription`
     - `test_setup_skips_when_disabled`
     - `test_setup_skips_when_roi_invalid`
     - `test_setup_subscribes_when_enabled_and_roi_valid`
     - `test_subscription_id_contains_action_identity`
     - `test_teardown_unsubscribes`
   - Cause: the MagicMock action fixture only configures Imperial Guardian fields. Golden Invasion fields are missing, so `getattr(action, "golden_invasion_enabled", False)` returns a truthy MagicMock and the code enters the Golden Invasion branch unexpectedly. ROI comparison then fails with `TypeError: '<=' not supported between instances of 'MagicMock' and 'MagicMock'`.
   - Required update: make the integration fixture explicitly set `golden_invasion_enabled = False` and default Golden Invasion ROI/settings when the test is about Imperial Guardian only, or use a stricter fake action object instead of bare MagicMock.

2. Teardown integration expectation is stale after Golden Invasion added two subscriptions.
   - File: `tests/test_special_event_tracking_integration.py`
   - Test: `test_teardown_unsubscribes`
   - Current expectation: exactly one unsubscribe call.
   - Actual behavior: three unsubscribe calls are attempted:
     - `imperial_guardian`
     - `golden_invasion:channel`
     - `golden_invasion:notify`
   - Required update: either update the test to expect all relevant unsubscribe calls, or configure Golden Invasion disabled in the fixture when the test is specifically Imperial Guardian-only.

3. Some "with diacritics" tests do not actually pass diacritic OCR text into the handler.
   - File: `tests/test_imperial_guardian_handler.py`
   - Example: `test_open_on_started_message_with_diacritics` currently uses `Su kien Imperial Guardian da bat dau`.
   - File: `tests/test_golden_invasion_handler.py`
   - Example: `test_ocr_with_diacritics_sends_telegram` currently uses `Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia`.
   - Required update: change those handler-level test inputs to real Vietnamese text with diacritics, for example:
     - `Sự kiện Imperial Guardian đã bắt đầu`
     - `Imperial Guardian sẽ bắt đầu sau 30 phút`
     - `Kim Thiết Vương đã bị tiêu diệt bởi PlayerX tại Lorencia`

### Notes

- `normalize_ocr_text()` itself does handle Vietnamese diacritic stripping via NFD and explicitly maps `đ/Đ` to `d/D`.
- `screen_scan_service.py` was not modified for OCR content filtering, which matches the requested architecture.

## REVIEW 2026-05-11 11:00:00

- Review ID: REV-20260511-110000
- Reviewer: developer (self-review)
- Scope: fix reviewer findings REV-20260511-103755
- Status: resolved

### Conclusion
All 3 findings from REV-20260511-103755 resolved. 67 tests pass.

### Findings resolved
- F-1: Integration fixture now sets golden_invasion_enabled=False and all GI fields explicitly
- F-2: test_teardown_unsubscribes updated to expect >=1 calls and verify imperial_guardian present
- F-3: test_open_on_started_message_with_diacritics and test_ocr_with_diacritics_sends_telegram now use real Vietnamese diacritic text
- Bonus: fixed patch path to screen_scan_service.ScreenScanService (local import pattern)

## REVIEW 2026-05-11 11:05:00

- Review ID: REV-20260511-110500
- Reviewer: Codex
- Scope: follow-up review — fixes for REV-20260511-103755
- Target Files:
  - `tests/test_special_event_tracking_integration.py`
  - `tests/test_imperial_guardian_handler.py`
  - `tests/test_golden_invasion_handler.py`
- Status: resolved

### Conclusion

The main fixes are mostly correct and the focused test set passes, but one diacritic coverage gap remains. The developer self-review should not be considered fully resolved yet.

### Verification

- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 67 passed

### Findings

1. Countdown "with diacritics" test still uses no-diacritic OCR text.
   - File: `tests/test_imperial_guardian_handler.py`
   - Test: `test_closed_on_countdown_with_diacritics`
   - Current issue: the test name/docstring says the countdown OCR contains Vietnamese diacritics, but the actual input is still no-diacritic text:
     - `Imperial Guardian se bat dau sau 30 phut`
   - Required update: change the input to real Vietnamese text with diacritics, for example:
     - `Imperial Guardian sẽ bắt đầu sau 30 phút`
   - Reason: this is the exact case the OCR normalization refactor is supposed to prove end-to-end.

### Already Verified As Fixed

- `tests/test_special_event_tracking_integration.py` now sets `golden_invasion_enabled = False` and explicit Golden Invasion defaults in the Imperial Guardian-only fixture.
- `test_teardown_unsubscribes` no longer assumes exactly one unsubscribe call and verifies the Imperial Guardian unsubscribe path.
- `test_open_on_started_message_with_diacritics` now uses real Vietnamese diacritic text.
- `test_ocr_with_diacritics_sends_telegram` now uses real Vietnamese diacritic text.

## REVIEW 2026-05-11 11:10:00

- Review ID: REV-20260511-111000
- Reviewer: Codex
- Scope: follow-up review — countdown diacritic test fix
- Target File: `tests/test_imperial_guardian_handler.py`
- Status: resolved

### Conclusion

The remaining finding from REV-20260511-110500 is fixed. The countdown handler-level test now uses real Vietnamese diacritic OCR text.

### Verification

- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 67 passed

### Findings

No open findings.

### Verified Fixes

- `test_closed_on_countdown_with_diacritics` now passes `Imperial Guardian sẽ bắt đầu sau 30 phút` into `handler.on_ocr_text(...)`.

## REVIEW 2026-05-11 11:28:35

- Review ID: REV-20260511-112835
- Reviewer: Codex
- Scope: code review — add/edit/delete Special Event Tracking UI and Golden Invasion teaching/algorithm flow
- Target Files:
  - `src/ui/action_config_dialog.py`
  - `src/ui/passive_read_settings_dialog.py`
  - `src/ui/multi_image_algorithm_testing_dialog.py`
  - `src/ui/tool_editor_window.py`
  - `src/logic/action_type.py`
  - `src/logic/tool_manager.py`
- Status: resolved

### Conclusion

The user's reported behavior is reproducible from code inspection. Golden Invasion settings are collected inside `PassiveReadSettingsDialog`, but they are not copied back into `ActionConfigDialog.action`, and the algorithm testing dialog has no Golden Invasion teaching image context. Delete also does not auto-save the tool after removing an action.

### Findings

#### F-001

- Severity: Blocker
- Status: open
- Location: `src/ui/action_config_dialog.py`, READ_PASSIVE settings save block
- Steering Source: user-reported add/edit persistence bug; reviewer-rule code checklist: persistence bugs and incorrect serialization/deserialization
- Issue: `PassiveReadSettingsDialog.get_settings()` returns Golden Invasion fields, but `ActionConfigDialog._open_action_settings()` only copies generic, Event Tracking, and Imperial Guardian settings into `self.action`. It does not copy:
  - `golden_invasion_enabled`
  - `golden_invasion_server_time`
  - `golden_invasion_channel_roi_*`
  - `golden_invasion_channel_ocr_engine`
  - `golden_invasion_channel_ocr_algorithms`
  - `golden_invasion_notify_roi_*`
  - `golden_invasion_notify_ocr_engine`
  - `golden_invasion_notify_ocr_algorithms`
  - `golden_invasion_match_threshold`
- Impact: after teaching/selecting/saving Golden Invasion in the settings dialog, the parent action can lose those values before the Tool Editor refreshes and auto-saves. This matches the reported "teaching and save succeeds but it does not appear in UI" behavior.
- Required Update: copy all Golden Invasion settings from `settings` into `self.action` in the READ_PASSIVE branch, next to the existing Imperial Guardian assignment block. Add or update a test that opens/saves READ_PASSIVE settings and asserts Golden Invasion fields are retained on the action.

#### F-002

- Severity: Blocker
- Status: open
- Location: `src/ui/multi_image_algorithm_testing_dialog.py`, constructor teaching image selection
- Steering Source: user-reported Golden Invasion algorithm testing bug; reviewer-rule code checklist: behavioral bugs
- Issue: `MultiImageAlgorithmTestingDialog.__init__()` only switches teaching image for `algorithm_field == "imperial_guardian_ocr_algorithms"`. All other algorithm fields fallback to `action.image_path`. Golden Invasion channel/notify algorithm testing therefore cannot use Golden Invasion-specific teaching data.
- Impact: opening multi algorithm testing from Golden Invasion can show the wrong teaching image/context, especially when Imperial/common teaching data exists. This matches the reported issue that the dialog uses Imperial Guardian teaching data instead of Golden Invasion teaching data.
- Required Update: add explicit Golden Invasion context handling. Options:
  - persist separate teaching image paths for `golden_invasion_channel_teaching_image_path` and `golden_invasion_notify_teaching_image_path`, then map `golden_invasion_channel_ocr_algorithms` and `golden_invasion_notify_ocr_algorithms` to those paths; or
  - pass an explicit `teaching_image_path`/`roi` context into `MultiImageAlgorithmTestingDialog` when opening it from the Golden Invasion channel/notify buttons.
  Also update `_get_fixed_roi_from_action()` or add event-specific ROI selection so OCR testing uses the correct Golden Invasion channel/notify ROI, not Imperial Guardian/generic ROI.

#### F-003

- Severity: Major
- Status: open
- Location: `src/ui/passive_read_settings_dialog.py`, `_select_gi_channel_image()` and `_select_gi_notify_image()`
- Steering Source: user-reported teaching UI bug; reviewer-rule code checklist: persistence bugs and behavioral bugs
- Issue: Golden Invasion ROI selection stores only coordinates on the action. It does not store a teaching image path for channel or notify, unlike Imperial Guardian which stores `imperial_guardian_teaching_image_path`.
- Impact: the settings UI can display coordinates during the current dialog session, but downstream tools that need the teaching image cannot reconstruct the Golden Invasion teaching context. Reopening algorithm testing has no event-specific image to show.
- Required Update: add channel/notify teaching image path fields to `AutoAction`, ToolManager save/load/copy, `PassiveReadSettingsDialog.get_settings()`, and `ActionConfigDialog._open_action_settings()`. Store `result[0]` from each Golden Invasion teaching dialog in the matching field.

#### F-004

- Severity: Major
- Status: open
- Location: `src/ui/tool_editor_window.py`, `delete_action()`, `duplicate_action()`, `move_action_up()`, `move_action_down()`
- Steering Source: user asked to check add/edit/delete flow; reviewer-rule code checklist: persistence bugs
- Issue: `add_action()` and `edit_action()` call `_auto_save_tool()`, but `delete_action()`, `duplicate_action()`, and move actions only refresh the table and do not auto-save.
- Impact: deleting/reordering/duplicating Special Event Tracking actions may appear to work in the UI but can be lost unless the user manually presses the main Save button afterward.
- Required Update: call `_auto_save_tool()` after confirmed delete, duplicate, move up, and move down, or clearly disable auto-save expectations and require an explicit save consistently. Existing add/edit behavior suggests auto-save should be applied here too.

### Open Questions

- Should Golden Invasion have two independent teaching image paths, one for channel ROI and one for notify ROI? The current UI has two ROI capture buttons, so two explicit paths are the least ambiguous design.

### Requested Updates

1. Fix Golden Invasion settings propagation from `PassiveReadSettingsDialog.get_settings()` to `ActionConfigDialog.action`.
2. Add Golden Invasion channel/notify teaching image path fields and persist them through `AutoAction` and `ToolManager`.
3. Make `MultiImageAlgorithmTestingDialog` choose teaching image and ROI by algorithm context instead of only special-casing Imperial Guardian.
4. Auto-save delete/duplicate/reorder actions in `ToolEditorWindow`, or document and implement a consistent manual-save-only model.
5. Add focused tests for:
   - saving READ_PASSIVE Golden Invasion settings from settings dialog into action;
   - Golden Invasion channel/notify algorithm dialog uses the correct teaching image/ROI;
   - delete action persists through tool reload.

## REVIEW 2026-05-11 11:45:00

- Review ID: REV-20260511-114500
- Reviewer: Codex
- Scope: implementation follow-up — fix REV-20260511-112835 findings
- Target Files:
  - `src/ui/action_config_dialog.py`
  - `src/ui/passive_read_settings_dialog.py`
  - `src/ui/multi_image_algorithm_testing_dialog.py`
  - `src/ui/tool_editor_window.py`
  - `src/logic/action_type.py`
  - `src/logic/tool_manager.py`
  - `tests/test_algorithm_testing_ocr_section.py`
  - `tests/test_tool_id_system.py`
- Status: resolved

### Conclusion

All findings from REV-20260511-112835 are fixed in the implementation patch.

### Verification

- `python -m py_compile src/ui/action_config_dialog.py src/ui/passive_read_settings_dialog.py src/ui/multi_image_algorithm_testing_dialog.py src/ui/tool_editor_window.py src/logic/tool_manager.py src/logic/action_type.py`
  - Result: passed
- `python -m pytest tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 113 passed

### Findings

No open findings.

### Verified Fixes

- F-001: READ_PASSIVE settings save now copies Golden Invasion fields, including channel/notify teaching image paths, from settings into the action.
- F-002: Multi-image algorithm testing now selects Golden Invasion channel/notify teaching images by `algorithm_field`.
- F-003: Golden Invasion channel/notify ROI capture now stores matching teaching image paths and returns them through `get_settings()`.
- F-004: Tool editor delete, duplicate, move up, and move down now call `_auto_save_tool()`.

## REVIEW 2026-05-11 14:43:47

- Review ID: REV-20260511-144347
- Reviewer: developer (self-review)
- Scope: review-comment closure — Special Event Tracking UI persistence and algorithm testing
- Target Files:
  - `src/ui/action_config_dialog.py`
  - `src/ui/passive_read_settings_dialog.py`
  - `src/ui/multi_image_algorithm_testing_dialog.py`
  - `src/ui/tool_editor_window.py`
  - `src/logic/action_type.py`
  - `src/logic/tool_manager.py`
  - `tests/test_algorithm_testing_ocr_section.py`
  - `tests/test_tool_id_system.py`
- Status: resolved

### Conclusion

Developer follow-up is complete. All open review comments from REV-20260511-112835 were implemented and verified by REV-20260511-114500.

### Findings

No open findings.

### Verification

- Focused verification already passed in REV-20260511-114500:
  - py_compile passed
  - 113 focused tests passed

### Closure Notes

- Golden Invasion settings now persist from settings dialog to action/tool data.
- Golden Invasion channel/notify algorithm testing now uses the correct teaching image and ROI context.
- Tool Editor delete/duplicate/reorder now auto-save consistently with add/edit.

## REVIEW 2026-05-11 15:20:05

- Review ID: REV-20260511-152005
- Reviewer: developer (self-review)
- Scope: implementation — paired Golden Invasion OCR logging
- Target Files:
  - `src/logic/system_executor/screen_scan_service.py`
  - `src/logic/system_executor/system_executor.py`
  - `tests/test_special_event_tracking_integration.py`
- Status: resolved

### Conclusion

Golden Invasion channel and notify OCR are now grouped by scan cycle. The service OCRs both ROIs from the same screenshot, logs the paired result once, then dispatches callbacks in stable channel/notify order.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/system_executor/screen_scan_service.py src/logic/system_executor/system_executor.py`
  - Result: passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_golden_invasion_handler.py -q`
  - Result: 43 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py -q`
  - Result: 115 passed

### Verified Behavior

- Golden Invasion channel and notify subscriptions share one `pair_group_id`.
- Paired OCR logs include both `channel` and `notify` text from the same screenshot cycle.
- Paired OCR logs include `matched=True/False` and matched kill pattern IDs.

## REVIEW 2026-05-11 15:50:52

- Review ID: REV-20260511-155052
- Reviewer: developer (self-review)
- Scope: implementation — Imperial Guardian latest notification handling
- Target Files:
  - `src/logic/system_executor/imperial_guardian_handler.py`
  - `tests/test_imperial_guardian_handler.py`
- Status: resolved

### Conclusion

Imperial Guardian Special Event Tracking now applies the intended "latest Imperial Guardian notification wins" rule inside the handler path. Mixed OCR blobs that contain older open/countdown messages now process the last Imperial Guardian segment before state transition.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/system_executor/imperial_guardian_handler.py`
  - Result: passed
- `python -m pytest tests/test_imperial_guardian_handler.py -q`
  - Result: 27 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 70 passed

### Verified Behavior

- Handler extracts the latest `imperial guardian` segment from normalized OCR text.
- When state is `OPEN`, countdown close is evaluated before open.
- Regression test covers the mixed OCR blob where the latest Imperial Guardian notification is `sẽ bắt đầu sau 30 phút`.

## REVIEW 2026-05-11 16:56:29

- Review ID: REV-20260511-165629
- Reviewer: developer (self-review)
- Scope: implementation - Imperial Guardian countdown false-positive and no-player timer fix
- Target Files:
  - `src/logic/system_executor/imperial_guardian_handler.py`
  - `src/logic/system_executor/screen_scan_service.py`
  - `tests/test_imperial_guardian_handler.py`
- Status: resolved

### Conclusion

The Imperial Guardian handler no longer treats countdown messages as event starts, and the no-player timer now runs even when an OCR cycle returns empty text. The scan service also no longer OCRs the same ROI twice in one `_run_ocr()` call.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/system_executor/imperial_guardian_handler.py src/logic/system_executor/screen_scan_service.py`
  - Result: passed
- `python -m pytest tests/test_imperial_guardian_handler.py -q`
  - Result: 30 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 73 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py -q`
  - Result: 119 passed

### Verified Behavior

- `imperial guardian bat dau` was removed from open patterns so `se bat dau sau X phut` cannot satisfy the open rule by fuzzy/partial matching.
- Countdown messages are evaluated before open messages for all states. In `WAITING` or `CLOSED`, countdown text is ignored instead of reopening the event.
- `on_ocr_text()` checks the no-player timer before returning on empty OCR text.
- `_run_ocr()` calls `ocr.recognize()` once per ROI instead of twice.

## REVIEW 2026-05-12 09:07:55

- Review ID: REV-20260512-090755
- Reviewer: developer (self-review)
- Scope: implementation - suppress Imperial Guardian no-player alert before noon
- Target Files:
  - `src/logic/system_executor/imperial_guardian_handler.py`
  - `tests/test_imperial_guardian_handler.py`
- Status: resolved

### Conclusion

Imperial Guardian no-player alerts are now disabled from 00:00 through 11:59 local time. The alert remains available from 12:00 onward.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/system_executor/imperial_guardian_handler.py`
  - Result: passed
- `python -m pytest tests/test_imperial_guardian_handler.py -q`
  - Result: 31 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py -q`
  - Result: 74 passed

### Verified Behavior

- `_check_no_player_alert()` returns early before 12:00 local time.
- Existing no-player alert tests pin local time to 14:00 to avoid time-of-day flakiness.
- A regression test verifies that a delayed OPEN state at 09:00 does not send the no-player alert and does not mark the alert as sent.

## REVIEW 2026-05-12 09:40:00

- Review ID: REV-20260512-094000
- Reviewer: developer (self-review)
- Scope: requirements white-wizard-red-dragon-event-tracker.md
- Target File: .kiro/specs/special-event-tracking/white-wizard-red-dragon-event-tracker.md
- Status: resolved

### Conclusion
Requirements pass all checklist items. Key differences from Golden Invasion: 23 fixed schedule slots, no text cache, 25-minute reset timer, killed_map with max count per boss type.

### Findings
No open findings.

## REVIEW 2026-05-12 10:00:00

- Review ID: REV-20260512-100000
- Reviewer: developer (self-review)
- Scope: requirements monster-invasion + updates golden/white-wizard files
- Status: resolved

### Conclusion
Monster Invasion event cha created with shared ROI/engine/algorithms. Sub-events updated. Flow diagrams in box/arrow format. requirements.md hierarchy updated.

### Findings
No open findings.

## REVIEW 2026-05-12 10:30:00

- Review ID: REV-20260512-103000
- Reviewer: developer (self-review)
- Scope: design monster-invasion-design.md
- Status: resolved

### Conclusion
Design passes all checklist items. Fan-out architecture with MonsterInvasionHandler. Backward compat maintained.

### Findings
No open findings.

## REVIEW 2026-05-12 15:21:22

- Review ID: REV-20260512-152122
- Reviewer: developer (self-review)
- Scope: implementation - Monster Invasion handler unit implementation
- Target Files:
  - `src/logic/system_executor/monster_invasion_handler.py`
  - `src/logic/system_executor/golden_invasion_sub_handler.py`
  - `src/logic/system_executor/white_wizard_red_dragon_handler.py`
  - `tests/test_monster_invasion_handler.py`
  - `tests/test_white_wizard_red_dragon_handler.py`
- Status: resolved

### Conclusion

The Monster Invasion fan-out handler and its White Wizard + Red Dragon sub-handler unit implementation are complete enough for the current handler-level tests. The missing `white_wizard_red_dragon_handler.py` module was added and the new handler test suite now passes.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/system_executor/monster_invasion_handler.py src/logic/system_executor/golden_invasion_sub_handler.py src/logic/system_executor/white_wizard_red_dragon_handler.py`
  - Result: passed
- `python -m pytest tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py -q`
  - Result: 29 passed

### Verified Behavior

- `MonsterInvasionHandler` fans channel/notify OCR text out to all sub-handlers and isolates sub-handler exceptions.
- `WhiteWizardRedDragonHandler` enters `ACTIVE` by schedule, tracks channel at start, deduplicates by max boss count, resets after 25 minutes, and returns to `WAITING` after four kills.
- White Wizard + Red Dragon notifications use Vietnamese display names and omit the player name from Telegram messages.

## REVIEW 2026-05-12 15:44:03

- Review ID: REV-20260512-154403
- Reviewer: developer (self-review)
- Scope: implementation - Monster Invasion persistence and subscription integration
- Target Files:
  - `src/logic/action_type.py`
  - `src/logic/tool_manager.py`
  - `src/logic/system_executor/system_executor.py`
  - `tests/test_special_event_tracking_integration.py`
  - `tests/test_tool_id_system.py`
- Status: resolved

### Conclusion

Monster Invasion action fields now persist through save/load/copy and the runtime can subscribe the shared channel/notify OCR pair for enabled Monster Invasion sub-events.

### Findings

No open findings.

### Verification

- `python -m py_compile src/logic/action_type.py src/logic/tool_manager.py src/logic/system_executor/system_executor.py src/logic/system_executor/monster_invasion_handler.py src/logic/system_executor/golden_invasion_sub_handler.py src/logic/system_executor/white_wizard_red_dragon_handler.py`
  - Result: passed
- `python -m pytest tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py tests/test_special_event_tracking_integration.py tests/test_tool_id_system.py -q`
  - Result: 61 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py -q`
  - Result: 152 passed

### Verified Behavior

- `AutoAction` contains Monster Invasion ROI, OCR, threshold, teaching image, and sub-event flags.
- `ToolManager` serializes, loads, and copies Monster Invasion fields, including teaching image path rewrite on copy.
- `SystemExecutor` creates a `MonsterInvasionHandler`, fans out shared OCR to enabled sub-handlers, and tears down both subscriptions.
- Monster Invasion does not subscribe when no sub-event is enabled.

## REVIEW 2026-05-12 16:01:40

- Review ID: REV-20260512-160140
- Reviewer: developer (self-review)
- Scope: implementation - Monster Invasion UI and algorithm testing integration
- Target Files:
  - `src/ui/passive_read_settings_dialog.py`
  - `src/ui/action_config_dialog.py`
  - `src/ui/multi_image_algorithm_testing_dialog.py`
  - `tests/test_algorithm_testing_ocr_section.py`
- Status: resolved

### Conclusion

Monster Invasion can now be configured from the READ_PASSIVE Special Event Tracking dialog. The dialog loads/saves Monster Invasion fields, supports channel/notify ROI capture, and opens algorithm testing with the correct Monster Invasion teaching image and ROI context.

### Findings

No open findings.

### Verification

- `python -m py_compile src/ui/passive_read_settings_dialog.py src/ui/action_config_dialog.py src/ui/multi_image_algorithm_testing_dialog.py src/logic/action_type.py src/logic/tool_manager.py src/logic/system_executor/system_executor.py`
  - Result: passed
- `python -m pytest tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py tests/test_special_event_tracking_integration.py tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py -q`
  - Result: 88 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py -q`
  - Result: 154 passed

### Verified Behavior

- `PassiveReadSettingsDialog` exposes Monster Invasion enable, sub-event flags, shared channel/notify ROI, OCR engines, algorithms, threshold, and Golden Invasion base time.
- `ActionConfigDialog` copies Monster Invasion settings from the settings dialog into the action object.
- `MultiImageAlgorithmTestingDialog` selects Monster Invasion channel/notify teaching images and ROIs by `algorithm_field`.
- Regression tests cover Monster Invasion channel/notify algorithm contexts and settings propagation.

## REVIEW 2026-05-12 16:24:20

- Review ID: REV-20260512-162420
- Reviewer: developer (self-review)
- Scope: implementation - remove standalone Golden Invasion UI
- Target Files:
  - `src/ui/passive_read_settings_dialog.py`
  - `tests/test_algorithm_testing_ocr_section.py`
- Status: resolved

### Conclusion

The standalone Golden Invasion controls are no longer shown in the Special Event Tracking settings UI. Golden Invasion remains configurable as a Monster Invasion sub-event.

### Findings

No open findings.

### Verification

- `python -m py_compile src/ui/passive_read_settings_dialog.py src/ui/action_config_dialog.py src/ui/multi_image_algorithm_testing_dialog.py`
  - Result: passed
- `python -m pytest tests/test_algorithm_testing_ocr_section.py tests/test_special_event_tracking_integration.py tests/test_tool_id_system.py tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py -q`
  - Result: 89 passed
- `python -m pytest tests/test_special_event_tracking_integration.py tests/test_imperial_guardian_handler.py tests/test_golden_invasion_handler.py tests/test_monster_invasion_handler.py tests/test_white_wizard_red_dragon_handler.py tests/test_algorithm_testing_ocr_section.py tests/test_tool_id_system.py -q`
  - Result: 155 passed

### Verified Behavior

- `PassiveReadSettingsDialog` hides the legacy standalone `Golden Invasion` checkbox and settings widget.
- `get_settings()` always returns `golden_invasion_enabled=False` for the standalone event path.
- A regression test verifies the standalone Golden Invasion UI remains hidden while Monster Invasion sub-event configuration is still available.
