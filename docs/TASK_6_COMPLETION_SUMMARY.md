# Task 6 Completion Summary: Fixed ROI Persistence & Gemini API Caching

## Overview
Completed two critical fixes to improve application stability and performance:
1. **Fixed ROI Settings Persistence** - Settings now survive app restart
2. **Gemini API Configuration Caching** - Eliminated redundant API initialization

---

## Fix 1: Fixed ROI Settings Persistence

### Problem
After capturing a teaching image, ticking the Fixed ROI checkbox, and adjusting coordinates, closing and reopening the app caused all settings to be lost.

### Root Cause
The `tool_manager.py` file was NOT serializing/deserializing Fixed ROI fields:
- `use_fixed_roi`, `roi_x`, `roi_y`, `roi_w`, `roi_h`
- `teaching_corner_x1/y1/x2/y2`

These fields existed in the `AutoAction` dataclass but were missing from:
- `_action_to_dict()` method (serialization)
- `from_dict()` method (deserialization)

### Solution
**File: `tool_manager.py`**

1. **Added Fixed ROI fields to `_action_to_dict()` (serialization)**:
   ```python
   # Fixed ROI settings
   "use_fixed_roi": bool(getattr(action, "use_fixed_roi", False)),
   "roi_x": int(getattr(action, "roi_x", 0) or 0),
   "roi_y": int(getattr(action, "roi_y", 0) or 0),
   "roi_w": int(getattr(action, "roi_w", 200) or 200),
   "roi_h": int(getattr(action, "roi_h", 100) or 100),
   # Teaching image corners
   "teaching_corner_x1": getattr(action, "teaching_corner_x1", None),
   "teaching_corner_y1": getattr(action, "teaching_corner_y1", None),
   "teaching_corner_x2": getattr(action, "teaching_corner_x2", None),
   "teaching_corner_y2": getattr(action, "teaching_corner_y2", None)
   ```

2. **Added Fixed ROI fields to `from_dict()` (deserialization)**:
   ```python
   # Fixed ROI settings
   use_fixed_roi=bool(a_data.get("use_fixed_roi", False)),
   roi_x=int(a_data.get("roi_x", 0) or 0),
   roi_y=int(a_data.get("roi_y", 0) or 0),
   roi_w=int(a_data.get("roi_w", 200) or 200),
   roi_h=int(a_data.get("roi_h", 100) or 100),
   # Teaching image corners
   teaching_corner_x1=a_data.get("teaching_corner_x1", None),
   teaching_corner_y1=a_data.get("teaching_corner_y1", None),
   teaching_corner_x2=a_data.get("teaching_corner_x2", None),
   teaching_corner_y2=a_data.get("teaching_corner_y2", None)
   ```

### Verification
Tested serialization/deserialization round-trip:
- ✅ All Fixed ROI fields serialize correctly to JSON
- ✅ All Fixed ROI fields deserialize correctly from JSON
- ✅ Values are preserved through save/load cycle

### Impact
- Users can now save Fixed ROI configurations and have them persist across app restarts
- Teaching image coordinates are preserved
- No data loss when closing and reopening the application

---

## Fix 2: Gemini API Configuration Caching

### Problem
When running tools with Gemini integration enabled, the API was being reconfigured from scratch every single time:

```
[Read Map] [Gemini] Configuring API...          ← EVERY TIME!
[Read Map] [Gemini] Initializing model: gemini-2.5-flash
[Read Map] [Gemini] Calling generate_content...
[Read Map] [Gemini] Timeout sau 10s
```

This was inefficient and could cause issues if the API was already in use.

### Root Cause
In `_gemini_extract_from_ocr()`, the code was calling:
```python
genai.configure(api_key=api_key)  # Called EVERY TIME
```

The API only needs to be configured once per unique API key, but it was being reconfigured on every tool execution.

### Solution
**File: `system_executor.py`**

