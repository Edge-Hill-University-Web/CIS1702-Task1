import importlib
import json
import os
import sys
import traceback
from pathlib import Path

import pytest

# -------------------------------------------------------------------------
# JSON Storage Helpers
# -------------------------------------------------------------------------
# Anchored to this file's folder so the count is the same wherever pytest is run from
ATTEMPTS_FILE = Path(__file__).resolve().parent / ".test_attempts.json"
THRESHOLD = 3

telemetry = None  # set by the load_telemetry fixture before each test


def read_attempts() -> dict:
    """Reads the attempt history from disk, creating the file if it does not exist."""
    if not ATTEMPTS_FILE.exists():
        write_attempts({})
        return {}
    try:
        data = json.loads(ATTEMPTS_FILE.read_text())
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        write_attempts({})
        return {}


def write_attempts(data: dict) -> None:
    """Writes the attempt history to disk (via a temp file so it is never left half-written)."""
    try:
        tmp = ATTEMPTS_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(ATTEMPTS_FILE)
    except OSError:
        pass


def _entry(data: dict, test_name: str) -> dict:
    """Returns the record for a test, upgrading the old plain-integer format if found."""
    entry = data.get(test_name)
    if isinstance(entry, int):
        entry = {"runs": entry, "fails": entry}
    if not isinstance(entry, dict):
        entry = {}
    entry.setdefault("runs", 0)
    entry.setdefault("fails", 0)
    entry.setdefault("clue_revealed", False)
    entry.setdefault("clues_seen", [])
    entry.setdefault("passed_after_clue", False)
    data[test_name] = entry
    return entry


def record_run(test_name: str) -> None:
    """Called at the start of every test so the JSON file is updated on every run."""
    data = read_attempts()
    _entry(data, test_name)["runs"] += 1
    write_attempts(data)


def record_failure(test_name: str) -> int:
    """Increments the failure count in the JSON file and returns the new total."""
    data = read_attempts()
    entry = _entry(data, test_name)
    entry["fails"] += 1
    write_attempts(data)
    return entry["fails"]


def clue(test_name: str, clue_id: str, hint_text: str) -> str:
    """
    Only evaluated when an assertion fails, so it records this failure in the
    JSON file, then uses the stored total to decide whether to reveal the hint.
    clue_id is a short fixed label stored in the JSON instead of the hint text,
    so the same clue is only recorded once even if the student's values change.
    """
    data = read_attempts()
    entry = _entry(data, test_name)
    entry["fails"] += 1
    fail_count = entry["fails"]

    unlocked = fail_count > THRESHOLD
    if unlocked:
        # Record that a clue was shown, and which one (a test can have several)
        entry["clue_revealed"] = True
        if clue_id not in entry["clues_seen"]:
            entry["clues_seen"].append(clue_id)
    write_attempts(data)

    if unlocked:
        return f"\n[CLUE UNLOCKED (Failed {fail_count} times)] {hint_text}"

    remaining = (THRESHOLD + 1) - fail_count
    return (
        f"\n[CLUE LOCKED] Failed {fail_count} time(s). "
        f"{remaining} more failure(s) until a clue is revealed."
    )


# -------------------------------------------------------------------------
# Fixture: Record the run and load the student's module
# -------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def load_telemetry(request):
    """
    Records the run, imports a fresh copy of app.telemetry, then after the
    test finishes checks whether it passed following a revealed clue.
    """
    global telemetry
    test_name = request.node.name
    record_run(test_name)
    fails_before = _entry(read_attempts(), test_name)["fails"]

    sys.modules.pop("app.telemetry", None)
    try:
        telemetry = importlib.import_module("app.telemetry")
    except SyntaxError as exc:
        record_failure(test_name)
        pytest.fail(f"Syntax error in app/telemetry.py at line {exc.lineno}: {exc.msg}")
    except ImportError as exc:
        record_failure(test_name)
        pytest.fail(f"Could not import app.telemetry: {exc}")
    except Exception as exc:
        # e.g. TypeError from "12000" - 1800.0 when a number is still a string
        record_failure(test_name)
        frame = traceback.extract_tb(exc.__traceback__)[-1]
        pytest.fail(
            f"app/telemetry.py crashed at line {frame.lineno}: "
            f"{type(exc).__name__}: {exc}"
        )

    yield  # the test runs here

    # Every failure goes through clue(), so an unchanged count means the test passed
    data = read_attempts()
    entry = _entry(data, test_name)
    if entry["fails"] == fails_before and entry["clue_revealed"]:
        entry["passed_after_clue"] = True
        write_attempts(data)


# -------------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------------
def test_pilot_identity():
    t_name = "test_pilot_identity"

    assert hasattr(telemetry, "pilot_callsign"), clue(
        t_name,
        "callsign_missing",
        "Variable 'pilot_callsign' not found. Check your variable declarations for naming typos.",
    )
    assert telemetry.pilot_callsign == "Starling", clue(
        t_name,
        "callsign_value",
        "'pilot_callsign' must be set to 'Starling'.",
    )
    assert hasattr(telemetry, "flight_code"), clue(
        t_name,
        "flight_code_missing",
        "'flight_code' variable is missing.",
    )
    assert telemetry.flight_code == "Starling-Aegis-4", clue(
        t_name,
        "flight_code_value",
        f"Expected flight_code to be 'Starling-Aegis-4', but got '{getattr(telemetry, 'flight_code', None)}'.",
    )


def test_fuel_calculations():
    t_name = "test_fuel_calculations"

    current_fuel_type = type(getattr(telemetry, "fuel_capacity_litres", None)).__name__
    assert isinstance(getattr(telemetry, "fuel_capacity_litres", None), (int, float)), clue(
        t_name,
        "fuel_type",
        f"'fuel_capacity_litres' is currently a {current_fuel_type}. Remove quotation marks to make it a numeric float/int.",
    )
    assert getattr(telemetry, "reserve_fuel", None) == 1800.0, clue(
        t_name,
        "reserve_value",
        f"Expected reserve_fuel to be 1800.0, but got {getattr(telemetry, 'reserve_fuel', None)}.",
    )
    assert getattr(telemetry, "usable_fuel", None) == 10200.0, clue(
        t_name,
        "usable_operator",
        f"Expected usable_fuel to be 10200.0, but got {getattr(telemetry, 'usable_fuel', None)}. Check your arithmetic operator (+ vs -).",
    )


def test_payload_calculations():
    t_name = "test_payload_calculations"

    crate_type = type(getattr(telemetry, "crate_count", None)).__name__
    assert isinstance(getattr(telemetry, "crate_count", None), int), clue(
        t_name,
        "crate_type",
        f"'crate_count' must be an integer, not {crate_type}.",
    )
    assert getattr(telemetry, "total_payload_kg", None) == 3512.5, clue(
        t_name,
        "payload_value",
        f"Expected total_payload_kg to be 3512.5, but got {getattr(telemetry, 'total_payload_kg', None)}.",
    )


def test_manifest_log():
    t_name = "test_manifest_log"

    assert hasattr(telemetry, "manifest_log"), clue(
        t_name,
        "manifest_missing",
        "'manifest_log' variable is missing.",
    )
    manifest_val = getattr(telemetry, "manifest_log", "")
    assert manifest_val == "Aegis-4 payload: 3512.5 kg", clue(
        t_name,
        "manifest_format",
        f"String formatting mismatch.\nExpected: 'Aegis-4 payload: 3512.5 kg'\nReceived: '{manifest_val}'",
    )