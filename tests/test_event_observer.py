from src.logic.event_observer import (
    HealthEventObserver,
    HealthState,
    LocationCondition,
    LocationEventObserver,
    LocationState,
    RegisteredEvent,
    is_health_below_transition,
)
from src.ai_control.current_character_info import _normalize_health


def condition(map_id: int = 1, map_name: str = "Lorencia", **kwargs) -> LocationCondition:
    return LocationCondition(map_id=map_id, map_name=map_name, **kwargs)


def state(map_name: str = "Lorencia", x: int = 10, y: int = 20) -> LocationState:
    return LocationState(map_name=map_name, x=x, y=y)


def event(trigger_mode: str = "enter") -> RegisteredEvent:
    destination = condition(
        use_coordinates=True,
        min_x=10,
        max_x=20,
        min_y=20,
        max_y=30,
    )
    source = condition(use_coordinates=True, min_x=1, max_x=5, min_y=1, max_y=5)
    return RegisteredEvent(
        event_id="event-1",
        name="Enter dungeon",
        prompt="Check the character",
        enabled=True,
        observer_type="location",
        trigger_mode=trigger_mode,
        source=source if trigger_mode == "source_to_destination" else None,
        destination=destination,
    )


def test_location_condition_uses_inclusive_coordinate_bounds() -> None:
    configured = condition(use_coordinates=True, min_x=10, max_x=20, min_y=30, max_y=40)

    assert configured.matches(state(x=10, y=30)) is True
    assert configured.matches(state(x=20, y=40)) is True
    assert configured.matches(state(x=9, y=40)) is False


def test_location_condition_matches_map_case_insensitively() -> None:
    configured = condition(map_name="Lorencia")

    assert configured.matches(state(map_name="lorencia")) is True


def test_first_valid_state_is_baseline_and_does_not_trigger() -> None:
    observer = LocationEventObserver(event("enter"))

    result = observer.evaluate(state(x=10, y=20), game_focused=False)

    assert result.triggered is False
    assert result.status == "Waiting for initial state"


def test_enter_triggers_only_on_outside_to_inside_transition() -> None:
    observer = LocationEventObserver(event("enter"))
    observer.evaluate(state(x=1, y=1), game_focused=False)

    entered = observer.evaluate(state(x=10, y=20), game_focused=False)
    repeated = observer.evaluate(state(x=11, y=21), game_focused=False)
    observer.evaluate(state(x=1, y=1), game_focused=False)
    entered_again = observer.evaluate(state(x=10, y=20), game_focused=False)

    assert entered.triggered is True
    assert repeated.triggered is False
    assert entered_again.triggered is True


def test_exit_triggers_only_on_inside_to_outside_transition() -> None:
    observer = LocationEventObserver(event("exit"))
    observer.evaluate(state(x=10, y=20), game_focused=False)

    exited = observer.evaluate(state(x=1, y=1), game_focused=False)
    repeated = observer.evaluate(state(x=2, y=2), game_focused=False)

    assert exited.triggered is True
    assert repeated.triggered is False


def test_source_to_destination_requires_source_before_destination() -> None:
    observer = LocationEventObserver(event("source_to_destination"))
    observer.evaluate(state(x=10, y=20), game_focused=False)
    destination_without_source = observer.evaluate(state(x=10, y=20), game_focused=False)

    observer.reset()
    observer.evaluate(state(x=10, y=20), game_focused=False)
    observer.evaluate(state(x=1, y=1), game_focused=False)
    destination_after_source = observer.evaluate(state(x=10, y=20), game_focused=False)

    assert destination_without_source.triggered is False
    assert destination_after_source.triggered is True


def test_game_focus_suppresses_trigger_but_keeps_transition_state() -> None:
    observer = LocationEventObserver(event("enter"))
    observer.evaluate(state(x=1, y=1), game_focused=False)

    suppressed = observer.evaluate(state(x=10, y=20), game_focused=True)
    observer.evaluate(state(x=1, y=1), game_focused=False)
    next_trigger = observer.evaluate(state(x=10, y=20), game_focused=False)

    assert suppressed.triggered is True
    assert suppressed.suppressed_by_focus is True
    assert next_trigger.triggered is True


def test_invalid_state_does_not_mutate_previous_transition() -> None:
    observer = LocationEventObserver(event("enter"))
    observer.evaluate(state(x=1, y=1), game_focused=False)

    invalid = observer.evaluate(None, game_focused=False)
    entered = observer.evaluate(state(x=10, y=20), game_focused=False)

    assert invalid.triggered is False
    assert entered.triggered is True


