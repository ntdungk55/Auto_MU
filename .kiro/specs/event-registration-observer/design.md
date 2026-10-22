# Event Registration and Location Observer - Technical Design

## 1. Impact Analysis

### 1.1. Files to add

| File                                      | Responsibility |
|-------------------------------------------|----------------|
| `src/logic/event_observer.py`             | Pure location matching, transition detection, baseline and runtime state machine. |
| `src/logic/event_catalog.py`              | Static map catalog with `{id, name}` values. |
| `src/ui/event_management_dialog.py`       | Event list window, inline prompt editing, enable/status columns, create/edit/delete flows. |
| `src/ui/event_settings_dialog.py`          | Create/edit event dialog with observer tabs and Location Observer form. |
| `tests/test_event_observer.py`             | Unit tests for location matching and transitions. |
| `tests/test_event_registration_persistence.py` | Persistence and backward/invalid data tests. |
| `tests/test_event_management_dialog.py`    | UI behavior tests for list editing and validation. |

### 1.2. Files to modify

| File                                      | Required change |
|-------------------------------------------|-----------------|
| `src/ai_control/chat_message_queue.py`    | Preserve event identity and prevent duplicate event prompts while queued or active. |
| `src/ui/gemini_chat_widget.py`            | Add the event-list button left of the automatic bubble/button, own the observer worker, open dialogs, route fired prompts to the shared queue, and update row statuses. |
| `main.py`                                 | Add load/save callbacks for per-game-process event registrations and pass them to `GeminiChatWidget`. |
| `tests/test_chat_message_queue.py`        | Verify active and pending event duplicate behavior. |
| `tests/test_gemini_chat_activity_ui.py`   | Verify button placement, event queue routing, and UI-thread signal handling. |

### 1.3. Existing integration points

- `GeminiChatWidget` already owns `_message_queue`, `_auto_timer`, the automatic button, queue bubble, AI busy state, and per-process rule callbacks.
- `ChatMessageQueue.enqueue_automatic(text, rule_id)` already rejects duplicate pending automatic messages. Event messages should use the same dispatch path but carry an event-specific identity.
- `src/ai_control/servers/keyboard.py` exposes `get_current_character_map`, backed by `get_current_character_map(target)`, which returns validated `map` and `position` data or `success=false`.
- `MainWindow._load_ai_auto_messages_for_target` and `_save_ai_auto_messages_for_target` establish the existing persistence pattern keyed by selected game window/process.
- `GeminiChatWidget` already uses `QueuedConnection` for AI turn completion and has an existing background AI worker pattern.

## 2. Architecture

```text
┌──────────────────────────────┐
│ GeminiChatWidget              │
│ event button + status table   │
└──────────────┬───────────────┘
               │ starts/stops
               ▼
┌──────────────────────────────┐
│ LocationObserverWorker        │  background thread
│ MCP polling + focus check     │
└──────────────┬───────────────┘
               │ queued signals
               ▼
┌──────────────────────────────┐
│ LocationEventObserver         │  pure logic
│ baseline + state machines     │
└──────────────┬───────────────┘
               │ EventTrigger / StatusUpdate
               ▼
┌──────────────────────────────┐
│ GeminiChatWidget UI thread    │
│ queue or ignore if game focus │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ ChatMessageQueue              │
│ existing AI dispatch path     │
└──────────────────────────────┘
```

The observer worker must not update Qt widgets. It emits immutable result objects. `GeminiChatWidget` receives the signals through `Qt.ConnectionType.QueuedConnection` and updates the table/status and shared AI queue on the UI thread.

## 3. Data Model

### 3.1. Static map catalog

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class MapDefinition:
    id: int
    name: str


MAP_CATALOG: tuple[MapDefinition, ...] = (
    MapDefinition(id=1, name="Lorencia"),
)
```

The catalog is the source for the UI dropdown. Matching normalizes case and surrounding whitespace. Unknown map IDs/names cannot be created through the UI.

### 3.2. Persisted event configuration

```python
from dataclasses import dataclass
from typing import Literal

TriggerMode = Literal["enter", "exit", "source_to_destination"]


@dataclass
class LocationCondition:
    map_id: int
    map_name: str
    use_coordinates: bool = False
    min_x: int | None = None
    max_x: int | None = None
    min_y: int | None = None
    max_y: int | None = None


@dataclass
class RegisteredEvent:
    event_id: str
    name: str
    prompt: str
    enabled: bool
    observer_type: str
    trigger_mode: TriggerMode
    source: LocationCondition | None
    destination: LocationCondition
