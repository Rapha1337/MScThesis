from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

SIMULATION_DIR = Path(__file__).resolve().parents[1]
if str(SIMULATION_DIR) not in sys.path:
    sys.path.append(str(SIMULATION_DIR))

from agent_context import WEEKDAY_NAMES, PHASE_LLM_LABELS


def test_known_dates_match_internal_weekday_convention() -> None:
    assert date(2026, 9, 10).weekday() == 3
    assert WEEKDAY_NAMES[date(2026, 9, 10).weekday()] == "Thursday"
    assert date(2026, 9, 13).weekday() == 6
    assert WEEKDAY_NAMES[date(2026, 9, 13).weekday()] == "Sunday"


def test_holiday_phase_is_llm_facing_vacation_period() -> None:
    assert PHASE_LLM_LABELS["holiday"] == "vacation_period"
