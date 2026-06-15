from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

try:  # optional dependency; tracking must work without it
    from codecarbon import EmissionsTracker, OfflineEmissionsTracker  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    EmissionsTracker = None
    OfflineEmissionsTracker = None

CARBON_CONFIG: dict[str, Any] = {
    "output_dir": "codecarbon",
    "project_name": "pa-simulation",
    "measure_power_secs": 15,
    "tracking_mode": "machine",
    "on_csv_write": "update",
    "is_offline": False,
    "country_iso_code": None,
}
HUMAN_TIME_CONFIG: dict[str, Any] = {}
UBELIX_ESTIMATION_CONFIG: dict[str, Any] = {"enabled": False}


@dataclass
class ResourceUsageConfig:
    """Configuration for Kai-style JSONL resource usage tracking."""

    resource_log_path: Path
    enable_tracking: bool = True
    enable_codecarbon: bool = False
    stage: str = "full_pa_simulation"
    run_label: str = "run"
    run_id: str = ""
    enable_time_savings: bool = False


class CarbonTrackerManager:
    """Small CodeCarbon manager compatible with Kai's tracker pattern."""

    def __init__(self, enabled: bool = True, carbon_config: Mapping[str, Any] | None = None) -> None:
        self._enabled = enabled
        self._config = dict(carbon_config or CARBON_CONFIG)
        self._tracker = None
        self._started = False
        self._init_tracker()

    def _init_tracker(self) -> None:
        if not self._enabled:
            raise RuntimeError("CodeCarbon tracking disabled.")
        if EmissionsTracker is None:
            raise RuntimeError("CodeCarbon tracking requested but package is not installed.")
        output_dir = Path(self._config.get("output_dir", "codecarbon"))
        output_dir.mkdir(parents=True, exist_ok=True)
        kwargs = {
            "project_name": self._config.get("project_name", "pa-simulation"),
            "output_dir": str(output_dir),
            "measure_power_secs": self._config.get("measure_power_secs", 15),
            "tracking_mode": self._config.get("tracking_mode", "machine"),
            "on_csv_write": self._config.get("on_csv_write", "update"),
            "save_to_file": True,
        }
        if self._config.get("is_offline"):
            if OfflineEmissionsTracker is None:
                raise RuntimeError("OfflineEmissionsTracker unavailable.")
            country_code = self._config.get("country_iso_code")
            if not country_code:
                raise ValueError("country_iso_code is required when CodeCarbon offline mode is enabled.")
            self._tracker = OfflineEmissionsTracker(country_iso_code=country_code, **kwargs)
        else:
            self._tracker = EmissionsTracker(**kwargs)

    def start(self) -> None:
        if self._started:
            return
        self._tracker.start()
        self._started = True

    def stop(self) -> float | None:
        if not self._started:
            return None
        try:
            return self._tracker.stop()
        except Exception as exc:  # pragma: no cover
            logging.warning("CodeCarbon tracker stop failed: %s", exc)
            return None
        finally:
            self._started = False

    def energy_kwh(self) -> float | None:
        data = getattr(self._tracker, "final_emissions_data", None)
        return getattr(data, "energy_consumed", None) if data is not None else None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return max(int(value), 0)
    except Exception:
        return None


def _lookup_usage_value(usage: Any, *names: str) -> int | None:
    for name in names:
        value = None
        if isinstance(usage, Mapping):
            value = usage.get(name)
        else:
            value = getattr(usage, name, None)
        parsed = _as_int(value)
        if parsed is not None:
            return parsed
    return None


def extract_token_usage(response: Any) -> dict[str, int | str]:
    """Extract OpenAI/GPUStack-style usage metadata without requiring one schema."""
    usage = response.get("usage") if isinstance(response, Mapping) else getattr(response, "usage", None)
    if usage is None:
        return {"prompt_tokens": 0, "response_tokens": 0, "tokens_total": 0, "token_source": "unavailable"}
    prompt_tokens = _lookup_usage_value(usage, "prompt_tokens", "input_tokens")
    response_tokens = _lookup_usage_value(usage, "completion_tokens", "output_tokens", "response_tokens")
    tokens_total = _lookup_usage_value(usage, "total_tokens", "tokens_total")
    if prompt_tokens is None:
        prompt_tokens = 0
    if response_tokens is None:
        response_tokens = 0
    if tokens_total is None:
        tokens_total = prompt_tokens + response_tokens
    source = "api" if any((prompt_tokens, response_tokens, tokens_total)) else "unavailable"
    return {
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "tokens_total": tokens_total,
        "token_source": source,
    }


