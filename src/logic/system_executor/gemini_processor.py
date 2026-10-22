"""Legacy-named AI processor for OCR text post-processing through OpenRouter."""

import os
import threading
import time
from datetime import datetime
try:
    from action_type import AutoAction
except ImportError:
    from ..action_type import AutoAction

class GeminiProcessor:
    """Handle provider-configured AI integration for text post-processing."""
    
    def __init__(self, ui_log_func=None):
        """Initialize Gemini processor.
        
        Args:
            ui_log_func: Optional logging function
        """
        self.ui_log = ui_log_func or (lambda x: None)
    
    @staticmethod
    def _escape_html(s: str) -> str:
        """Escape HTML special characters."""
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    
    def process(self, ocr_text: str, action: AutoAction, overall_timeout_s: float | None = None) -> str | None:
        """Send OCR text to the selected OpenRouter model using the action prompt.

        Args:
            ocr_text: Text from OCR
            action: AutoAction with Gemini configuration
            overall_timeout_s: Overall timeout in seconds

        Returns:
            AI output string, or None on timeout/error.
        """
        provider = str(os.environ.get("AI_PROVIDER", "openrouter") or "openrouter").strip().casefold()
        if provider != "openrouter":
            self.ui_log(f"<b style='color:red;'>[AI]</b> OCR processor hiện chỉ dùng OpenRouter, không dùng provider {provider}.")
            return None
        api_key = str(os.environ.get("OPENROUTER_API_KEY", "") or "").strip()
        if not api_key:
            self.ui_log("<b style='color:red;'>[AI]</b> Chưa có OPENROUTER_API_KEY.")
            return None
        self.ui_log("<b style='color:green;'>[OpenRouter]</b> API key found ✓")

        # Step 3: Resolve model name
        model_name = str(os.environ.get("AI_MODEL_NAME", "") or "").strip() or str(
            getattr(action, "gemini_model", "") or ""
        ).strip() or "google/gemini-2.5-flash"
        self.ui_log(f"<b style='color:blue;'>[OpenRouter]</b> Model: {model_name}")

        # Step 4: Check prompt configuration
        prompt_tpl = str(getattr(action, "prompt", "") or "").strip() or str(getattr(action, "gemini_prompt", "") or "").strip()
        if not prompt_tpl:
            self.ui_log("<b style='color:red;'>[AI]</b> Bạn chưa cấu hình prompt cho AI.")
            return None
        self.ui_log(f"<b style='color:green;'>[OpenRouter]</b> Prompt configured ✓ (length: {len(prompt_tpl)})")

        # Step 5: Build final prompt
        if "{text}" in prompt_tpl:
            prompt = prompt_tpl.replace("{text}", ocr_text or "")
        else:
            prompt = f"{prompt_tpl}\n\n=== OCR TEXT ===\n{ocr_text or ''}\n"
        
        # Prepend ISO datetime (realtime)
        iso_time = datetime.now().isoformat(timespec='seconds')
        prompt = f"[Current time: {iso_time}]\n{prompt}"
        self.ui_log(f"<b style='color:blue;'>[Gemini]</b> Final prompt length: {len(prompt)} chars")

        # Step 6: Determine timeout
        t_action = float(getattr(action, "gemini_timeout", 10.0) or 10.0)
        if overall_timeout_s is not None:
            try:
                t_action = max(0.1, min(float(t_action), float(overall_timeout_s)))
            except Exception:
                pass
        if t_action <= 0:
            self.ui_log("<b style='color:red;'>[Gemini]</b> Invalid timeout value")
            return None
        self.ui_log(f"<b style='color:blue;'>[Gemini]</b> Timeout: {t_action:.1f}s")

        # Step 7: Execute Gemini call with timeout
        out = {"text": None, "err": None}

        def _worker():
            try:
                from openai import OpenAI
                self.ui_log(f"<b style='color:blue;'>[OpenRouter]</b> Calling model: {model_name}")
                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=4996,
                )
                out["text"] = str(resp.choices[0].message.content or "")
                self.ui_log(f"<b style='color:green;'>[OpenRouter]</b> Response received ({len(out['text'])} chars)")
            except Exception as e:
                out["err"] = str(e)
                self.ui_log(f"<b style='color:red;'>[OpenRouter Worker]</b> Exception: {e}")

        th = threading.Thread(target=_worker, daemon=True)
        th.start()
        th.join(timeout=float(t_action))
        
        if th.is_alive():
            self.ui_log(f"<b style='color:red;'>[OpenRouter]</b> Timeout sau {t_action:.0f}s")
            return None
        
        if out["err"]:
            self.ui_log(f"<b style='color:red;'>[OpenRouter]</b> Lỗi: {self._escape_html(out['err'])}")
            return None
        
        result = str(out["text"] or "").strip()
        self.ui_log(f"<b style='color:green;'>[OpenRouter Success]</b> Result: {len(result)} chars")
        return result
