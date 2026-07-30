import json
import os
import uuid
from typing import List, Optional, Tuple
from dataclasses import asdict
from .action_type import AutoAction

MONSTER_INVASION_DEFAULTS = {
    "monster_invasion_enabled": False,
    "monster_invasion_channel_roi_x1": 0,
    "monster_invasion_channel_roi_y1": 0,
    "monster_invasion_channel_roi_x2": 0,
    "monster_invasion_channel_roi_y2": 0,
    "monster_invasion_channel_ocr_engine": "auto",
    "monster_invasion_channel_ocr_algorithms": [],
    "monster_invasion_channel_teaching_image_path": "",
    "monster_invasion_notify_roi_x1": 0,
    "monster_invasion_notify_roi_y1": 0,
    "monster_invasion_notify_roi_x2": 0,
    "monster_invasion_notify_roi_y2": 0,
    "monster_invasion_notify_ocr_engine": "auto",
    "monster_invasion_notify_ocr_algorithms": [],
    "monster_invasion_notify_teaching_image_path": "",
    "monster_invasion_match_threshold": 70.0,
    "monster_invasion_golden_invasion_enabled": False,
    "monster_invasion_golden_invasion_server_time": "01:30",
    "monster_invasion_white_wizard_red_dragon_enabled": False,
}

