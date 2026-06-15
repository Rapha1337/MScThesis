from __future__ import annotations

import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_resource_tracker_writes_records_and_total(tmp_path: Path) -> None:
    from resource_usage import ResourceUsageEngine

    log_path = tmp_path / "resource_usage.jsonl"
    tracker = ResourceUsageEngine(
        resource_log_path=log_path,
        enable_tracking=True,
        enable_codecarbon=False,
        stage="full_pa_simulation",
        run_label="test_run",
        run_id="run-1",
    )

    tracker.start_run()
    tracker.log_paper(
        paper_id="llm1_persona_A_day_0",
        stage="llm1_behavior_probability",
        prompt_tokens=10,
        response_tokens=5,
        prompt_tokens_source="api",
        response_tokens_source="api",
        token_source="api",
        paper_seconds=0.25,
    )
    tracker.stop_run(total_runtime_seconds=1.0, paper_count=1)

    records = _read_jsonl(log_path)
    assert len(records) == 2
    assert records[0]["paper_id"] == "llm1_persona_A_day_0"
    assert records[0]["tokens_total"] == 15
    assert records[0]["token_source"] == "api"
    assert records[1]["paper_id"] == "TOTAL"
    assert records[1]["run_status"] == "success"
    assert records[1]["error_type"] is None
    assert records[1]["error_message"] is None
    assert records[1]["prompt_tokens"] == 10
    assert records[1]["response_tokens"] == 5
    assert records[1]["tokens_total"] == 15
    assert records[1]["paper_count"] == 1


def test_resource_tracker_works_when_codecarbon_disabled(tmp_path: Path) -> None:
    from resource_usage import ResourceUsageEngine

    log_path = tmp_path / "resource_usage.jsonl"
    tracker = ResourceUsageEngine(log_path, enable_tracking=True, enable_codecarbon=False)

    tracker.start_run()
    tracker.stop_run(total_runtime_seconds=0.0, paper_count=0)

    total = _read_jsonl(log_path)[-1]
    assert total["paper_id"] == "TOTAL"
    assert total["run_status"] == "success"
    assert total["codecarbon_emissions_kg"] is None
    assert total["codecarbon_energy_kwh"] is None


def test_token_usage_extraction_accepts_api_metadata_objects() -> None:
    from resource_usage import extract_token_usage

    response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=12, completion_tokens=7, total_tokens=19)
    )

    assert extract_token_usage(response) == {
        "prompt_tokens": 12,
        "response_tokens": 7,
        "tokens_total": 19,
        "token_source": "api",
    }


def test_token_usage_extraction_accepts_api_metadata_dicts() -> None:
    from resource_usage import extract_token_usage

    assert extract_token_usage({"usage": {"input_tokens": 4, "output_tokens": 6}}) == {
        "prompt_tokens": 4,
        "response_tokens": 6,
        "tokens_total": 10,
        "token_source": "api",
    }


def test_token_usage_extraction_does_not_crash_when_missing() -> None:
    from resource_usage import extract_token_usage

    assert extract_token_usage(SimpleNamespace()) == {
        "prompt_tokens": 0,
        "response_tokens": 0,
        "tokens_total": 0,
        "token_source": "unavailable",
    }


def test_full_simulation_dry_run_writes_resource_usage_jsonl(tmp_path: Path) -> None:
    from run_full_pa_simulation import config_from_args, parse_args, run_full_simulation

    config = config_from_args(
        parse_args(
            [
                "--dry-run",
                "--n-personas",
                "1",
                "--n-days",
                "1",
                "--output-dir",
                str(tmp_path),
            ]
        )
    )

    run_full_simulation(config)

    resource_log = tmp_path / "resource_usage.jsonl"
    assert resource_log.exists()
    records = _read_jsonl(resource_log)
    assert [record["stage"] for record in records[:-1]] == [
        "llm1_behavior_probability",
        "llm2_pa_decision",
    ]
    assert all(record["token_source"] == "dry_run" for record in records[:-1])
    assert records[-1]["paper_id"] == "TOTAL"
    assert records[-1]["paper_count"] == 2
    assert records[-1]["run_status"] == "success"
    assert records[-1]["output_files"]["simulation_run_manifest"] == "simulation_run_manifest.json"

    manifest_path = tmp_path / "simulation_run_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"]
    assert manifest["created_at_utc"]
    assert manifest["run_status"] == "success"
    assert set(manifest) >= {"simulation", "models", "decision_schema", "output_files"}
    assert manifest["decision_schema"]["active_categories"] == [
        "skip_activity",
        "do_planned_activity",
        "adapt_activity",
        "extra_activity",
        "app_ignored",
    ]
    assert "postpone_activity" in manifest["decision_schema"]["deprecated_categories"]
    assert "postponed" in manifest["decision_schema"]["deprecated_categories"]
    assert manifest["output_files"]["resource_usage"] == "resource_usage.jsonl"


def test_failed_resource_stop_writes_total_and_preserves_original_exception(tmp_path: Path) -> None:
    from resource_usage import ResourceUsageEngine

    log_path = tmp_path / "resource_usage.jsonl"
    tracker = ResourceUsageEngine(log_path, enable_tracking=True, enable_codecarbon=False)
    original_error = RuntimeError("boom")

    try:
        raise original_error
    except RuntimeError as exc:
        tracker.stop_run(
            total_runtime_seconds=0.1,
            paper_count=0,
            run_status="failed",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        preserved = exc

    assert preserved is original_error
    total = _read_jsonl(log_path)[-1]
    assert total["paper_id"] == "TOTAL"
    assert total["run_status"] == "failed"
    assert total["error_type"] == "RuntimeError"
    assert total["error_message"] == "boom"


def test_full_simulation_failure_writes_failed_manifest_and_resource_total(
    tmp_path: Path, monkeypatch
) -> None:
    import run_full_pa_simulation as module

    config = module.config_from_args(
        module.parse_args(
            [
                "--dry-run",
                "--n-personas",
                "1",
                "--n-days",
                "1",
                "--output-dir",
                str(tmp_path),
            ]
        )
    )

    def fail_build_personas(config):
        raise RuntimeError("forced failure")

    monkeypatch.setattr(module, "_build_persona_states", fail_build_personas)

    try:
        module.run_full_simulation(config)
    except RuntimeError as exc:
        assert str(exc) == "forced failure"
    else:  # pragma: no cover - defensive
        raise AssertionError("run_full_simulation should have raised")

    manifest = json.loads((tmp_path / "simulation_run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_status"] == "failed"
    assert manifest["error_type"] == "RuntimeError"
    assert manifest["error_message"] == "forced failure"

    total = _read_jsonl(tmp_path / "resource_usage.jsonl")[-1]
    assert total["paper_id"] == "TOTAL"
    assert total["run_status"] == "failed"
    assert total["error_type"] == "RuntimeError"
    assert total["error_message"] == "forced failure"
