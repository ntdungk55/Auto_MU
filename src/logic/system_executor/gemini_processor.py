"""Gemini Processor - AI-powered text post-processing."""

import os
import threading
import time
from datetime import datetime
try:
    from action_type import AutoAction
except ImportError:
    from ..action_type import AutoAction

try:
    import google.generativeai as genai
except Exception:
    genai = None


class GeminiProcessor:
    """Handle Gemini API integration for text post-processing."""
    
    def __init__(self, ui_log_func=None):
        """Initialize Gemini processor.
        
        Args:
            ui_log_func: Optional logging function
        """
        self.ui_log = ui_log_func or (lambda x: None)
        self._gemini_model_cache: dict[str, object] = {}
        # Gemini API configuration cache: key -> api_key (to avoid reconfiguring)
        self._gemini_api_configured: dict[str, bool] = {}
    
    def _get_gemini_model(self, model_name: str):
        """Lazy init GenerativeModel for Gemini action post-processing."""
        if genai is None:
            return None
        model_name = str(model_name or "").strip() or "gemini-1.5-flash"
        if model_name in self._gemini_model_cache:
            return self._gemini_model_cache[model_name]
        try:
            m = genai.GenerativeModel(model_name)
            self._gemini_model_cache[model_name] = m
            return m
        except Exception:
            return None
    
    @staticmethod
    def _escape_html(s: str) -> str:
        """Escape HTML special characters."""
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
    
    def process(self, ocr_text: str, action: AutoAction, overall_timeout_s: float | None = None) -> str | None:
        """Send OCR text to Gemini using prompt configured on the action.

        Args:
            ocr_text: Text from OCR
            action: AutoAction with Gemini configuration
            overall_timeout_s: Overall timeout in seconds

        Returns:
            Gemini output string, or None on timeout/error.
        """
        # Step 1: Check if Gemini SDK is available
        if genai is None:
            self.ui_log("<b style='color:red;'>[Gemini]</b> Chưa có Gemini SDK trong runtime.")
            return None

        # Step 2: Check API key
        api_key = str(os.environ.get("GEMINI_API_KEY", "") or "").strip()
        if not api_key:
            self.ui_log("<b style='color:red;'>[Gemini]</b> Chưa có GEMINI_API_KEY (hãy lưu key trong app hoặc set env).")
            return None
        self.ui_log("<b style='color:green;'>[Gemini]</b> API key found ✓")

        # Step 3: Resolve model name
        model_name = str(os.environ.get("GEMINI_MODEL_NAME", "") or "").strip() or str(
            getattr(action, "gemini_model", "") or ""
        ).strip() or "gemini-1.5-flash"
        self.ui_log(f"<b style='color:blue;'>[Gemini]</b> Model: {model_name}")

        # Step 4: Check prompt configuration
        prompt_tpl = str(getattr(action, "prompt", "") or "").strip() or str(getattr(action, "gemini_prompt", "") or "").strip()
        if not prompt_tpl:
            self.ui_log("<b style='color:red;'>[Gemini]</b> Bạn chưa cấu hình prompt cho Gemini.")
            return None
        self.ui_log(f"<b style='color:green;'>[Gemini]</b> Prompt configured ✓ (length: {len(prompt_tpl)})")

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
                # Check if API is already configured for this key
                if api_key not in self._gemini_api_configured:
                    self.ui_log("<b style='color:blue;'>[Gemini]</b> Configuring API...")
                    genai.configure(api_key=api_key)
                    self._gemini_api_configured[api_key] = True
                    self.ui_log("<b style='color:green;'>[Gemini]</b> API configured ✓")
                else:
                    self.ui_log("<b style='color:green;'>[Gemini]</b> Using cached API configuration ✓")
                
                self.ui_log(f"<b style='color:blue;'>[Gemini]</b> Initializing model: {model_name}")
                m = self._get_gemini_model(model_name)
                if m is None:
                    out["err"] = f"Không khởi tạo được model: {model_name}"
                    return
                
                self.ui_log("<b style='color:blue;'>[Gemini]</b> Calling generate_content...")
                resp = m.generate_content(prompt)
                out["text"] = str(getattr(resp, "text", "") or "")
                self.ui_log(f"<b style='color:green;'>[Gemini]</b> Response received ({len(out['text'])} chars)")
            except Exception as e:
                out["err"] = str(e)
                self.ui_log(f"<b style='color:red;'>[Gemini Worker]</b> Exception: {e}")

        th = threading.Thread(target=_worker, daemon=True)
        th.start()
        th.join(timeout=float(t_action))
        
        if th.is_alive():
            self.ui_log(f"<b style='color:red;'>[Gemini]</b> Timeout sau {t_action:.0f}s")
            return None
        
        if out["err"]:
            self.ui_log(f"<b style='color:red;'>[Gemini]</b> Lỗi: {self._escape_html(out['err'])}")
            return None
        
        result = str(out["text"] or "").strip()
        self.ui_log(f"<b style='color:green;'>[Gemini Success]</b> Result: {len(result)} chars")
        return result