class Tool:
    def __init__(
        self,
        name: str,
        actions: List[AutoAction],
        loop_enabled: bool = False,
        loop_mode: str = "forever",  # "forever" | "count"
        loop_count: int = 1,
        loop_pre_delay_100ms: int = 0,
        loop_post_delay_100ms: int = 0,
        stop_on_timeout: bool = True,
        restart_on_timeout: bool = False,
        run_lock_mode: int = 0,  # 0=no dialog, 1=dialog when processing (exclude delays), 2=dialog always (include delays)
        user_input_mode: str = "ignore",  # "ignore" | "pause" | "stop"
        pause_duration: int = 5,  # seconds (1-300)
        notify_on_timeout: bool = False,  # Telegram notification when timeout causes stop completely
        block_input_enabled: bool = False,  # Block user input when executing actions
        block_input_duration: float = 3.0,  # Max duration to block input (0.1-10.0 seconds)
        target_window_title: str = "",  # Per-tool target game window title
        window_capture_dir: str = "",  # Per-tool folder for manual window captures
        id: Optional[str] = None,  # UUID for tool identification
    ):
        self.id = id or str(uuid.uuid4())  # Auto-generate UUID if not provided
        self.name = name
        self.actions = actions
        self.loop_enabled = bool(loop_enabled)
        self.loop_mode = loop_mode if loop_mode in ("forever", "count") else "forever"
        self.loop_count = int(loop_count) if int(loop_count) > 0 else 1
        self.loop_pre_delay_100ms = int(loop_pre_delay_100ms) if int(loop_pre_delay_100ms) >= 0 else 0
        self.loop_post_delay_100ms = int(loop_post_delay_100ms) if int(loop_post_delay_100ms) >= 0 else 0
        self.stop_on_timeout = bool(stop_on_timeout)
        self.restart_on_timeout = bool(restart_on_timeout)
        # Clamp lock mode to supported values
        try:
            self.run_lock_mode = int(run_lock_mode)
        except Exception:
            self.run_lock_mode = 0
        if self.run_lock_mode not in (0, 1, 2):
            self.run_lock_mode = 0
        # User input detection settings
        self.user_input_mode = user_input_mode if user_input_mode in ("ignore", "pause", "stop") else "ignore"
        self.pause_duration = max(1, min(300, int(pause_duration)))
        # Telegram timeout notification
        self.notify_on_timeout = bool(notify_on_timeout)
        # Input blocking settings
        self.block_input_enabled = bool(block_input_enabled)
        self.block_input_duration = max(0.1, min(10.0, float(block_input_duration)))
        self.target_window_title = str(target_window_title or "")
        self.window_capture_dir = str(window_capture_dir or "")
        # Enforce mutual exclusivity
        if self.restart_on_timeout:
            self.stop_on_timeout = False
    
    def to_dict(self):
        return {
            "id": self.id,  # UUID first for readability
            "name": self.name,
            "settings": {
                "loop_enabled": bool(getattr(self, "loop_enabled", False)),
                "loop_mode": getattr(self, "loop_mode", "forever"),
                "loop_count": int(getattr(self, "loop_count", 1)),
                "loop_pre_delay_100ms": int(getattr(self, "loop_pre_delay_100ms", 0)),
                "loop_post_delay_100ms": int(getattr(self, "loop_post_delay_100ms", 0)),
                "stop_on_timeout": bool(getattr(self, "stop_on_timeout", True)),
                "restart_on_timeout": bool(getattr(self, "restart_on_timeout", False)),
                "run_lock_mode": int(getattr(self, "run_lock_mode", 0)),
                "user_input_mode": str(getattr(self, "user_input_mode", "ignore") or "ignore"),
                "pause_duration": int(getattr(self, "pause_duration", 5) or 5),
                "notify_on_timeout": bool(getattr(self, "notify_on_timeout", False)),
                "block_input_enabled": bool(getattr(self, "block_input_enabled", False)),
                "block_input_duration": float(getattr(self, "block_input_duration", 3.0)),
                "target_window_title": str(getattr(self, "target_window_title", "") or ""),
                "window_capture_dir": str(getattr(self, "window_capture_dir", "") or ""),
            },
            "actions": [self._action_to_dict(a) for a in self.actions]
        }
    
    @staticmethod
    def _action_to_dict(action: AutoAction):
        data = {
            "name": action.name,
            "purpose": action.purpose,
            "action_type": action.action_type.value,
            "mode": action.mode.value,
            "value": action.value,
            "image_path": action.image_path,
            "enable_post_key_image_check": bool(getattr(action, "enable_post_key_image_check", False)),
            "post_key_check_delay": float(getattr(action, "post_key_check_delay", 1.0) or 1.0),
            "post_key_retry_count": int(getattr(action, "post_key_retry_count", 0) or 0),
            "enable_post_click_image_check": bool(getattr(action, "enable_post_click_image_check", False)),
            "post_click_check_delay": float(getattr(action, "post_click_check_delay", 1.0) or 1.0),
            "post_click_retry_count": int(getattr(action, "post_click_retry_count", 0) or 0),
            "post_click_image_path": getattr(action, "post_click_image_path", None),
            "post_click_match_threshold": float(getattr(action, "post_click_match_threshold", 0.4) or 0.4),
            "click_x": action.click_x,
            "click_y": action.click_y,
            "alt_click": getattr(action, "alt_click", False),
            "match_threshold": float(getattr(action, "match_threshold", 0.4)),
            "continue_on_timeout": bool(getattr(action, "continue_on_timeout", False)),
            "multiscale_enabled": bool(getattr(action, "multiscale_enabled", True)),
            "multiscale_min": float(getattr(action, "multiscale_min", 0.70)),
            "multiscale_max": float(getattr(action, "multiscale_max", 1.30)),
            "multiscale_step": float(getattr(action, "multiscale_step", 0.05)),
            "delay": action.delay,
            "read_data": getattr(action, 'read_data', False),  # Thêm read_data
            "ocr_engine": str(getattr(action, "ocr_engine", "auto") or "auto"),
            "ocr_bright_on_dark": bool(getattr(action, "ocr_bright_on_dark", False)),
            "preprocessing_config": getattr(action, "preprocessing_config", None),
            "gemini_enabled": bool(getattr(action, "gemini_enabled", False)),
            "prompt": str(getattr(action, "prompt", "") or "") or str(getattr(action, "gemini_prompt", "") or ""),
            # Back-compat field name (older builds)
            "gemini_prompt": str(getattr(action, "gemini_prompt", "") or "") or str(getattr(action, "prompt", "") or ""),
            "gemini_timeout": float(getattr(action, "gemini_timeout", 10.0) or 10.0),
            "timeout": getattr(action, 'timeout', 30.0),  # Thêm timeout
            "check_interval": getattr(action, 'check_interval', 1.0),  # Thêm check_interval
            "notification_enabled": bool(getattr(action, "notification_enabled", False)),  # Telegram notification
            "notification_filter_keywords": str(getattr(action, "notification_filter_keywords", "") or ""),
            "notification_dedup_minutes": int(getattr(action, "notification_dedup_minutes", 1) or 1),
            "goto_step_enabled": bool(getattr(action, "goto_step_enabled", False)),
            "goto_step_index": int(getattr(action, "goto_step_index", 0) or 0),
            "timeout_goto_enabled": bool(getattr(action, "timeout_goto_enabled", False)),
            "timeout_goto_step_index": int(getattr(action, "timeout_goto_step_index", 0) or 0),
            "passive_mode": str(getattr(action, "passive_mode", "detect_image") or "detect_image"),
            "passive_sample_every": int(getattr(action, "passive_sample_every", 1) or 1),
            "passive_only_new_frame": bool(getattr(action, "passive_only_new_frame", True)),
            "passive_cancel_old": bool(getattr(action, "passive_cancel_old", False)),
            "passive_keywords": str(getattr(action, "passive_keywords", "") or ""),
            "passive_detect_timeout": float(getattr(action, "passive_detect_timeout", 30.0) or 30.0),
            "passive_detect_threshold": float(getattr(action, "passive_detect_threshold", 0.4) or 0.4),
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
            "teaching_corner_y2": getattr(action, "teaching_corner_y2", None),
            # Teaching window resolution
            "teaching_window_width": getattr(action, "teaching_window_width", None),
            "teaching_window_height": getattr(action, "teaching_window_height", None),
            "post_click_teaching_corner_x1": getattr(action, "post_click_teaching_corner_x1", None),
            "post_click_teaching_corner_y1": getattr(action, "post_click_teaching_corner_y1", None),
            "post_click_teaching_corner_x2": getattr(action, "post_click_teaching_corner_x2", None),
            "post_click_teaching_corner_y2": getattr(action, "post_click_teaching_corner_y2", None),
            "post_click_teaching_window_width": getattr(action, "post_click_teaching_window_width", None),
            "post_click_teaching_window_height": getattr(action, "post_click_teaching_window_height", None),
            # OCR preprocessing options
            "ocr_upscale_enabled": bool(getattr(action, "ocr_upscale_enabled", True)),
            "ocr_upscale_factor": float(getattr(action, "ocr_upscale_factor", 2.0) or 2.0),
            "ocr_enhance_contrast": bool(getattr(action, "ocr_enhance_contrast", True)),
            "ocr_sharpen": bool(getattr(action, "ocr_sharpen", True)),
            "ocr_denoise": bool(getattr(action, "ocr_denoise", False)),
            # Click by coordinate mode
            "click_by_coordinate": bool(getattr(action, "click_by_coordinate", False)),
            "coordinate_click_pos": list(getattr(action, "coordinate_click_pos", None) or []) if getattr(action, "coordinate_click_pos", None) else None,
            "dynamic_ocr_target_mode": str(getattr(action, "dynamic_ocr_target_mode", "roi") or "roi"),
            "dynamic_ocr_rules": list(getattr(action, "dynamic_ocr_rules", []) or []),
            "dynamic_ocr_patterns": list(getattr(action, "dynamic_ocr_patterns", []) or []),
            "dynamic_ocr_pattern_threshold": float(getattr(action, "dynamic_ocr_pattern_threshold", 80.0) or 80.0),
            "dynamic_ocr_code": str(getattr(action, "dynamic_ocr_code", "return False") or "return False"),
            # Event notify (Alarm/Gate) settings
            "event_notify_times": list(getattr(action, "event_notify_times", []) or []),
            "event_prepare_start_s": int(getattr(action, "event_prepare_start_s", 300) or 300),
            "event_prepare_end_s": int(getattr(action, "event_prepare_end_s", 60) or 60),
            # Template mask regions
            "mask_regions": list(getattr(action, "mask_regions", []) or []),
            # Multi-Image Algorithm Testing
            "window_capture_paths": list(getattr(action, "window_capture_paths", []) or []),
            "window_capture_results": dict(getattr(action, "window_capture_results", {}) or {}),
            "preprocessing_algorithms": list(getattr(action, "preprocessing_algorithms", []) or []),
            # Preprocessing Algorithms UI
            "template_matching_algorithms": list(getattr(action, "template_matching_algorithms", []) or []),
            "ocr_algorithms": list(getattr(action, "ocr_algorithms", []) or []),
            # Event Tracking settings (no event_tracking_enabled - use passive_mode instead)
            "event_ocr_pattern": str(getattr(action, "event_ocr_pattern", "") or ""),
            "event_match_threshold": float(getattr(action, "event_match_threshold", 100.0) or 100.0),
            "event_ocr_engine": str(getattr(action, "event_ocr_engine", "auto") or "auto"),
            "event_reappear_timeout_minutes": int(getattr(action, "event_reappear_timeout_minutes", 15) or 15),
            # ROI will be taken from Teaching image (teaching_corner_x1, y1, x2, y2)
            # Special Event Tracking settings
            "imperial_guardian_enabled": bool(getattr(action, "imperial_guardian_enabled", False)),
            "imperial_guardian_no_player_alert_delay": int(getattr(action, "imperial_guardian_no_player_alert_delay", 10) or 10),
            "imperial_guardian_teaching_corner_x1": int(getattr(action, "imperial_guardian_teaching_corner_x1", 0) or 0),
            "imperial_guardian_teaching_corner_y1": int(getattr(action, "imperial_guardian_teaching_corner_y1", 0) or 0),
            "imperial_guardian_teaching_corner_x2": int(getattr(action, "imperial_guardian_teaching_corner_x2", 0) or 0),
            "imperial_guardian_teaching_corner_y2": int(getattr(action, "imperial_guardian_teaching_corner_y2", 0) or 0),
            "imperial_guardian_teaching_image_path": getattr(action, "imperial_guardian_teaching_image_path", ""),
            "imperial_guardian_ocr_engine": getattr(action, "imperial_guardian_ocr_engine", "auto"),
            "imperial_guardian_match_threshold": getattr(action, "imperial_guardian_match_threshold", 70.0),
            "imperial_guardian_ocr_algorithms": getattr(action, "imperial_guardian_ocr_algorithms", []) or [],
            "golden_invasion_enabled": bool(getattr(action, "golden_invasion_enabled", False)),
            "golden_invasion_server_time": str(getattr(action, "golden_invasion_server_time", "01:30") or "01:30"),
            "golden_invasion_channel_roi_x1": int(getattr(action, "golden_invasion_channel_roi_x1", 0) or 0),
            "golden_invasion_channel_roi_y1": int(getattr(action, "golden_invasion_channel_roi_y1", 0) or 0),
            "golden_invasion_channel_roi_x2": int(getattr(action, "golden_invasion_channel_roi_x2", 0) or 0),
            "golden_invasion_channel_roi_y2": int(getattr(action, "golden_invasion_channel_roi_y2", 0) or 0),
            "golden_invasion_channel_ocr_engine": str(getattr(action, "golden_invasion_channel_ocr_engine", "auto") or "auto"),
            "golden_invasion_channel_ocr_algorithms": list(getattr(action, "golden_invasion_channel_ocr_algorithms", []) or []),
            "golden_invasion_channel_teaching_image_path": str(getattr(action, "golden_invasion_channel_teaching_image_path", "") or ""),
            "golden_invasion_notify_roi_x1": int(getattr(action, "golden_invasion_notify_roi_x1", 0) or 0),
            "golden_invasion_notify_roi_y1": int(getattr(action, "golden_invasion_notify_roi_y1", 0) or 0),
            "golden_invasion_notify_roi_x2": int(getattr(action, "golden_invasion_notify_roi_x2", 0) or 0),
            "golden_invasion_notify_roi_y2": int(getattr(action, "golden_invasion_notify_roi_y2", 0) or 0),
            "golden_invasion_notify_ocr_engine": str(getattr(action, "golden_invasion_notify_ocr_engine", "auto") or "auto"),
            "golden_invasion_notify_ocr_algorithms": list(getattr(action, "golden_invasion_notify_ocr_algorithms", []) or []),
            "golden_invasion_notify_teaching_image_path": str(getattr(action, "golden_invasion_notify_teaching_image_path", "") or ""),
            "golden_invasion_match_threshold": float(getattr(action, "golden_invasion_match_threshold", 70.0) or 70.0),
        }
        for key, default in MONSTER_INVASION_DEFAULTS.items():
            value = getattr(action, key, default)
            if isinstance(default, bool):
                data[key] = bool(value)
            elif isinstance(default, int):
                data[key] = int(value or 0)
            elif isinstance(default, float):
                data[key] = float(value or default)
            elif isinstance(default, list):
                data[key] = list(value or [])
            else:
                data[key] = str(value or default)
        return data
    
    @staticmethod
    def from_dict(data: dict) -> 'Tool':
        from .action_type import ActionType, ActionMode
        # Load ID (generate if missing for backward compatibility)
        tool_id = data.get("id")
        if not tool_id:
            tool_id = str(uuid.uuid4())
        
        settings = data.get("settings") or {}
        loop_enabled = bool(settings.get("loop_enabled", False))
        loop_mode = settings.get("loop_mode", "forever")
        loop_count = int(settings.get("loop_count", 1) or 1)
        loop_pre_delay_100ms = int(settings.get("loop_pre_delay_100ms", 0) or 0)
        loop_post_delay_100ms = int(settings.get("loop_post_delay_100ms", 0) or 0)
        stop_on_timeout = bool(settings.get("stop_on_timeout", True))
        restart_on_timeout = bool(settings.get("restart_on_timeout", False))
        run_lock_mode = settings.get("run_lock_mode", 0)
        user_input_mode = str(settings.get("user_input_mode", "ignore") or "ignore")
        pause_duration = int(settings.get("pause_duration", 5) or 5)
        notify_on_timeout = bool(settings.get("notify_on_timeout", False))
        block_input_enabled = bool(settings.get("block_input_enabled", False))
        block_input_duration = float(settings.get("block_input_duration", 3.0) or 3.0)
        target_window_title = str(settings.get("target_window_title", "") or "")
        window_capture_dir = str(settings.get("window_capture_dir", "") or "")
        actions = []
        for a_data in data.get("actions", []):
            try:
                action_type = next(t for t in ActionType if t.value == a_data["action_type"])
            except StopIteration:
                # Unknown action type, skip this action
                print(f"[WARN] Unknown action_type: {a_data.get('action_type')}, skipping action: {a_data.get('name')}")
                continue
            
            # Backward/forward compatibility:
            # - Older tools may have "mode"
            # - Newer tools may omit it (we no longer use ActionMode in runtime logic)
            try:
                mode_val = a_data.get("mode", ActionMode.ACTIVE.value)
                mode = next(m for m in ActionMode if m.value == mode_val)
            except Exception:
                mode = ActionMode.ACTIVE
            action = AutoAction(
                name=a_data["name"],
                purpose=a_data["purpose"],
                action_type=action_type,
                mode=mode,
                value=a_data.get("value", ""),
                image_path=a_data.get("image_path"),
                enable_post_key_image_check=bool(a_data.get("enable_post_key_image_check", False)),
                post_key_check_delay=float(a_data.get("post_key_check_delay", 1.0) or 1.0),
                post_key_retry_count=int(a_data.get("post_key_retry_count", 0) or 0),
                enable_post_click_image_check=bool(a_data.get("enable_post_click_image_check", False)),
                post_click_check_delay=float(a_data.get("post_click_check_delay", 1.0) or 1.0),
                post_click_retry_count=int(a_data.get("post_click_retry_count", 0) or 0),
                post_click_image_path=a_data.get("post_click_image_path"),
                post_click_match_threshold=float(a_data.get("post_click_match_threshold", 0.4) or 0.4),
                click_x=a_data.get("click_x"),
                click_y=a_data.get("click_y"),
                alt_click=bool(a_data.get("alt_click", False)),
                match_threshold=float(a_data.get("match_threshold", 0.4)),
                continue_on_timeout=bool(a_data.get("continue_on_timeout", False)),
                multiscale_enabled=bool(a_data.get("multiscale_enabled", True)),
                multiscale_min=float(a_data.get("multiscale_min", 0.70)),
                multiscale_max=float(a_data.get("multiscale_max", 1.30)),
                multiscale_step=float(a_data.get("multiscale_step", 0.05)),
                delay=a_data.get("delay", 1.0),
                read_data=a_data.get("read_data", False),  # Thêm read_data
                ocr_engine=str(a_data.get("ocr_engine", "auto") or "auto"),
                ocr_bright_on_dark=bool(a_data.get("ocr_bright_on_dark", False)),
                preprocessing_config=a_data.get("preprocessing_config", None),
                gemini_enabled=bool(a_data.get("gemini_enabled", False)),
                prompt=str(a_data.get("prompt", "") or a_data.get("gemini_prompt", "") or ""),
                gemini_prompt=str(a_data.get("gemini_prompt", "") or a_data.get("prompt", "") or ""),
                gemini_timeout=float(a_data.get("gemini_timeout", 10.0) or 10.0),
                timeout=a_data.get("timeout", 5.0),  # Thêm timeout (mặc định 5s)
                check_interval=a_data.get("check_interval", 1.0),  # Thêm check_interval
                notification_enabled=bool(a_data.get("notification_enabled", False)),  # Telegram notification
                notification_filter_keywords=str(a_data.get("notification_filter_keywords", "") or ""),
                notification_dedup_minutes=int(a_data.get("notification_dedup_minutes", 1) or 1),
                goto_step_enabled=bool(a_data.get("goto_step_enabled", False)),
                goto_step_index=int(a_data.get("goto_step_index", 0) or 0),
                timeout_goto_enabled=bool(a_data.get("timeout_goto_enabled", False)),
                timeout_goto_step_index=int(a_data.get("timeout_goto_step_index", 0) or 0),
                passive_mode=str(a_data.get("passive_mode", "detect_image") or "detect_image"),
                passive_sample_every=int(a_data.get("passive_sample_every", 1) or 1),
                passive_only_new_frame=bool(a_data.get("passive_only_new_frame", True)),
                passive_cancel_old=bool(a_data.get("passive_cancel_old", False)),
                passive_keywords=str(a_data.get("passive_keywords", "") or ""),
                passive_detect_timeout=float(a_data.get("passive_detect_timeout", 30.0) or 30.0),
                passive_detect_threshold=float(a_data.get("passive_detect_threshold", 0.4) or 0.4),
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
                teaching_corner_y2=a_data.get("teaching_corner_y2", None),
                # Teaching window resolution
                teaching_window_width=a_data.get("teaching_window_width", None),
                teaching_window_height=a_data.get("teaching_window_height", None),
                post_click_teaching_corner_x1=a_data.get("post_click_teaching_corner_x1", None),
                post_click_teaching_corner_y1=a_data.get("post_click_teaching_corner_y1", None),
                post_click_teaching_corner_x2=a_data.get("post_click_teaching_corner_x2", None),
                post_click_teaching_corner_y2=a_data.get("post_click_teaching_corner_y2", None),
                post_click_teaching_window_width=a_data.get("post_click_teaching_window_width", None),
                post_click_teaching_window_height=a_data.get("post_click_teaching_window_height", None),
                # OCR preprocessing options
                ocr_upscale_enabled=bool(a_data.get("ocr_upscale_enabled", True)),
                ocr_upscale_factor=float(a_data.get("ocr_upscale_factor", 2.0) or 2.0),
                ocr_enhance_contrast=bool(a_data.get("ocr_enhance_contrast", True)),
                ocr_sharpen=bool(a_data.get("ocr_sharpen", True)),
                ocr_denoise=bool(a_data.get("ocr_denoise", False)),
                # Click by coordinate mode
                click_by_coordinate=bool(a_data.get("click_by_coordinate", False)),
                coordinate_click_pos=tuple(a_data.get("coordinate_click_pos")) if a_data.get("coordinate_click_pos") else None,
                dynamic_ocr_target_mode=str(a_data.get("dynamic_ocr_target_mode", "roi") or "roi"),
                dynamic_ocr_rules=list(a_data.get("dynamic_ocr_rules", []) or []),
                dynamic_ocr_patterns=list(a_data.get("dynamic_ocr_patterns", []) or []),
                dynamic_ocr_pattern_threshold=float(a_data.get("dynamic_ocr_pattern_threshold", 80.0) or 80.0),
                dynamic_ocr_code=str(a_data.get("dynamic_ocr_code", "return False") or "return False"),
            )
            # Set event notify fields after creation (AutoAction has these fields with defaults)
            event_times_raw = a_data.get("event_notify_times", []) or []
            # Handle backward compatibility: migrate old string format to new dict format
            if event_times_raw and isinstance(event_times_raw[0], str):
                # Old format: ["10:58", "09:10"] -> New format: [{"time": "10:58", "enabled": true}, ...]
                action.event_notify_times = [{"time": time_str, "enabled": True} for time_str in event_times_raw]
                print(f"[DEBUG ToolManager] Migrated event_notify_times from old format: {event_times_raw} -> {action.event_notify_times}")
            else:
                # New format or empty
                action.event_notify_times = list(event_times_raw)
            action.event_prepare_start_s = int(a_data.get("event_prepare_start_s", 300) or 300)
            action.event_prepare_end_s = int(a_data.get("event_prepare_end_s", 60) or 60)
            # Set mask regions
            action.mask_regions = list(a_data.get("mask_regions", []) or [])
            # Set multi-image algorithm testing fields
            action.window_capture_paths = list(a_data.get("window_capture_paths", []) or [])
            action.window_capture_results = dict(a_data.get("window_capture_results", {}) or {})
            action.preprocessing_algorithms = list(a_data.get("preprocessing_algorithms", []) or [])
            # Set preprocessing algorithms UI fields (backward compatibility)
            action.template_matching_algorithms = list(a_data.get("template_matching_algorithms", []) or [])
            action.ocr_algorithms = list(a_data.get("ocr_algorithms", []) or [])
            # Set Event Tracking fields (no event_tracking_enabled - use passive_mode instead)
            action.event_ocr_pattern = str(a_data.get("event_ocr_pattern", "") or "")
            action.event_match_threshold = float(a_data.get("event_match_threshold", 100.0) or 100.0)
            action.event_ocr_engine = str(a_data.get("event_ocr_engine", "auto") or "auto")
            action.event_reappear_timeout_minutes = int(a_data.get("event_reappear_timeout_minutes", 15) or 15)
            # ROI will be taken from Teaching image (teaching_corner_x1, y1, x2, y2)
            # Set Special Event Tracking fields
            action.imperial_guardian_enabled = bool(a_data.get("imperial_guardian_enabled", False))
            action.imperial_guardian_no_player_alert_delay = int(a_data.get("imperial_guardian_no_player_alert_delay", 10) or 10)
            action.imperial_guardian_teaching_corner_x1 = int(a_data.get("imperial_guardian_teaching_corner_x1", 0) or 0)
            action.imperial_guardian_teaching_corner_y1 = int(a_data.get("imperial_guardian_teaching_corner_y1", 0) or 0)
            action.imperial_guardian_teaching_corner_x2 = int(a_data.get("imperial_guardian_teaching_corner_x2", 0) or 0)
            action.imperial_guardian_teaching_corner_y2 = int(a_data.get("imperial_guardian_teaching_corner_y2", 0) or 0)
            action.imperial_guardian_ocr_engine = str(a_data.get("imperial_guardian_ocr_engine", "auto") or "auto")
            action.imperial_guardian_match_threshold = float(a_data.get("imperial_guardian_match_threshold", 70.0) or 70.0)
            action.imperial_guardian_ocr_algorithms = list(a_data.get("imperial_guardian_ocr_algorithms", []) or [])
            action.imperial_guardian_teaching_image_path = str(a_data.get("imperial_guardian_teaching_image_path", "") or "")
            action.golden_invasion_enabled = bool(a_data.get("golden_invasion_enabled", False))
            action.golden_invasion_server_time = str(a_data.get("golden_invasion_server_time", "01:30") or "01:30")
            action.golden_invasion_channel_roi_x1 = int(a_data.get("golden_invasion_channel_roi_x1", 0) or 0)
            action.golden_invasion_channel_roi_y1 = int(a_data.get("golden_invasion_channel_roi_y1", 0) or 0)
            action.golden_invasion_channel_roi_x2 = int(a_data.get("golden_invasion_channel_roi_x2", 0) or 0)
            action.golden_invasion_channel_roi_y2 = int(a_data.get("golden_invasion_channel_roi_y2", 0) or 0)
            action.golden_invasion_channel_ocr_engine = str(a_data.get("golden_invasion_channel_ocr_engine", "auto") or "auto")
            action.golden_invasion_channel_ocr_algorithms = list(a_data.get("golden_invasion_channel_ocr_algorithms", []) or [])
            action.golden_invasion_channel_teaching_image_path = str(a_data.get("golden_invasion_channel_teaching_image_path", "") or "")
            action.golden_invasion_notify_roi_x1 = int(a_data.get("golden_invasion_notify_roi_x1", 0) or 0)
            action.golden_invasion_notify_roi_y1 = int(a_data.get("golden_invasion_notify_roi_y1", 0) or 0)
            action.golden_invasion_notify_roi_x2 = int(a_data.get("golden_invasion_notify_roi_x2", 0) or 0)
            action.golden_invasion_notify_roi_y2 = int(a_data.get("golden_invasion_notify_roi_y2", 0) or 0)
            action.golden_invasion_notify_ocr_engine = str(a_data.get("golden_invasion_notify_ocr_engine", "auto") or "auto")
            action.golden_invasion_notify_ocr_algorithms = list(a_data.get("golden_invasion_notify_ocr_algorithms", []) or [])
            action.golden_invasion_notify_teaching_image_path = str(a_data.get("golden_invasion_notify_teaching_image_path", "") or "")
            action.golden_invasion_match_threshold = float(a_data.get("golden_invasion_match_threshold", 70.0) or 70.0)
            for key, default in MONSTER_INVASION_DEFAULTS.items():
                raw_value = a_data.get(key, default)
                if isinstance(default, bool):
                    value = bool(raw_value)
                elif isinstance(default, int):
                    value = int(raw_value or 0)
                elif isinstance(default, float):
                    value = float(raw_value or default)
                elif isinstance(default, list):
                    value = list(raw_value or [])
                else:
                    value = str(raw_value or default)
                setattr(action, key, value)
            actions.append(action)
        return Tool(
            id=tool_id,  # Pass UUID
            name=data["name"],
            actions=actions,
            loop_enabled=loop_enabled,
            loop_mode=loop_mode,
            loop_count=loop_count,
            loop_pre_delay_100ms=loop_pre_delay_100ms,
            loop_post_delay_100ms=loop_post_delay_100ms,
            stop_on_timeout=stop_on_timeout,
            restart_on_timeout=restart_on_timeout,
            run_lock_mode=run_lock_mode,
            user_input_mode=user_input_mode,
            pause_duration=pause_duration,
            notify_on_timeout=notify_on_timeout,
            block_input_enabled=block_input_enabled,
            block_input_duration=block_input_duration,
            target_window_title=target_window_title,
            window_capture_dir=window_capture_dir,
        )

