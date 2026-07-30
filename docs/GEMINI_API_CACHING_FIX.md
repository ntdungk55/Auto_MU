# Gemini API Configuration Caching Fix

## Problem
When running tools with Gemini integration enabled, the API was being reconfigured from scratch every single time:

```
[Read Map] [Gemini] API key found ✓
[Read Map] [Gemini] Model: gemini-2.5-flash
[Read Map] [Gemini] Prompt configured ✓ (length: 54)
[Read Map] [Gemini] Final prompt length: 181 chars
[Read Map] [Gemini] Timeout: 10.0s
[Read Map] [Gemini] Configuring API...          ← EVERY TIME!
[Read Map] [Gemini] Initializing model: gemini-2.5-flash
[Read Map] [Gemini] Calling generate_content...
[Read Map] [Gemini] Timeout sau 10s
[Read Map] [Passive Gemini] No result from Gemini
```

The issue was that `genai.configure(api_key=api_key)` was being called inside the worker thread every time `_gemini_extract_from_ocr()` was invoked, even though the API was already initialized.

## Root Cause
In `system_executor.py`, the `_gemini_extract_from_ocr()` method was calling:
```python
genai.configure(api_key=api_key)  # Called EVERY TIME
```

This is inefficient because:
1. The API only needs to be configured once per unique API key
2. Reconfiguring wastes time and resources
3. It can cause issues if the API is already in use elsewhere

## Solution
Implemented API configuration caching:

### 1. Added cache to `SystemExecutor.__init__`:
```python
self._gemini_api_configured: dict[str, bool] = {}
```

### 2. Modified `_gemini_extract_from_ocr()` to check cache:
```python
if api_key not in self._gemini_api_configured:
    self._ui_log("<b style='color:blue;'>[Gemini]</b> Configuring API...")
    genai.configure(api_key=api_key)
    self._gemini_api_configured[api_key] = True
    self._ui_log("<b style='color:green;'>[Gemini]</b> API configured ✓")
else:
    self._ui_log("<b style='color:green;'>[Gemini]</b> Using cached API configuration ✓")
```

## Benefits
- **Performance**: API configuration happens only once per unique API key
- **Efficiency**: Eliminates redundant initialization overhead
- **Logging**: Clear indication when cached configuration is being used
- **Reliability**: Reduces potential issues from repeated API configuration

## Expected Behavior After Fix
First tool run:
```
[Read Map] [Gemini] Configuring API...
[Read Map] [Gemini] API configured ✓
```

Subsequent tool runs (same API key):
```
[Read Map] [Gemini] Using cached API configuration ✓
```

## Testing
To verify the fix works:
1. Run a tool with Gemini enabled
2. Check logs - should see "Configuring API..."
3. Run another tool with Gemini enabled
4. Check logs - should see "Using cached API configuration ✓"
5. Verify Gemini still responds correctly

## Files Modified
- `system_executor.py`: Added caching logic to avoid redundant API configuration