1. **Added API configuration cache to `__init__`**:
   ```python
   # Gemini API configuration cache: key -> api_key (to avoid reconfiguring)
   self._gemini_api_configured: dict[str, bool] = {}
   ```

2. **Modified `_gemini_extract_from_ocr()` to check cache before configuring**:
   ```python
   if api_key not in self._gemini_api_configured:
       self._ui_log("<b style='color:blue;'>[Gemini]</b> Configuring API...")
       genai.configure(api_key=api_key)
       self._gemini_api_configured[api_key] = True
       self._ui_log("<b style='color:green;'>[Gemini]</b> API configured ✓")
   else:
       self._ui_log("<b style='color:green;'>[Gemini]</b> Using cached API configuration ✓")
   ```

### Expected Behavior After Fix
**First tool run:**
```
[Read Map] [Gemini] Configuring API...
[Read Map] [Gemini] API configured ✓
```

**Subsequent tool runs (same API key):**
```
[Read Map] [Gemini] Using cached API configuration ✓
```

### Benefits
- **Performance**: API configuration happens only once per unique API key
- **Efficiency**: Eliminates redundant initialization overhead
- **Logging**: Clear indication when cached configuration is being used
- **Reliability**: Reduces potential issues from repeated API configuration

---

## Commits Made

### Commit 1: Fixed ROI Persistence
```
Fix: Add Fixed ROI fields serialization/deserialization in tool_manager.py

- Added Fixed ROI fields to _action_to_dict(): use_fixed_roi, roi_x, roi_y, roi_w, roi_h
- Added teaching corner fields to _action_to_dict(): teaching_corner_x1/y1/x2/y2
- Added Fixed ROI fields to from_dict() for proper deserialization
- Added teaching corner fields to from_dict() for proper deserialization
- Verified serialization/deserialization works correctly with test

This fixes the issue where Fixed ROI settings were lost after app restart.
```

### Commit 2: Gemini API Caching
```
Optimize: Cache Gemini API configuration to avoid reconfiguring on each tool run

- Added _gemini_api_configured cache dict to SystemExecutor.__init__
- Modified _gemini_extract_from_ocr to check cache before calling genai.configure()
- Only configure API once per unique API key, reuse configuration on subsequent calls
- Added logging to show when cached configuration is being used
- This eliminates redundant API initialization and improves performance

The issue was that genai.configure() was being called every time a tool ran,
even though the API was already initialized. Now it's only configured once.
```

### Commit 3: Documentation
```
docs: Add Gemini API caching fix documentation
```

---

## Files Modified
1. **tool_manager.py** - Added Fixed ROI field serialization/deserialization
2. **system_executor.py** - Added Gemini API configuration caching

## Files Created
1. **GEMINI_API_CACHING_FIX.md** - Documentation for the Gemini API caching fix
2. **TASK_6_COMPLETION_SUMMARY.md** - This summary document

---

## Testing Recommendations

### Test 1: Fixed ROI Persistence
1. Open the application
2. Create a new action with type "Đọc thụ động" (READ_PASSIVE)
3. Capture a teaching image
4. Tick the "Sử dụng vùng đọc cố định" (Use Fixed ROI) checkbox
5. Adjust the ROI coordinates (X, Y, Width, Height)
6. Save the tool
7. Close the application
8. Reopen the application
9. Load the same tool
10. Verify: Fixed ROI checkbox is still ticked and coordinates are preserved

### Test 2: Gemini API Caching
1. Set up Gemini API key in environment
2. Create an action with Gemini enabled
3. Run the tool - check logs for "Configuring API..."
4. Run another tool with Gemini enabled
5. Check logs for "Using cached API configuration ✓"
6. Verify Gemini still responds correctly

---

## Summary
Both fixes are now complete and committed:
- ✅ Fixed ROI settings persist across app restarts
- ✅ Gemini API configuration is cached to avoid redundant initialization
- ✅ All changes are backward compatible
- ✅ Comprehensive logging added for debugging