def health_event(threshold: int = 100) -> RegisteredEvent:
    return RegisteredEvent(
        event_id="health-event",
        name="HP dưới 100",
        prompt="",
        enabled=True,
        observer_type="health",
        trigger_mode="health_below",  # type: ignore[arg-type]
        source=None,
        destination=None,
        health_threshold=threshold,
    )


def test_health_observer_skips_initial_state_and_triggers_on_crossing() -> None:
    observer = HealthEventObserver(health_event())

    assert observer.evaluate_window_pair(previous_state=None, current_state=HealthState(150), game_focused=False).triggered is False
    assert observer.evaluate_window_pair(previous_state=HealthState(150), current_state=HealthState(99), current_captured_at=1, game_focused=False).triggered is True
    assert observer.evaluate_window_pair(previous_state=HealthState(99), current_state=HealthState(80), current_captured_at=2, game_focused=False).triggered is False


def test_health_observer_uses_window_state_previous_sample_on_first_evaluation() -> None:
    observer = HealthEventObserver(health_event())
    result = observer.evaluate_window_pair(
        previous_state=HealthState(6321),
        current_state=HealthState(0),
        current_captured_at=1,
        game_focused=False,
    )

    assert result.triggered is True


def test_health_observer_uses_window_pair_even_after_current_zero_was_seen() -> None:
    observer = HealthEventObserver(health_event())
    observer.evaluate_window_pair(previous_state=None, current_state=HealthState(0), game_focused=False)

    result = observer.evaluate_window_pair(
        previous_state=HealthState(6321),
        current_state=HealthState(0),
        current_captured_at=1,
        game_focused=False,
    )

    assert result.triggered is True


def test_health_transition_rule_matches_logger_pair() -> None:
    assert is_health_below_transition(HealthState(8190), HealthState(0)) is True
    assert is_health_below_transition(HealthState(0), HealthState(0)) is False


def test_health_observer_rearms_after_health_recovers() -> None:
    observer = HealthEventObserver(health_event())
    observer.evaluate_window_pair(previous_state=None, current_state=HealthState(150), game_focused=False)
    observer.evaluate_window_pair(previous_state=HealthState(150), current_state=HealthState(99), current_captured_at=1, game_focused=False)

    observer.evaluate_window_pair(previous_state=HealthState(99), current_state=HealthState(100), current_captured_at=2, game_focused=False)
    assert observer.evaluate_window_pair(previous_state=HealthState(100), current_state=HealthState(99), current_captured_at=3, game_focused=False).triggered is True


def test_health_observer_emits_once_until_health_recovers() -> None:
    observer = HealthEventObserver(health_event())

    first = observer.evaluate_window_pair(
        previous_state=HealthState(8190),
        current_state=HealthState(0),
        current_captured_at=1,
        game_focused=False,
    )
    repeated_pair = observer.evaluate_window_pair(
        previous_state=HealthState(8190),
        current_state=HealthState(0),
        current_captured_at=2,
        game_focused=False,
    )

    assert first.triggered is True
    assert repeated_pair.triggered is False


def test_health_observer_compares_one_retained_state_with_new_state() -> None:
    observer = HealthEventObserver(health_event())

    assert observer.evaluate_current_state(HealthState(8190), game_focused=False).triggered is False
    assert observer.evaluate_current_state(HealthState(8190), game_focused=False).triggered is False
    assert observer.evaluate_current_state(HealthState(0), game_focused=False).triggered is True
    assert observer.evaluate_current_state(HealthState(0), game_focused=False).triggered is False


def test_health_observer_focus_suppresses_delivery_but_consumes_crossing() -> None:
    observer = HealthEventObserver(health_event())
    observer.evaluate_window_pair(previous_state=None, current_state=HealthState(150), game_focused=False)

    suppressed = observer.evaluate_window_pair(previous_state=HealthState(150), current_state=HealthState(99), current_captured_at=1, game_focused=True)
    repeated = observer.evaluate_window_pair(previous_state=HealthState(99), current_state=HealthState(80), current_captured_at=2, game_focused=False)

    assert suppressed.triggered is True
    assert suppressed.suppressed_by_focus is True
    assert repeated.triggered is False


def test_health_normalizer_accepts_death_state_with_only_zero() -> None:
    assert _normalize_health("0") == {"current": 0}


def test_health_normalizer_ignores_maximum_health_line() -> None:
    assert _normalize_health("6,321 6,321") == {"current": 6321}