```

Persistence stores a list of dictionaries under a new per-process app-state key, for example `ai_event_registrations_by_process`. Runtime fields such as previous state, baseline state, source matched, current status, and AI queue state are never persisted.

### 3.3. Runtime state

```python
@dataclass
class LocationState:
    map_name: str
    x: int
    y: int


@dataclass
class ObserverRuntime:
    baseline_ready: bool = False
    previous_state: LocationState | None = None
    source_matched: bool = False
    status: str = "Waiting for initial state"
```

The worker holds one runtime state per `event_id`. Deleting or editing an event removes/resets its runtime state. A failed MCP read does not overwrite `previous_state`; a transition from unavailable state to a valid state starts a new baseline and emits no event.

## 4. Observer Behavior

### 4.1. Location matching

`LocationCondition.matches(state)` returns `True` only when:

1. Map names match case-insensitively.
2. If `use_coordinates` is false, map match is sufficient.
3. If `use_coordinates` is true, all four bounds exist and inclusive checks pass:
   `min_x <= x <= max_x` and `min_y <= y <= max_y`.

If the MCP response does not contain all required fields, the sample is invalid and does not match any condition.

### 4.2. Baseline and game lifecycle

- The first valid sample after worker start is baseline only.
- A failed/invalid sample does not mutate the last valid transition state.
- When the game window becomes unavailable and later returns with a valid state, all event runtimes reset and the first returned state becomes the new baseline.
- The worker uses the existing game-state update interval; no new interval setting is exposed.

### 4.3. Trigger state machine

- `enter`: fire only on `outside -> inside`; after firing, remain armed only after an `outside` sample.
- `exit`: fire only on `inside -> outside`; after firing, remain armed only after an `inside` sample.
- `source_to_destination`:
  - Do not track until a valid sample matches source.
  - Set `source_matched=True` when source is observed.
  - If the current map leaves the configured map or the current sample no longer matches source before destination, reset to waiting for source.
  - Fire only after a later valid sample matches destination.
  - Reset to waiting for source after firing.
- An event disabled/re-enabled or its observer edited resets its runtime state.

### 4.4. Game focus behavior

The worker compares the selected target HWND with `GetForegroundWindow()` on every valid sample. Focus does not stop matching or transition updates. If a trigger fires while the game is focused, the worker emits a suppressed trigger; the UI updates status but does not enqueue or send the prompt. The transition remains consumed, so re-arm rules still apply.

## 5. AI Queue Integration

`ChatMessageQueue` remains the only dispatch path. Extend its queued message metadata with an event identity/source without creating a second queue.

Recommended API:

```python
def enqueue_event(self, text: str, event_id: str) -> bool:
    """Queue one event prompt unless the same event is pending or active."""

def mark_active(self, message: QueuedChatMessage) -> None:
    """Track the message currently being processed for duplicate checks."""

def clear_active(self, message: QueuedChatMessage) -> None:
    """Release the active identity after the AI turn finishes."""
```

The existing `_start_next_queued_turn` and `_on_turn_finished` lifecycle should call the active tracking methods. Manual messages retain current behavior. Event messages use `source="event"`, `rule_id=event_id`, and are shown as event-origin messages in the existing queue bubble.

When the worker emits a fired event:

1. If `suppressed_by_focus=True`, update status and stop.
2. Otherwise call `enqueue_event(prompt, event_id)` on the UI thread.
3. Refresh the existing queue bubble and call `_start_next_queued_turn()`.
4. If the event is later deleted, any already queued message remains valid and is not removed.

## 6. UI Design

### 6.1. Main chat composer

Add `event_messages_btn` immediately before the existing `auto_messages_btn` in the composer action layout. The button opens `EventManagementDialog`. It is independent from the automatic schedule state.

Add an `event_status_bubble` to the existing bottom overlay bubble layout. It is positioned immediately to the left of `auto_status_bubble`, uses the current enabled-event count/status summary, and opens `EventManagementDialog` when clicked. The event bubble and automatic bubble must not overlap; `_position_queue_bubble` should calculate the event bubble width before placing the automatic bubble.

### 6.2. EventManagementDialog

- `QTableWidget` with columns: `Enabled`, `Name`, `Prompt`, `Observer`, `Status`.
- Single-row selection because deletion is one event at a time.
- Inline prompt editing with `itemChanged`; block signals while refreshing rows.
- Persist prompt on commit and show a transient success/error message.
- Double-click a row to open `EventSettingsDialog` in edit mode.
- `Create event` opens create mode.
- `Delete event` requires confirmation, removes config/runtime immediately, and refreshes the table.
- Status cells are read-only and updated by queued worker signals.
- Runtime status is session-only.

### 6.3. EventSettingsDialog

- Fields: event name, prompt, enabled checkbox, observer tabs.
- Initial tab: `Location Observer`.
- Trigger combo: enter, exit, source-to-destination.
- Source/destination each contain a map combo from `MAP_CATALOG`, a coordinate checkbox, and four integer fields.
- Source group is visible only for source-to-destination.
- Coordinate fields are disabled/hidden when that condition's checkbox is off.
- Save validates unique name case-insensitively, non-empty prompt, required source/destination, valid map selection, and inclusive coordinate bounds.
- Cancel/close with unsaved inline changes asks whether to save or discard.

## 7. Persistence

Add per-process callbacks parallel to the existing auto-message callbacks:

```python
def _load_ai_events_for_target(self, target: object) -> list[dict]:
    """Load persisted registered events for one game target."""

