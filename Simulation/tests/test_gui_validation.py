from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import GUI_pa_simulation as gui


def test_valid_integer_fields_are_accepted() -> None:
    assert gui.parse_required_int("3", "Anzahl Personas", 1) == 3


def test_required_integer_fields_reject_empty_values() -> None:
    with pytest.raises(gui.GUIValidationError, match=r"\(leer\)"):
        gui.parse_required_int("", "Anzahl Personas", 1)


def test_negative_seeds_are_rejected() -> None:
    with pytest.raises(gui.GUIValidationError, match="≥ 0"):
        gui.parse_required_int("-1", "Basis-Seed", 0)


@pytest.mark.parametrize("value", ["0", "0.5", "2"])
def test_temperature_accepts_valid_range(value: str) -> None:
    assert gui.parse_required_float(value, "Temperature", 0, 2, True) == float(value)


@pytest.mark.parametrize("value", ["-0.1", "2.1"])
def test_temperature_rejects_outside_range(value: str) -> None:
    with pytest.raises(gui.GUIValidationError):
        gui.parse_required_float(value, "Temperature", 0, 2, True)


@pytest.mark.parametrize("value", ["1", "0.5"])
def test_top_p_accepts_valid_range(value: str) -> None:
    assert gui.parse_required_float(value, "Top P", 0, 1, False) == float(value)


@pytest.mark.parametrize("value", ["0", "-0.1", "1.1"])
def test_top_p_rejects_invalid_range(value: str) -> None:
    with pytest.raises(gui.GUIValidationError):
        gui.parse_required_float(value, "Top P", 0, 1, False)


def test_iso_date_is_accepted() -> None:
    assert gui.parse_required_date("2026-03-02", "Startdatum").isoformat() == "2026-03-02"


def test_non_iso_date_is_rejected() -> None:
    with pytest.raises(gui.GUIValidationError, match="YYYY-MM-DD"):
        gui.parse_required_date("02.03.2026", "Startdatum")


def test_single_numeric_override_is_accepted() -> None:
    assert gui.validate_optional_numeric_list("7.5", "PA-Stunden pro Woche", 3) == [7.5]


def test_persona_list_is_accepted_for_three_personas() -> None:
    assert gui.validate_optional_numeric_list("7.5,5,3", "PA-Stunden pro Woche", 3) == [7.5, 5.0, 3.0]


@pytest.mark.parametrize("value", ["7.5,,3", "7.5,", ",7.5"])
def test_numeric_lists_reject_empty_elements(value: str) -> None:
    with pytest.raises(gui.GUIValidationError, match="leere"):
        gui.validate_optional_numeric_list(value, "PA-Stunden pro Woche", 3)


def test_numeric_lists_reject_negative_values() -> None:
    with pytest.raises(gui.GUIValidationError, match="nicht-negative"):
        gui.validate_optional_numeric_list("-2", "PA-Stunden pro Woche", 3)


def test_numeric_lists_reject_too_many_persona_values() -> None:
    with pytest.raises(gui.GUIValidationError, match="höchstens 2"):
        gui.validate_optional_numeric_list("1.2,2.5,0.8", "Arbeitsplatz-Entfernung in km", 2)


def test_decimal_comma_ambiguity_produces_informative_message() -> None:
    with pytest.raises(gui.GUIValidationError) as excinfo:
        gui.validate_optional_numeric_list("7,5", "PA-Stunden pro Woche", 3)
    assert "Bitte Dezimalpunkte verwenden" in str(excinfo.value)
    assert "Kommas trennen" in str(excinfo.value)


@pytest.mark.parametrize("value", ["0", "-1"])
def test_token_limits_reject_zero_and_negative_values(value: str) -> None:
    with pytest.raises(gui.GUIValidationError, match="≥ 1"):
        gui.parse_required_int(value, "LLM1 Max Tokens", 1)


def test_output_paths_pointing_to_files_are_rejected(tmp_path: Path) -> None:
    file_path = tmp_path / "output.txt"
    file_path.write_text("not a directory")
    with pytest.raises(gui.GUIValidationError, match="nicht zu einer Datei"):
        gui.validate_output_dir(str(file_path), "Output-Pfad")


def test_invalid_input_prevents_subprocess_creation() -> None:
    class DummyGUI:
        is_running = False

        def validate_inputs(self):  # noqa: ANN201
            return None

    with patch.object(gui.subprocess, "Popen") as popen:
        gui.PASimulationGUI.start_simulation(DummyGUI())  # type: ignore[arg-type]

    popen.assert_not_called()
    assert DummyGUI.is_running is False
