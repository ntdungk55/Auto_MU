"""AutoAction entity - Single Source of Truth for action data."""

from dataclasses import dataclass, field
from typing import Optional
from ..value_objects.action_type import ActionType


@dataclass
class AutoAction:
    """Domain entity for automation action."""
    
    name: str
    action_type: ActionType
    
    # Timing
    timeout: float = 30.0
    delay: float = 0.0
    check_interval: float = 0.5
    
    # Goto on success
    goto_step_enabled: bool = False
    goto_step_index: int = 0
    
    # Goto on timeout
    timeout_goto_enabled: bool = False
    timeout_goto_step_index: int = 0
    
    # Keyboard specific
    key: str = ""
    modifiers: list[str] = field(default_factory=list)
    
    # Mouse/Image specific
    image_path: str = ""
    threshold: float = 0.8
    click_by_coordinate: bool = False
    click_x: int = 0
    click_y: int = 0
    teaching_corners: Optional[list] = None
    
    # Fixed ROI
    fixed_roi_enabled: bool = False
    fixed_roi: Optional[tuple[int, int, int, int]] = None
    
    # OCR preprocessing
    ocr_preprocessing_enabled: bool = False
    ocr_preprocessing_config: Optional[dict] = None
    
    # Gemini
    gemini_enabled: bool = False
    gemini_prompt: str = ""
    
    # Notification
    send_telegram: bool = False
    notification_filter_enabled: bool = False
    notification_filter_keywords: str = ""

    # Event notify (Alarm/Gate)
    # List of event times in a day as "HH:MM"
    event_notify_times: list[str] = field(default_factory=list)
    # Start of preparation window before event time (seconds)
    event_prepare_start_s: int = 300
    # End of preparation window before event time (seconds)
    event_prepare_end_s: int = 60
    
    @classmethod
    def serializable_fields(cls) -> list[str]:
        """SSOT: All fields that should be serialized."""
        return [
            'name', 'action_type', 'timeout', 'delay', 'check_interval',
            'goto_step_enabled', 'goto_step_index',
            'timeout_goto_enabled', 'timeout_goto_step_index',
            'key', 'modifiers', 'image_path', 'threshold',
            'click_by_coordinate', 'click_x', 'click_y', 'teaching_corners',
            'fixed_roi_enabled', 'fixed_roi',
            'ocr_preprocessing_enabled', 'ocr_preprocessing_config',
            'gemini_enabled', 'gemini_prompt',
            'send_telegram', 'notification_filter_enabled', 'notification_filter_keywords',
            'event_notify_times', 'event_prepare_start_s', 'event_prepare_end_s',
        ]