class ResourceUsageTracker:
    """Track per-item and per-run resource usage using Kai's JSONL/TOTAL pattern."""

    def __init__(self, config: ResourceUsageConfig) -> None:
        self.config = config
        self.stage = config.stage
        self._records: list[dict[str, Any]] = []
        self._totals = {
            "tokens_total": 0,
            "prompt_tokens": 0,
            "response_tokens": 0,
            "embedding_tokens": 0,
            "pdf_text_tokens": 0,
            "pdf_visual_tokens": 0,
            "paper_seconds": 0.0,
        }
        self._carbon_tracker: CarbonTrackerManager | None = None

    def start_run(self) -> None:
        if not self.config.enable_tracking or not self.config.enable_codecarbon:
            return
        try:
            self._carbon_tracker = CarbonTrackerManager(enabled=True)
            self._carbon_tracker.start()
        except Exception as exc:  # pylint: disable=broad-except
            logging.warning("CodeCarbon disabled for this run: %s", exc)
            self._carbon_tracker = None

    def log_paper(
        self,
        paper_id: str,
        prompt_tokens: int,
        response_tokens: int,
        pdf_text_tokens: int = 0,
        pdf_visual_tokens: int = 0,
        embedding_tokens: int = 0,
        prompt_tokens_source: str = "estimate",
        response_tokens_source: str = "estimate",
        embedding_tokens_source: str = "estimate",
        paper_seconds: float | None = None,
        stage: str | None = None,
        token_source: str | None = None,
        tokens_total: int | None = None,
    ) -> None:
        if not self.config.enable_tracking:
            return
        prompt_tokens = max(int(prompt_tokens or 0), 0)
        response_tokens = max(int(response_tokens or 0), 0)
        embedding_tokens = max(int(embedding_tokens or 0), 0)
        pdf_text_tokens = max(int(pdf_text_tokens or 0), 0)
        pdf_visual_tokens = max(int(pdf_visual_tokens or 0), 0)
        computed_total_tokens = prompt_tokens + response_tokens + embedding_tokens + pdf_text_tokens + pdf_visual_tokens
        total_tokens = max(int(tokens_total), 0) if tokens_total is not None else computed_total_tokens
        source = token_source or prompt_tokens_source
        record = {
            "paper_id": paper_id,
            "stage": stage or self.stage,
            "run_label": self.config.run_label,
            "run_id": self.config.run_id,
            "tokens_total": total_tokens,
            "prompt_tokens": prompt_tokens,
            "response_tokens": response_tokens,
            "embedding_tokens": embedding_tokens,
            "prompt_tokens_source": prompt_tokens_source,
            "response_tokens_source": response_tokens_source,
            "embedding_tokens_source": embedding_tokens_source,
            "token_source": source,
            "pdf_text_tokens": pdf_text_tokens,
            "pdf_visual_tokens": pdf_visual_tokens,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "paper_seconds": paper_seconds,
        }
        self._records.append(record)
        self._totals["tokens_total"] += total_tokens
        self._totals["prompt_tokens"] += prompt_tokens
        self._totals["response_tokens"] += response_tokens
        self._totals["embedding_tokens"] += embedding_tokens
        self._totals["pdf_text_tokens"] += pdf_text_tokens
        self._totals["pdf_visual_tokens"] += pdf_visual_tokens
        if paper_seconds is not None:
            self._totals["paper_seconds"] += max(float(paper_seconds), 0.0)

    def stop_run(
        self,
        total_runtime_seconds: float,
        paper_count: int | None = None,
        *,
        run_status: str = "success",
        error_type: str | None = None,
        error_message: str | None = None,
        output_files: Mapping[str, str] | None = None,
    ) -> None:
        if not self.config.enable_tracking:
            return
        emissions_kg = None
        energy_kwh = None
        if self._carbon_tracker is not None:
            emissions_kg = self._carbon_tracker.stop()
            energy_kwh = self._carbon_tracker.energy_kwh()
        self._write_totals(
            total_runtime_seconds,
            paper_count,
            emissions_kg,
            energy_kwh,
            run_status=run_status,
            error_type=error_type,
            error_message=error_message,
            output_files=output_files,
        )

    def _write_totals(
        self,
        total_runtime_seconds: float,
        paper_count: int | None,
        emissions_kg: float | None,
        energy_kwh: float | None,
        *,
        run_status: str,
        error_type: str | None,
        error_message: str | None,
        output_files: Mapping[str, str] | None,
    ) -> None:
        self.config.resource_log_path.parent.mkdir(parents=True, exist_ok=True)
        count = int(paper_count if paper_count is not None else len(self._records))
        avg_runtime = (float(total_runtime_seconds) / count) if count else 0.0
        token_total = int(self._totals["tokens_total"])
        energy_per_1k = (energy_kwh / token_total) * 1000.0 if energy_kwh and token_total else None
        carbon_per_1k = ((emissions_kg * 1000.0) / token_total) * 1000.0 if emissions_kg and token_total else None
        total_record = {
            "paper_id": "TOTAL",
            "stage": self.stage,
            "run_status": run_status,
            "error_type": error_type,
            "error_message": error_message,
            "run_label": self.config.run_label,
            "run_id": self.config.run_id,
            "tokens_total": token_total,
            "prompt_tokens": self._totals["prompt_tokens"],
            "response_tokens": self._totals["response_tokens"],
            "embedding_tokens": self._totals["embedding_tokens"],
            "pdf_text_tokens": self._totals["pdf_text_tokens"],
            "pdf_visual_tokens": self._totals["pdf_visual_tokens"],
            "codecarbon_emissions_kg": emissions_kg,
            "codecarbon_energy_kwh": energy_kwh,
            "codecarbon_energy_kwh_per_1k_tokens": energy_per_1k,
            "codecarbon_carbon_g_per_1k_tokens": carbon_per_1k,
            "total_runtime_seconds": float(total_runtime_seconds),
            "total_runtime_avg_seconds_per_paper": avg_runtime,
            "paper_count": count,
            "paper_seconds_total": self._totals["paper_seconds"],
            "llm_decision_avg_seconds_per_paper": (self._totals["paper_seconds"] / count) if count else 0.0,
            "human_rate_min_per_paper": None,
            "human_minutes_estimate": None,
            "time_saved_minutes": None,
            "time_saved_percent": None,
            "time_saved_note": "time-savings disabled",
            "ubelix_operational_estimate": None,
            "ubelix_assumptions_log": None,
            "output_files": dict(output_files or {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        lines = [json.dumps(record, ensure_ascii=False) + "\n" for record in self._records]
        lines.append(json.dumps(total_record, ensure_ascii=False) + "\n")
        self.config.resource_log_path.write_text("".join(lines), encoding="utf-8")


class ResourceUsageEngine:
    """Dominant Kai-style facade used by simulation runners."""

    def __init__(
        self,
        resource_log_path: Path,
        enable_tracking: bool = True,
        enable_codecarbon: bool = False,
        stage: str = "full_pa_simulation",
        run_label: str = "run",
        run_id: str = "",
        enable_time_savings: bool = False,
    ) -> None:
        self.config = ResourceUsageConfig(
            resource_log_path=resource_log_path,
            enable_tracking=enable_tracking,
            enable_codecarbon=enable_codecarbon,
            stage=stage,
            run_label=run_label,
            run_id=run_id,
            enable_time_savings=enable_time_savings,
        )
        self._tracker = ResourceUsageTracker(self.config)

    def start_run(self) -> None:
        self._tracker.start_run()

    def log_paper(self, **kwargs: Any) -> None:
        self._tracker.log_paper(**kwargs)

    def stop_run(
        self,
        total_runtime_seconds: float,
        paper_count: int | None = None,
        *,
        run_status: str = "success",
        error_type: str | None = None,
        error_message: str | None = None,
        output_files: Mapping[str, str] | None = None,
    ) -> None:
        self._tracker.stop_run(
            total_runtime_seconds=total_runtime_seconds,
            paper_count=paper_count,
            run_status=run_status,
            error_type=error_type,
            error_message=error_message,
            output_files=output_files,
        )
