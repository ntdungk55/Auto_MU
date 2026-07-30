# Feature: Deferred Tool Settings

## 1. Tổng quan

Feature này cho phép user thay đổi setting của tool đang chạy mà không gián đoạn chu kỳ hiện tại. Setting mới sẽ được áp dụng từ chu kỳ tiếp theo.

## 2. User Stories

- Là user, tôi muốn thay đổi setting tool đang chạy, để điều chỉnh hành vi mà không phải dừng và khởi động lại tool
- Là user, tôi muốn chu kỳ hiện tại tiếp tục chạy với setting cũ, để không bị gián đoạn giữa chừng
- Là user, tôi muốn setting mới tự động áp dụng từ chu kỳ tiếp theo, để không phải thao tác thêm

## 3. Acceptance Criteria

### Requirement 1: Save Settings Without Restart

**User Story:** Là user, tôi muốn save setting mà không restart tool, để chu kỳ hiện tại không bị gián đoạn.

#### Acceptance Criteria

1. WHEN user clicks "Setting" button THEN THE System SHALL open settings dialog without stopping the tool
2. WHEN user modifies settings and clicks OK THEN THE System SHALL save settings to JSON file
3. WHEN settings are saved THEN THE System SHALL NOT restart the tool
4. WHEN settings are saved THEN THE System SHALL NOT interrupt the current cycle

### Requirement 2: Apply Settings on Next Cycle

**User Story:** Là user, tôi muốn setting mới áp dụng từ chu kỳ tiếp theo, để chu kỳ hiện tại chạy hoàn chỉnh.

#### Acceptance Criteria

1. WHEN current cycle is running THEN THE System SHALL continue using old settings in memory
2. WHEN current cycle completes (after cycle post delay) THEN THE System SHALL reload tool settings from JSON file
3. WHEN next cycle starts THEN THE System SHALL use the new settings from JSON file
4. WHEN tool is in pause state THEN THE System SHALL reload settings when next cycle starts (after resume)

### Requirement 3: Multiple Settings Changes

**User Story:** Là user, tôi muốn thay đổi setting nhiều lần trong cùng chu kỳ, để điều chỉnh linh hoạt.

#### Acceptance Criteria

1. WHEN user changes settings multiple times in same cycle THEN THE System SHALL save each change to JSON file
2. WHEN next cycle starts THEN THE System SHALL use the latest settings from JSON file
3. WHEN settings are changed THEN THE System SHALL NOT show any notification or confirmation

### Requirement 4: Non-Loop Tools

**User Story:** Là user, tôi muốn setting áp dụng cho tool không lặp, để đảm bảo tính nhất quán.

#### Acceptance Criteria

1. WHEN tool has loop disabled THEN THE System SHALL reload settings after tool completes
2. WHEN tool runs again (manual start) THEN THE System SHALL use new settings from JSON file

## 4. Input/Output

**Input:**
- User clicks "Setting" button
- User modifies settings in dialog
- User clicks OK

**Output:**
- Settings saved to JSON file
- Tool continues running with old settings
- Next cycle uses new settings

## 5. Sơ đồ khối

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Running (Cycle 1)                    │
│                  (Using old settings in memory)              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ User clicks Setting │
                  └─────────┬───────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  Settings Dialog   │
                  │   (User modifies)  │
                  └─────────┬───────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  Save to JSON file │
                  │  (No tool restart) │
                  └─────────┬───────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Cycle 1 continues with old settings             │
│                    (No interruption)                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │  Cycle 1 completes │
                  │ (After post delay) │
                  └─────────┬───────────┘
                           │
                           ▼
                  ┌────────────────────┐
                  │ Reload settings    │
                  │   from JSON file   │
                  └─────────┬───────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Cycle 2 starts                            │
│                  (Using new settings)                        │
└─────────────────────────────────────────────────────────────┘
```

## 6. Technical Notes

### Current Behavior (Problem)
- `_open_tool_settings()` calls `_stop_runner()` then `_toggle_run_pause()`
- This restarts the tool immediately, interrupting current cycle

### New Behavior (Solution)
- `_open_tool_settings()` only saves to JSON, no restart
- `ToolRunner._run()` reloads settings at end of each cycle
- Reload happens after cycle post delay, before next cycle starts

### Key Changes
1. Remove restart logic from `_open_tool_settings()`
2. Add `reload_tool_settings()` method to ToolRunner
3. Call `reload_tool_settings()` at end of each cycle in `_run()` loop

### Edge Cases
- Tool paused: Reload when next cycle starts (after resume)
- Tool stopped: Reload when tool starts again
- Non-loop tool: Reload after completion, before next manual start
- Multiple changes: Always use latest settings from JSON

### Performance
- Reload from JSON is fast (< 1ms)
- No impact on cycle timing
- No additional memory overhead
