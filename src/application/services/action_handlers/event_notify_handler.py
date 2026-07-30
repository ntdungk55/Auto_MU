"""Event notify (alarm/gate) action handler."""

from __future__ import annotations

import time
from datetime import datetime, timedelta

from domain.entities.action import AutoAction
from domain.entities.execution_result import ActionResult
from domain.value_objects.action_type import ActionType
from .base import IActionHandler


class EventNotifyActionHandler(IActionHandler):
    """Handler for EVENT_NOTIFY actions.

    Note: clean-architecture handlers do not currently emit detailed logs;
    the legacy SystemExecutor path does.
    """

    def can_handle(self, action: AutoAction) -> bool:
        return action.action_type == ActionType.EVENT_NOTIFY

    def execute(self, action: AutoAction) -> ActionResult:
        now_ts = int(time.time())
        now_dt = datetime.fromtimestamp(now_ts)

        times_raw = list(getattr(action, "event_notify_times", []) or [])
        prepare_start_s = int(getattr(action, "event_prepare_start_s", 300) or 300)
        prepare_end_s = int(getattr(action, "event_prepare_end_s", 60) or 60)

        # Filter only enabled times and extract time strings
        times = []
        for t in times_raw:
            if isinstance(t, dict):
                # New format: {"time": "10:58", "enabled": true}
                if t.get("enabled", True):  # Default enabled if missing
                    times.append(t.get("time", ""))
            else:
                # Old format: "10:58" (always enabled)
                times.append(str(t))

        success = False
        if times and prepare_start_s > prepare_end_s and prepare_start_s >= 0 and prepare_end_s >= 0:
            for t in times:
                t = str(t or "").strip()
                if not t:
                    continue
                try:
                    hh_str, mm_str = t.split(":")
                    hh = int(hh_str)
                    mm = int(mm_str)
                    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
                        continue
                except Exception:
                    continue

                base_today = now_dt.replace(hour=hh, minute=mm, second=0, microsecond=0)
                for day_offset in (0, 1):
                    event_ts = int((base_today + timedelta(days=day_offset)).timestamp())
                    start_ts = event_ts - prepare_start_s
                    end_ts = event_ts - prepare_end_s
                    if start_ts <= now_ts <= end_ts:
                        success = True
                        break
                if success:
                    break

        return ActionResult(
            success=success,
            action_name=action.name,
            action_type=action.action_type,
            timed_out=not success,
        )

