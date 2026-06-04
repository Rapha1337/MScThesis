from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from run_agent_context_simulation import main


def test_run_agent_context_simulation_smoke(tmp_path: Path, capsys) -> None:
    output_path = tmp_path / "agent_day_contexts.json"

    main(
        [
            "--n-personas",
            "2",
            "--base-seed",
            "37",
            "--day-index",
            "21",
            "--fitness-hours-week",
            "6",
            "--social-hours-week",
            "8",
            "--work-hours-week",
            "5",
            "--carework-hours-week",
            "7",
            "--workplace-distance-km",
            "3.0",
            "--indoor-activity-distance-km",
            "1.2",
            "--outdoor-activity-distance-km",
            "0.6",
            "--output-path",
            str(output_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert len(payload["personas"]) == 2
    for persona in payload["personas"]:
        assert len(persona["day_context"]["hourly_context_24h"]) == 24
    json.dumps(payload)
    assert "JSON export success: true" in captured.out
