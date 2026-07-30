"""Event Notify Handler - EVENT_NOTIFY logic extracted from SystemExecutor."""

import time
import traceback
from datetime import datetime, timedelta
from typing import Callable, Optional


class EventNotifyHandler:
    """Handles EVENT_NOTIFY action: checks if current time is within event preparation window."""

    def __init__(self, ui_log_func: Callable[[str], None], escape_html_fn: Callable[[str], str]):
        """Initialize EventNotifyHandler.

        Args:
            ui_log_func: Function to log UI messages
            escape_html_fn: Function to escape HTML special characters
        """
        self._ui_log = ui_log_func
        self._escape_html = escape_html_fn

    def execute(self, action, engine=None) -> bool:
        """Execute EVENT_NOTIFY action.

        Checks if current time is within the preparation window for any configured event time.

        Args:
            action: AutoAction with event_notify settings
            engine: Optional engine reference for stop checks

        Returns:
            True if within preparation window, False otherwise
        """
        try:
            return self._execute_internal(action, engine)
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            print(f"[EventNotify] FATAL ERROR: {error_msg}")
            print(f"[EventNotify] TRACEBACK:\n{error_trace}")
            self._ui_log(f"<b style='color:red;'>[Event]</b> ❌ Lỗi nghiêm trọng: {error_msg}")
            self._ui_log(f"<pre style='color:red;font-size:10px;'>{self._escape_html(error_trace)}</pre>")
            return False

    def _execute_internal(self, action, engine) -> bool:
        """Internal implementation of EVENT_NOTIFY execution."""
        # Parse action attributes
        try:
            event_name = str(getattr(action, "name", "") or "").strip() or "Thông báo sự kiện"
            times_raw = list(getattr(action, "event_notify_times", []) or [])
            prepare_start_s = int(getattr(action, "event_prepare_start_s", 300) or 300)
            prepare_end_s = int(getattr(action, "event_prepare_end_s", 60) or 60)
        except Exception as e:
            print(f"[EventNotify] ERROR parsing attributes: {e}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi đọc cấu hình: {e}")
            return False

        # Filter enabled times (support both dict format and string format)
        try:
            times = []
            for t in times_raw:
                if isinstance(t, dict):
                    # New format: {"time": "10:58", "enabled": true}
                    if t.get("enabled", True):
                        times.append(t.get("time", ""))
                else:
                    # Old format: "10:58" (always enabled)
                    times.append(str(t))
            print(f"[EventNotify DEBUG] Raw times: {times_raw}")
            print(f"[EventNotify DEBUG] Filtered enabled times: {times}")
        except Exception as e:
            print(f"[EventNotify] ERROR filtering times: {e}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi lọc thời gian: {e}")
            return False

        # Validate config
        try:
            if not times:
                self._ui_log(
                    "<b style='color:red;'>[Event]</b> ❌ Thất bại: không có mốc thời gian nào được enable. "
                    "Vui lòng mở cài đặt action và enable ít nhất 1 mốc thời gian bằng cách check checkbox."
                )
                return False
            if prepare_start_s <= prepare_end_s or prepare_start_s < 0 or prepare_end_s < 0:
                self._ui_log(
                    "<b style='color:red;'>[Event]</b> Thất bại: cấu hình sai "
                    f"(start={prepare_start_s}s phải > end={prepare_end_s}s)"
                )
                return False
        except Exception as e2:
            print(f"[EventNotify] ERROR validating config: {e2}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi validate: {e2}")
            return False

        # Get current time
        try:
            now_ts = int(time.time())
            now_dt = datetime.fromtimestamp(now_ts)
        except Exception as e3:
            print(f"[EventNotify] ERROR getting time: {e3}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi lấy thời gian: {e3}")
            return False

        # Log check info
        try:
            self._ui_log(
                f"<b>[Event]</b> Check: <code>{self._escape_html(event_name)}</code> | "
                f"mốc={len(times)} | window={prepare_start_s}s→{prepare_end_s}s | "
                f"now={now_dt.strftime('%H:%M:%S')}"
            )
        except Exception as e4:
            print(f"[EventNotify] ERROR logging check info: {e4}")

        # Evaluate windows
        matched = None
        next_window_start = None

        try:
            for idx, t in enumerate(times):
                try:
                    t = str(t or "").strip()
                    if not t:
                        continue
                    try:
                        hh_str, mm_str = t.split(":")
                        hh = int(hh_str)
                        mm = int(mm_str)
                        if hh < 0 or hh > 23 or mm < 0 or mm > 59:
                            continue
                    except Exception as parse_err:
                        print(f"[EventNotify] ERROR parsing time[{idx}] '{t}': {parse_err}")
                        continue

                    try:
                        base_today = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
                        for day_offset in (0, 1):
                            try:
                                event_dt = base_today + timedelta(days=day_offset)
                                event_ts = int(event_dt.timestamp())
                                start_ts = event_ts - prepare_start_s
                                end_ts = event_ts - prepare_end_s

                                start_dt_dbg = datetime.fromtimestamp(start_ts)
                                end_dt_dbg = datetime.fromtimestamp(end_ts)
                                print(f"[EventNotify DEBUG] Event {t} (day+{day_offset}): window {start_dt_dbg.strftime('%H:%M:%S')} - {end_dt_dbg.strftime('%H:%M:%S')}, now_ts={now_ts}, start_ts={start_ts}, end_ts={end_ts}")
                                print(f"[EventNotify DEBUG] Check: {start_ts} <= {now_ts} <= {end_ts} = {start_ts <= now_ts <= end_ts}")

                                if start_ts <= now_ts <= end_ts:
                                    matched = (event_ts, start_ts, end_ts, t)
                                    break

                                if now_ts < start_ts:
                                    if next_window_start is None or start_ts < next_window_start:
                                        next_window_start = start_ts
                            except Exception as day_err:
                                print(f"[EventNotify] ERROR calculating day_offset={day_offset} for time[{idx}] '{t}': {day_err}")
                                print(traceback.format_exc())
                                continue

                        if matched:
                            break
                    except Exception as calc_err:
                        print(f"[EventNotify] ERROR calculating windows for time[{idx}] '{t}': {calc_err}")
                        print(traceback.format_exc())
                        continue
                except Exception as time_err:
                    print(f"[EventNotify] ERROR processing time[{idx}]: {time_err}")
                    print(traceback.format_exc())
                    continue
        except Exception as e5:
            print(f"[EventNotify] ERROR evaluating windows: {e5}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi tính toán cửa sổ: {e5}")
            return False

        # Handle result
        try:
            result = self._build_result(matched, next_window_start, now_dt)
            self._apply_delay(action, engine)
            return result
        except Exception as e6:
            print(f"[EventNotify] ERROR handling result: {e6}")
            print(traceback.format_exc())
            self._ui_log(f"<b style='color:red;'>[Event]</b> Lỗi xử lý kết quả: {e6}")
            return False

    def _build_result(self, matched: Optional[tuple], next_window_start: Optional[int], now_dt: datetime) -> bool:
        """Build and log the result based on window matching."""
        if matched:
            event_ts, start_ts, end_ts, label = matched
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)
            event_dt = datetime.fromtimestamp(event_ts)
            self._ui_log(
                f"<b style='color:green;'>[Event]</b> ✓ Trong khoảng cho phép: "
                f"<code>{start_dt.strftime('%H:%M:%S')}</code> - <code>{end_dt.strftime('%H:%M:%S')}</code> "
                f"(mốc <code>{label}</code>, event <code>{event_dt.strftime('%H:%M')}</code>)"
            )
            return True

        if next_window_start is not None:
            nxt = datetime.fromtimestamp(int(next_window_start))
            self._ui_log(
                f"<b style='color:red;'>[Event]</b> ✗ Ngoài khoảng cho phép → Timeout<br>"
                f"<span style='color:gray;'>Hiện tại: <code>{now_dt.strftime('%H:%M:%S')}</code> | "
                f"Cửa sổ kế tiếp bắt đầu: <code>{nxt.strftime('%H:%M:%S')}</code></span>"
            )
        else:
            self._ui_log(
                f"<b style='color:red;'>[Event]</b> ✗ Ngoài khoảng cho phép → Timeout<br>"
                f"<span style='color:gray;'>Hiện tại: <code>{now_dt.strftime('%H:%M:%S')}</code> | "
                f"Đã qua tất cả cửa sổ trong ngày. Cửa sổ tiếp theo sẽ là ngày mai.</span>"
            )
        return False

    def _apply_delay(self, action, engine) -> None:
        """Apply post-execution delay if configured."""
        try:
            delay = float(getattr(action, "delay", 0.0) or 0.0)
            if delay <= 0:
                return
            if engine and hasattr(engine, "is_running"):
                sleep_end = time.time() + delay
                while time.time() < sleep_end:
                    if not engine.is_running or getattr(engine, "should_stop_completely", False):
                        break
                    remaining = sleep_end - time.time()
                    time.sleep(min(0.1, max(0.0, remaining)))
            else:
                time.sleep(delay)
        except Exception as delay_err:
            print(f"[EventNotify] ERROR applying delay: {delay_err}")