class ToolManager:
    def __init__(self, tools_dir: str = "tools", images_dir: str = "images"):
        self.tools_dir = tools_dir
        self.images_dir = images_dir
        os.makedirs(tools_dir, exist_ok=True)
    
    def save_tool(self, tool: Tool):
        """Save tool to JSON file by UUID.
        
        Args:
            tool: Tool object to save
        """
        filename = f"{tool.id}.json"
        filepath = os.path.join(self.tools_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(tool.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_tool(self, tool_id: str) -> Optional[Tool]:
        """Load tool from JSON file by UUID.
        
        Args:
            tool_id: UUID of the tool
            
        Returns:
            Tool object or None if not found
        """
        # Try load by UUID first (new format)
        filepath = os.path.join(self.tools_dir, f"{tool_id}.json")
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    return Tool.from_dict(data)
            except Exception as e:
                print(f"Error loading tool {tool_id}: {e}")
                return None
        
        # Fallback: try load by name (old format) for backward compatibility
        sanitized_name = tool_id.replace(' ', '_').replace('/', '_')
        filepath_old = os.path.join(self.tools_dir, f"{sanitized_name}.json")
        
        if os.path.exists(filepath_old):
            try:
                with open(filepath_old, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    # Auto-generate ID if missing
                    if 'id' not in data:
                        data['id'] = str(uuid.uuid4())
                    return Tool.from_dict(data)
            except Exception as e:
                print(f"Error loading tool {tool_id}: {e}")
                return None
        
        return None
    
    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        """Find tool by name.
        
        Args:
            name: Tool name to search for
            
        Returns:
            Tool object or None if not found
        """
        for filename in os.listdir(self.tools_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.tools_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    if data.get("name") == name:
                        return Tool.from_dict(data)
            except Exception:
                continue
        
        return None
    
    def list_tools(self) -> List[Tuple[str, str]]:
        """List all tools.
        
        Returns:
            List of (tool_id, tool_name) tuples
        """
        tools = []
        for filename in os.listdir(self.tools_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.tools_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    tool_id = data.get("id", filename[:-5])  # Fallback to filename without .json
                    tool_name = data.get("name", "Unnamed")
                    tools.append((tool_id, tool_name))
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue
        
        return tools
    
    def delete_tool(self, tool_id: str):
        """Delete tool by UUID.
        
        Args:
            tool_id: UUID of the tool to delete
        """
        # Delete JSON file
        filepath = os.path.join(self.tools_dir, f"{tool_id}.json")
        if os.path.exists(filepath):
            os.remove(filepath)
        
        # Delete teaching images folder
        images_dir = os.path.join(self.images_dir, tool_id)
        if os.path.exists(images_dir):
            import shutil
            shutil.rmtree(images_dir)
    
    def validate_unique_name(self, name: str, exclude_id: Optional[str] = None) -> bool:
        """Check if tool name is unique.
        
        Args:
            name: Tool name to check
            exclude_id: Tool ID to exclude from check (for rename)
            
        Returns:
            True if name is unique, False if duplicate exists
        """
        for filename in os.listdir(self.tools_dir):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(self.tools_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    tool_id = data.get("id")
                    tool_name = data.get("name")
                    
                    # Skip if this is the tool being renamed
                    if tool_id == exclude_id:
                        continue
                    
                    # Check for duplicate name
                    if tool_name == name:
                        return False
            except Exception:
                continue
        
        return True
    
    def copy_tool(self, source_tool_id: str, new_name: str) -> Tool:
        """Copy tool with new name and UUID.
        
        Args:
            source_tool_id: UUID of the source tool to copy
            new_name: Name for the new tool
            
        Returns:
            New Tool object with copied data
            
        Raises:
            ValueError: If source tool not found, name invalid, or name already exists
        """
        # Validate new name
        new_name = str(new_name or "").strip()
        if not new_name:
            raise ValueError("Tool name cannot be empty")
        
        if not self.validate_unique_name(new_name):
            raise ValueError(f"Tool name '{new_name}' already exists")
        
        # Load source tool
        source_tool = self.load_tool(source_tool_id)
        if not source_tool:
            raise ValueError(f"Source tool with ID '{source_tool_id}' not found")
        
        # Generate new UUID for copied tool
        new_tool_id = str(uuid.uuid4())
        
        # Deep copy all actions with updated image paths
        copied_actions = []
        for action in source_tool.actions:
            # Create new action with same data
            copied_action = AutoAction(
                name=action.name,
                purpose=action.purpose,
                action_type=action.action_type,
                mode=action.mode,
                value=action.value,
                image_path=action.image_path,
                enable_post_key_image_check=getattr(action, "enable_post_key_image_check", False),
                post_key_check_delay=getattr(action, "post_key_check_delay", 1.0),
                post_key_retry_count=getattr(action, "post_key_retry_count", 0),
                enable_post_click_image_check=getattr(action, "enable_post_click_image_check", False),
                post_click_check_delay=getattr(action, "post_click_check_delay", 1.0),
                post_click_retry_count=getattr(action, "post_click_retry_count", 0),
                post_click_image_path=getattr(action, "post_click_image_path", None),
                post_click_match_threshold=getattr(action, "post_click_match_threshold", 0.4),
                click_x=action.click_x,
                click_y=action.click_y,
                alt_click=getattr(action, "alt_click", False),
                match_threshold=getattr(action, "match_threshold", 0.4),
                continue_on_timeout=getattr(action, "continue_on_timeout", False),
                multiscale_enabled=getattr(action, "multiscale_enabled", True),
                multiscale_min=getattr(action, "multiscale_min", 0.70),
                multiscale_max=getattr(action, "multiscale_max", 1.30),
                multiscale_step=getattr(action, "multiscale_step", 0.05),
                delay=action.delay,
                read_data=getattr(action, 'read_data', False),
                ocr_engine=getattr(action, "ocr_engine", "auto"),
                ocr_bright_on_dark=getattr(action, "ocr_bright_on_dark", False),
                preprocessing_config=getattr(action, "preprocessing_config", None),
                gemini_enabled=getattr(action, "gemini_enabled", False),
                prompt=getattr(action, "prompt", ""),
                gemini_prompt=getattr(action, "gemini_prompt", ""),
                gemini_timeout=getattr(action, "gemini_timeout", 10.0),
                timeout=getattr(action, 'timeout', 30.0),
                check_interval=getattr(action, 'check_interval', 1.0),
                notification_enabled=getattr(action, "notification_enabled", False),
                notification_filter_keywords=getattr(action, "notification_filter_keywords", ""),
                notification_dedup_minutes=getattr(action, "notification_dedup_minutes", 1),
                goto_step_enabled=getattr(action, "goto_step_enabled", False),
                goto_step_index=getattr(action, "goto_step_index", 0),
                timeout_goto_enabled=getattr(action, "timeout_goto_enabled", False),
                timeout_goto_step_index=getattr(action, "timeout_goto_step_index", 0),
                passive_mode=getattr(action, "passive_mode", "detect_image"),
                passive_sample_every=getattr(action, "passive_sample_every", 1),
                passive_only_new_frame=getattr(action, "passive_only_new_frame", True),
                passive_cancel_old=getattr(action, "passive_cancel_old", False),
                passive_keywords=getattr(action, "passive_keywords", ""),
                passive_detect_timeout=getattr(action, "passive_detect_timeout", 30.0),
                passive_detect_threshold=getattr(action, "passive_detect_threshold", 0.4),
                use_fixed_roi=getattr(action, "use_fixed_roi", False),
                roi_x=getattr(action, "roi_x", 0),
                roi_y=getattr(action, "roi_y", 0),
                roi_w=getattr(action, "roi_w", 200),
                roi_h=getattr(action, "roi_h", 100),
                teaching_corner_x1=getattr(action, "teaching_corner_x1", None),
                teaching_corner_y1=getattr(action, "teaching_corner_y1", None),
                teaching_corner_x2=getattr(action, "teaching_corner_x2", None),
                teaching_corner_y2=getattr(action, "teaching_corner_y2", None),
                teaching_window_width=getattr(action, "teaching_window_width", None),
                teaching_window_height=getattr(action, "teaching_window_height", None),
                post_click_teaching_corner_x1=getattr(action, "post_click_teaching_corner_x1", None),
                post_click_teaching_corner_y1=getattr(action, "post_click_teaching_corner_y1", None),
                post_click_teaching_corner_x2=getattr(action, "post_click_teaching_corner_x2", None),
                post_click_teaching_corner_y2=getattr(action, "post_click_teaching_corner_y2", None),
                post_click_teaching_window_width=getattr(action, "post_click_teaching_window_width", None),
                post_click_teaching_window_height=getattr(action, "post_click_teaching_window_height", None),
                ocr_upscale_enabled=getattr(action, "ocr_upscale_enabled", True),
                ocr_upscale_factor=getattr(action, "ocr_upscale_factor", 2.0),
                ocr_enhance_contrast=getattr(action, "ocr_enhance_contrast", True),
                ocr_sharpen=getattr(action, "ocr_sharpen", True),
                ocr_denoise=getattr(action, "ocr_denoise", False),
                click_by_coordinate=getattr(action, "click_by_coordinate", False),
                coordinate_click_pos=getattr(action, "coordinate_click_pos", None),
                dynamic_ocr_target_mode=getattr(action, "dynamic_ocr_target_mode", "roi"),
                dynamic_ocr_rules=list(getattr(action, "dynamic_ocr_rules", []) or []),
                dynamic_ocr_patterns=list(getattr(action, "dynamic_ocr_patterns", []) or []),
                dynamic_ocr_code=getattr(action, "dynamic_ocr_code", "return False"),
            )
            
            # Copy additional fields that are set after creation
            copied_action.event_notify_times = list(getattr(action, "event_notify_times", []) or [])
            copied_action.event_prepare_start_s = getattr(action, "event_prepare_start_s", 300)
            copied_action.event_prepare_end_s = getattr(action, "event_prepare_end_s", 60)
            copied_action.mask_regions = list(getattr(action, "mask_regions", []) or [])
            copied_action.window_capture_paths = list(getattr(action, "window_capture_paths", []) or [])
            copied_action.window_capture_results = dict(getattr(action, "window_capture_results", {}) or {})
            copied_action.preprocessing_algorithms = list(getattr(action, "preprocessing_algorithms", []) or [])
            copied_action.template_matching_algorithms = list(getattr(action, "template_matching_algorithms", []) or [])
            copied_action.ocr_algorithms = list(getattr(action, "ocr_algorithms", []) or [])
            # Copy Event Tracking fields (no event_tracking_enabled - use passive_mode instead)
            copied_action.event_ocr_pattern = getattr(action, "event_ocr_pattern", "")
            copied_action.event_match_threshold = getattr(action, "event_match_threshold", 100.0)
            copied_action.event_ocr_engine = getattr(action, "event_ocr_engine", "auto")
            copied_action.event_reappear_timeout_minutes = getattr(action, "event_reappear_timeout_minutes", 15)
            # Copy Special Event Tracking fields
            copied_action.imperial_guardian_enabled = getattr(action, "imperial_guardian_enabled", False)
            copied_action.imperial_guardian_no_player_alert_delay = getattr(action, "imperial_guardian_no_player_alert_delay", 10)
            copied_action.imperial_guardian_teaching_corner_x1 = getattr(action, "imperial_guardian_teaching_corner_x1", 0)
            copied_action.imperial_guardian_teaching_corner_y1 = getattr(action, "imperial_guardian_teaching_corner_y1", 0)
            copied_action.imperial_guardian_teaching_corner_x2 = getattr(action, "imperial_guardian_teaching_corner_x2", 0)
            copied_action.imperial_guardian_teaching_corner_y2 = getattr(action, "imperial_guardian_teaching_corner_y2", 0)
            copied_action.imperial_guardian_teaching_image_path = getattr(action, "imperial_guardian_teaching_image_path", "")
            copied_action.imperial_guardian_ocr_engine = getattr(action, "imperial_guardian_ocr_engine", "auto")
            copied_action.imperial_guardian_match_threshold = getattr(action, "imperial_guardian_match_threshold", 70.0)
            copied_action.imperial_guardian_ocr_algorithms = list(getattr(action, "imperial_guardian_ocr_algorithms", []) or [])
            copied_action.golden_invasion_enabled = getattr(action, "golden_invasion_enabled", False)
            copied_action.golden_invasion_server_time = getattr(action, "golden_invasion_server_time", "01:30")
            copied_action.golden_invasion_channel_roi_x1 = getattr(action, "golden_invasion_channel_roi_x1", 0)
            copied_action.golden_invasion_channel_roi_y1 = getattr(action, "golden_invasion_channel_roi_y1", 0)
            copied_action.golden_invasion_channel_roi_x2 = getattr(action, "golden_invasion_channel_roi_x2", 0)
            copied_action.golden_invasion_channel_roi_y2 = getattr(action, "golden_invasion_channel_roi_y2", 0)
            copied_action.golden_invasion_channel_ocr_engine = getattr(action, "golden_invasion_channel_ocr_engine", "auto")
            copied_action.golden_invasion_channel_ocr_algorithms = list(getattr(action, "golden_invasion_channel_ocr_algorithms", []) or [])
            copied_action.golden_invasion_channel_teaching_image_path = getattr(action, "golden_invasion_channel_teaching_image_path", "")
            copied_action.golden_invasion_notify_roi_x1 = getattr(action, "golden_invasion_notify_roi_x1", 0)
            copied_action.golden_invasion_notify_roi_y1 = getattr(action, "golden_invasion_notify_roi_y1", 0)
            copied_action.golden_invasion_notify_roi_x2 = getattr(action, "golden_invasion_notify_roi_x2", 0)
            copied_action.golden_invasion_notify_roi_y2 = getattr(action, "golden_invasion_notify_roi_y2", 0)
            copied_action.golden_invasion_notify_ocr_engine = getattr(action, "golden_invasion_notify_ocr_engine", "auto")
            copied_action.golden_invasion_notify_ocr_algorithms = list(getattr(action, "golden_invasion_notify_ocr_algorithms", []) or [])
            copied_action.golden_invasion_notify_teaching_image_path = getattr(action, "golden_invasion_notify_teaching_image_path", "")
            copied_action.golden_invasion_match_threshold = getattr(action, "golden_invasion_match_threshold", 70.0)
            for key, default in MONSTER_INVASION_DEFAULTS.items():
                value = getattr(action, key, default)
                if isinstance(default, list):
                    value = list(value or [])
                setattr(copied_action, key, value)
            
            # Update image path to use new tool ID
            if copied_action.image_path and source_tool_id in copied_action.image_path:
                copied_action.image_path = copied_action.image_path.replace(source_tool_id, new_tool_id)
            for attr in (
                "post_click_image_path",
                "imperial_guardian_teaching_image_path",
                "golden_invasion_channel_teaching_image_path",
                "golden_invasion_notify_teaching_image_path",
                "monster_invasion_channel_teaching_image_path",
                "monster_invasion_notify_teaching_image_path",
            ):
                path = getattr(copied_action, attr, "")
                if path and source_tool_id in path:
                    setattr(copied_action, attr, path.replace(source_tool_id, new_tool_id))
            
            copied_actions.append(copied_action)
        
        # Create new tool with copied data
        copied_tool = Tool(
            id=new_tool_id,
            name=new_name,
            actions=copied_actions,
            loop_enabled=source_tool.loop_enabled,
            loop_mode=source_tool.loop_mode,
            loop_count=source_tool.loop_count,
            loop_pre_delay_100ms=source_tool.loop_pre_delay_100ms,
            loop_post_delay_100ms=source_tool.loop_post_delay_100ms,
            stop_on_timeout=source_tool.stop_on_timeout,
            restart_on_timeout=source_tool.restart_on_timeout,
            run_lock_mode=source_tool.run_lock_mode,
            user_input_mode=source_tool.user_input_mode,
            pause_duration=source_tool.pause_duration,
            notify_on_timeout=source_tool.notify_on_timeout,
            block_input_enabled=source_tool.block_input_enabled,
            block_input_duration=source_tool.block_input_duration,
            target_window_title=getattr(source_tool, "target_window_title", ""),
            window_capture_dir=getattr(source_tool, "window_capture_dir", ""),
        )
        
        # Copy teaching images if they exist
        source_images_dir = os.path.join(self.images_dir, source_tool_id)
        if os.path.exists(source_images_dir):
            target_images_dir = os.path.join(self.images_dir, new_tool_id)
            try:
                import shutil
                shutil.copytree(source_images_dir, target_images_dir)
            except Exception as e:
                # If image copy fails, still save the tool but log the error
                print(f"Warning: Failed to copy images: {e}")
        
        # Save the copied tool
        self.save_tool(copied_tool)
        
        return copied_tool

