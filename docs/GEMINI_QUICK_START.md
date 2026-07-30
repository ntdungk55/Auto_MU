# Gemini Integration - Quick Start Guide

## What Was Fixed

✅ **Gemini configuration now saves properly for READ_PASSIVE actions**
✅ **Comprehensive logging shows exactly what's happening**
✅ **Gemini options are independent (builder pattern)**

## How to Use Gemini with READ_PASSIVE

### Step 1: Create READ_PASSIVE Action
1. Open tool editor
2. Create new action
3. Select action type: **"Đọc thụ động"** (READ_PASSIVE)
4. Configure teaching image or Fixed ROI

### Step 2: Enable Gemini
1. Check: **"Dùng Gemini để chiết xuất dữ liệu từ text OCR"**
2. Click **"Cài key"** and enter your GEMINI_API_KEY
3. Click **"Cài đặt prompt"** and enter your prompt
   - Use `{text}` placeholder for OCR text
   - Example: `"Extract numbers from: {text}"`
4. Set timeout (default 10 seconds is fine)
5. Click **OK** to save

### Step 3: Run and Monitor
1. Start the tool
2. Watch the log output for:
   - ✅ "API key found"
   - ✅ "Prompt configured"
   - ✅ "Response received"
   - ✅ Gemini result displayed

## Troubleshooting

### Problem: "Chưa có GEMINI_API_KEY"
**Solution**: Click "Cài key" and enter your API key

### Problem: "Bạn chưa cấu hình prompt cho Gemini"
**Solution**: Click "Cài đặt prompt" and enter a prompt

### Problem: "Timeout sau 10s"
**Solution**: Increase timeout value (up to 120 seconds)

### Problem: Gemini not responding
**Solution**: Check the log output for error messages and follow the troubleshooting steps above

## Prompt Examples

### Extract Numbers
```
Extract all numbers from the following text: {text}
```

### Extract Dates
```
Find all dates in the following text and format as YYYY-MM-DD: {text}
```

### Summarize
```
Summarize the following text in one sentence: {text}
```

### Translate
```
Translate the following text to English: {text}
```

### Extract Specific Info
```
Extract the product name and price from: {text}
```

## How It Works

1. **OCR**: Text is extracted from the image
2. **Gemini**: Your prompt + OCR text is sent to Gemini
3. **Result**: Gemini's response is logged and cached
4. **Notification**: Result can be sent to Telegram (optional)

## Key Features

- ✅ **Independent Options**: Change Gemini settings without affecting other options
- ✅ **Persistent Configuration**: Settings are saved and loaded correctly
- ✅ **Comprehensive Logging**: See exactly what's happening at each step
- ✅ **Graceful Fallback**: If Gemini fails, OCR text is still available
- ✅ **Timeout Protection**: Gemini processing won't hang indefinitely

## Tips

1. **Test Your Prompt**: Make sure your prompt works with sample OCR text
2. **Use {text} Placeholder**: Always use `{text}` to insert OCR text
3. **Set Reasonable Timeout**: 10-30 seconds is usually enough
4. **Monitor Logs**: Check logs to see if Gemini is processing
5. **Save API Key**: Use "Cài key" to save your API key securely

## Next Steps

1. Get your GEMINI_API_KEY from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a READ_PASSIVE action
3. Enable Gemini and configure your prompt
4. Test with your images
5. Monitor the logs to verify it's working

## Support

If Gemini is still not working:
1. Check the log output for error messages
2. Verify your API key is correct
3. Verify your prompt is configured
4. Check your internet connection
5. Try increasing the timeout value
