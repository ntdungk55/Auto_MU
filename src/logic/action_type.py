from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ActionMode(Enum):
    ACTIVE = "Chủ động"
    PASSIVE = "Thụ động"


class PassiveMode(Enum):
    READ_DATA = "Đọc dữ liệu"
    DETECT_IMAGE = "Phát hiện hình ảnh"


class ActionType(Enum):
    KEYBOARD = "Ấn Phím"
    MOUSE_CLICK = "Click Chuột"
    IMAGE_DETECT = "Bắt Hình Ảnh"
    DYNAMIC_OCR_CONDITION = "Dynamic OCR Condition"
    READ_PASSIVE = "Đọc thụ động"
    WAIT = "Chờ"
    EVENT_NOTIFY = "Thông báo sự kiện"


@dataclass
class AutoAction:
    name: str
    purpose: str
    action_type: ActionType
    mode: ActionMode
    value: str = ""
    text_input_enabled: bool = False
    image_path: Optional[str] = None
    yolo_enabled: bool = False
    yolo_model_path: str = ""
    yolo_confidence: float = 0.25
    yolo_iou: float = 0.45
    yolo_class_ids: list[int] = field(default_factory=list)
    enable_post_key_image_check: bool = False
    post_key_check_delay: float = 1.0
    post_key_retry_count: int = 0
    enable_post_click_image_check: bool = False
    post_click_check_delay: float = 1.0
    post_click_retry_count: int = 0
    post_click_image_path: Optional[str] = None
    post_click_match_threshold: float = 0.4
    click_x: Optional[int] = None
    click_y: Optional[int] = None
    alt_click: bool = False
    match_threshold: float = 0.4
    continue_on_timeout: bool = False
    multiscale_enabled: bool = True
    multiscale_min: float = 0.70
    multiscale_max: float = 1.30
    multiscale_step: float = 0.05
    delay: float = 1.0
    read_data: bool = False
    ocr_engine: str = "auto"
    ocr_bright_on_dark: bool = False
    preprocessing_config: Optional[dict] = None
    gemini_enabled: bool = False
    prompt: str = ""
    gemini_prompt: str = ""
    gemini_timeout: float = 10.0
    timeout: float = 5.0
    check_interval: float = 1.0
    notification_enabled: bool = False
    notification_filter_keywords: str = ""
    notification_dedup_minutes: int = 1
    goto_step_enabled: bool = False
    goto_step_index: int = 0
    timeout_goto_enabled: bool = False
    timeout_goto_step_index: int = 0
    passive_mode: str = "detect_image"
    passive_sample_every: int = 1
    passive_only_new_frame: bool = True
    passive_cancel_old: bool = False
    passive_keywords: str = ""
    passive_detect_timeout: float = 30.0
    passive_detect_threshold: float = 0.4
    use_fixed_roi: bool = False
    roi_x: int = 0
    roi_y: int = 0
    roi_w: int = 200
    roi_h: int = 100
    teaching_corner_x1: Optional[int] = None
    teaching_corner_y1: Optional[int] = None
    teaching_corner_x2: Optional[int] = None
    teaching_corner_y2: Optional[int] = None
    ocr_upscale_enabled: bool = True
    ocr_upscale_factor: float = 2.0
    ocr_enhance_contrast: bool = True
    ocr_sharpen: bool = True
    ocr_denoise: bool = False
    click_by_coordinate: bool = False
    coordinate_click_pos: Optional[tuple] = None
    dynamic_ocr_target_mode: str = "roi"
    dynamic_ocr_rules: list[dict] = field(default_factory=list)
    dynamic_ocr_patterns: list[str] = field(default_factory=list)
    dynamic_ocr_pattern_threshold: float = 80.0
    dynamic_ocr_code: str = "return False"
    dynamic_ocr_code_comment: str = ""

    event_notify_times: list = field(default_factory=list)
    event_prepare_start_s: int = 300
    event_prepare_end_s: int = 60

    mask_regions: list[dict] = field(default_factory=list)

    window_capture_paths: list[str] = field(default_factory=list)
    window_capture_results: dict[str, float] = field(default_factory=dict)
    preprocessing_algorithms: list[dict] = field(default_factory=list)

    template_matching_algorithms: list[dict] = field(default_factory=list)
    ocr_algorithms: list[dict] = field(default_factory=list)

    teaching_window_width: Optional[int] = None
    teaching_window_height: Optional[int] = None
    post_click_teaching_corner_x1: Optional[int] = None
    post_click_teaching_corner_y1: Optional[int] = None
    post_click_teaching_corner_x2: Optional[int] = None
    post_click_teaching_corner_y2: Optional[int] = None
    post_click_teaching_window_width: Optional[int] = None
    post_click_teaching_window_height: Optional[int] = None

    event_ocr_pattern: str = ""
    event_match_threshold: float = 100.0
    event_ocr_engine: str = "auto"
    event_reappear_timeout_minutes: int = 15

    imperial_guardian_enabled: bool = False
    imperial_guardian_no_player_alert_delay: int = 10
    imperial_guardian_teaching_image_path: str = ""
    imperial_guardian_teaching_corner_x1: int = 0
    imperial_guardian_teaching_corner_y1: int = 0
    imperial_guardian_teaching_corner_x2: int = 0
    imperial_guardian_teaching_corner_y2: int = 0
    imperial_guardian_ocr_engine: str = "auto"
    imperial_guardian_match_threshold: float = 70.0
    imperial_guardian_ocr_algorithms: list = None

    golden_invasion_enabled: bool = False
    golden_invasion_server_time: str = "01:30"
    golden_invasion_channel_roi_x1: int = 0
    golden_invasion_channel_roi_y1: int = 0
    golden_invasion_channel_roi_x2: int = 0
    golden_invasion_channel_roi_y2: int = 0
    golden_invasion_channel_ocr_engine: str = "auto"
    golden_invasion_channel_ocr_algorithms: list = None
    golden_invasion_channel_teaching_image_path: str = ""
    golden_invasion_notify_roi_x1: int = 0
    golden_invasion_notify_roi_y1: int = 0
    golden_invasion_notify_roi_x2: int = 0
    golden_invasion_notify_roi_y2: int = 0
    golden_invasion_notify_ocr_engine: str = "auto"
    golden_invasion_notify_ocr_algorithms: list = None
    golden_invasion_notify_teaching_image_path: str = ""
    golden_invasion_match_threshold: float = 70.0

    monster_invasion_enabled: bool = False
    monster_invasion_channel_roi_x1: int = 0
    monster_invasion_channel_roi_y1: int = 0
    monster_invasion_channel_roi_x2: int = 0
    monster_invasion_channel_roi_y2: int = 0
    monster_invasion_channel_ocr_engine: str = "auto"
    monster_invasion_channel_ocr_algorithms: list = None
    monster_invasion_channel_teaching_image_path: str = ""
    monster_invasion_notify_roi_x1: int = 0
    monster_invasion_notify_roi_y1: int = 0
    monster_invasion_notify_roi_x2: int = 0
    monster_invasion_notify_roi_y2: int = 0
    monster_invasion_notify_ocr_engine: str = "auto"
    monster_invasion_notify_ocr_algorithms: list = None
    monster_invasion_notify_teaching_image_path: str = ""
    monster_invasion_match_threshold: float = 70.0
    monster_invasion_golden_invasion_enabled: bool = False
    monster_invasion_golden_invasion_server_time: str = "01:30"
    monster_invasion_white_wizard_red_dragon_enabled: bool = False