def _save_ai_events_for_target(self, target: object, events: list[dict]) -> None:
    """Persist registered events for one game target."""
```

`GeminiChatWidget` receives these callbacks from `MainWindow`. The managed process tab reloads event definitions when its target changes, stops the old worker, clears runtime state, and starts the new worker after the first valid target state is available.

Serialization must preserve `event_id`, name, prompt, enabled, observer type, trigger mode, map IDs/names, coordinate flags, and all bounds. Invalid persisted entries are skipped with a user-visible warning; valid entries must not be lost because one entry is malformed.

## 8. Thread Safety and Lifecycle

- `LocationObserverWorker` runs outside the UI thread and blocks only on the MCP read for the current cycle.
- Start the worker when a valid selected game target is assigned; stop it on target release, widget close, or event configuration reload.
- Use a stop event and join/quit with a bounded timeout during shutdown.
- Worker signals use `Qt.ConnectionType.QueuedConnection`.
- UI widgets, table cells, queue operations, persistence callbacks, and status updates run only on the UI thread.
- No QWidget method may be called from the worker.

## 9. Technical Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| MCP OCR read is slow | Observer cycle stalls | Keep polling in worker; preserve last valid state on failure. |
| OCR returns a wrong map/coordinate | False event | Require MCP `success=true` and all required fields; reject incomplete samples. |
| Event prompt duplicates active AI turn | Duplicate AI work | Track active event IDs in `ChatMessageQueue`, not only pending items. |
| Worker updates Qt directly | Crash/race | Emit queued signals and update UI only in `GeminiChatWidget`. |
| Per-process state mix-up | Event sent to wrong game | Key persistence and worker by selected target HWND/process key. |
| Editing while worker fires | Stale runtime transition | Stop/reset worker state before applying edited configuration. |
| Game restart appears as movement | False transition | Treat unavailable-to-valid lifecycle as reset plus new baseline. |

## 10. Code Skeleton

```python
class LocationEventObserver:
    """Evaluate one registered event against sequential game states."""

    def evaluate(self, state: LocationState | None, *, game_focused: bool) -> ObserverResult:
        """Return status and optional trigger for the current sample."""
        ...


class LocationObserverWorker(QObject):
    """Poll MCP game state and emit observer results without touching UI widgets."""

    state_updated = pyqtSignal(str, str)
    event_triggered = pyqtSignal(object)
    finished = pyqtSignal()

    def run(self) -> None:
        """Poll using the existing game-state interval until stopped."""
        ...


class EventManagementDialog(QDialog):
    """Manage persisted event registrations and session runtime statuses."""

    def _on_prompt_changed(self, item: QTableWidgetItem) -> None:
        """Persist an inline prompt edit and show the save result."""
        ...


class EventSettingsDialog(QDialog):
    """Create or edit a registered event and its observer configuration."""

    def get_event(self) -> RegisteredEvent:
        """Validate and return the current event configuration."""
        ...
```

## 11. Verification Plan

- Unit test all map/bounds matching cases, case-insensitive map names, inclusive bounds, incomplete state, baseline, re-arm, source reset, and game restart reset.
- Test queue duplicate behavior for pending and active event IDs, event focus suppression, and deletion preserving already queued messages.
- Test persistence round-trip per process, malformed entry isolation, stable event IDs, and map id/name storage.
- Test dialog validation, inline prompt save success/error, double-click edit, enable reset, delete confirmation, and status column updates.
- Test worker-to-UI signal delivery without direct worker QWidget access.
- Manual test: start app before game, start game after app, restart game, focus/unfocus game, enter/exit destination, source-to-destination, AI busy queue, and delete while queued.
