"""Read-only binary context analysis of existing empirical PA v1.2 runs.

Run from the repository root with --seed14-dir, --seed96-dir and --output-dir.
Only aggregate tables and source hashes are exported; no participant identifiers
or daily simulation payloads are written. No simulation modules are imported.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from statistics import NormalDist

try:
    from .final_h1_h4_analysis import classify_record
except ImportError:  # Direct script invocation
    from final_h1_h4_analysis import classify_record


OLD_CLASSES = ("supportive", "mixed_neutral", "hindering")
NEW_CLASSES = ("supportive", "non_supportive")
SOURCE_FILES = ("run_config.json", "simulation_run_manifest.json",
                "full_simulation_trace.json", "contexts_compact.json", "daily_decision_log.csv")


def binary_class(score: object) -> str:
    """Reject missing/non-finite scores instead of silently assigning a class."""
    if isinstance(score, bool) or not isinstance(score, Real) or not math.isfinite(score):
        raise ValueError("Missing or invalid final_context_score")
    return "supportive" if score > 0 else "non_supportive"


def classify_records(records: list[dict], contexts: list[dict], seed: int,
                     aliases: dict[str, str]) -> list[dict]:
    """Join one-to-one; preserve each source decision payload without mutation."""
    def key(row):
        return row["persona_id"], row["day_index"]

    lookup = {key(row): row for row in contexts}
    keys = [key(row) for row in records]
    if len(lookup) != len(contexts) or len(set(keys)) != len(keys) or set(keys) != set(lookup):
        raise ValueError("Duplicate or unmatched persona-days in trace/contexts")
    rows = []
    for record in records:
        context = lookup[key(record)]
        if context["calendar_date"] != record["calendar_date"]:
            raise ValueError("Context/trace calendar date mismatch")
        if record["was_physical_activity_planned_today"] or record.get("planned_physical_activity"):
            raise ValueError("Expected unplanned empirical v1.2 days")
        hours = context["hourly_context_24h"]
        if len(hours) != 24 or sorted(h["hour"] for h in hours) != list(range(24)):
            raise ValueError("Expected exactly 24 unique hourly contexts")
        result = classify_record({**record, "hourly_context_24h": hours})
        try:
            label = binary_class(result.get("final_context_score"))
        except ValueError as exc:
            raise ValueError(f"Seed {seed}, {aliases[record['persona_id']]}, "
                             f"day {record['day_index']}: {exc}") from exc
        decision = record["pa_decision"]
        performed = record["closed_loop_update"]["activity_done"]
        duration = decision["duration_min"]
        if not isinstance(performed, bool) or decision["decision_label"] not in ("skip_activity", "extra_activity"):
            raise ValueError("Invalid empirical activity decision")
        if (decision["decision_label"] == "extra_activity") != performed or (duration > 0) != performed:
            raise ValueError("Inconsistent activity outcome/duration")
        rows.append({"seed": seed, "medoid": aliases[record["persona_id"]],
                     "day_index": record["day_index"], **result,
                     "binary_context_class": label, "activity_performed": performed,
                     "source_pa_decision": decision})
    return rows


def wilson(successes: int, n: int) -> tuple[float | None, float | None]:
    if n == 0:
        return None, None
    z = NormalDist().inv_cdf(0.975)
    p = successes / n
    denominator = 1 + z*z/n
    center = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return max(0.0, center-half), min(1.0, center+half)


def summarize(rows: list[dict]) -> list[dict]:
    groups = [("all", "all", rows)]
    for seed in sorted({r["seed"] for r in rows}):
        group = [r for r in rows if r["seed"] == seed]
        groups.append((seed, "all", group))
        groups.extend((seed, medoid, [r for r in group if r["medoid"] == medoid])
                      for medoid in sorted({r["medoid"] for r in group}))
    output = []
    for seed, medoid, group in groups:
        for scheme, column, classes in (("old", "context_class", OLD_CLASSES),
                                        ("binary", "binary_context_class", NEW_CLASSES)):
            if any(r[column] not in classes for r in group):
                raise ValueError("Unexpected context class")
            for label in classes:
                subset = [r for r in group if r[column] == label]
                n = len(subset)
                pa = sum(r["activity_performed"] for r in subset)
                low, high = wilson(pa, n)
                output.append(dict(seed=seed, medoid=medoid, classification=scheme,
                                   category=label, days=n, pa_days=pa,
                                   pa_proportion=pa/n if n else None,
                                   wilson95_low=low, wilson95_high=high,
                                   no_downtime_days=sum(r["downtime_length"] == 0 for r in subset)))
    return output


def source_hashes(root: Path) -> dict[str, str]:
    return {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def load_run(root: Path, seed: int) -> tuple[list[dict], list[dict]]:
    def read(name):
        return json.loads((root/name).read_text(encoding="utf-8"))
    config = read("run_config.json")
    if any(config.get(k) != v for k, v in dict(base_seed=seed, n_days=90, n_personas=4,
                                              empirical_pa_v1_2=True).items()):
        raise ValueError("Wrong seed, horizon, persona count or simulation version")
    if read("simulation_run_manifest.json").get("run_status") != "success":
        raise ValueError("Run is not complete")
    records = read("full_simulation_trace.json")["records"]
    personas = {r["persona_id"] for r in records}
    if len(records) != 360 or len(personas) != 4:
        raise ValueError("Expected 360 observations for four medoids")
    for persona in personas:
        days = [r["day_index"] for r in records if r["persona_id"] == persona]
        if len(days) != 90 or set(days) != set(range(90)):
            raise ValueError("Expected unique days 0..89 per medoid")
    return records, read("contexts_compact.json")["llm_contexts"]


def write_report(path: Path, table: list[dict], rows: list[dict]) -> None:
    lines = ["# Binäre Kontextauswertung AIcoPA v1.2", "",
             "Auswertungsentscheidung; die Simulationslogik bleibt unverändert. "
             "Bestehende 90-Tage-Runs: Seeds 14 und 96, vier Medoids, 720 Beobachtungen.", "",
             "Alt: supportive ≥2, neutral (mixed_neutral) zwischen −2 und +2, hindering ≤−2. "
             "Neu: supportive >0, non_supportive ≤0. Die bestehenden Dimensionen und Overrides "
             "werden unverändert über classify_record aus final_h1_h4_analysis.py berechnet. "
             "Keine Downtime: final −2; leichte Krankheit: höchstens 0; mittel/schwer: −2.", "",
             "Alle Tage ohne Downtime bleiben im primären Nenner. "
             f"Separat gezählt: {sum(r['downtime_length'] == 0 for r in rows)} Tage "
             + "; ".join(f"Seed {s}: {sum(r['downtime_length'] == 0 for r in rows if r['seed'] == s)}"
                         for s in (14, 96)) + ".", "",
             "M1–M4 sind stabile Aliase nach sortierter Simulations-Persona-ID; "
             "dieselben vier IDs wurden über beide Seeds geprüft. Keine T1-Kennungen exportiert.", "",
             "PA-Anteil = PA-Tage / alle Tage der jeweiligen Kategorie. "
             "95%-Wilson-Intervalle sind deskriptiv; leere Kategorien: —.", "",
             "| Seed | Medoid | Schema | Kategorie | Tage | PA-Tage | PA % | Wilson 95 % | Ohne Downtime |",
             "|---|---|---|---|---:|---:|---:|---|---:|"]
    for row in table:
        pct = "—" if row["pa_proportion"] is None else f"{100*row['pa_proportion']:.1f}"
        ci = "—" if row["wilson95_low"] is None else f"{100*row['wilson95_low']:.1f}–{100*row['wilson95_high']:.1f}"
        category = "neutral" if row["category"] == "mixed_neutral" else row["category"]
        lines.append(f"| {row['seed']} | {row['medoid']} | {row['classification']} | {category} | "
                     f"{row['days']} | {row['pa_days']} | {pct} | {ci} | {row['no_downtime_days']} |")
    lines += ["", "Methodische Einschränkungen: Wiederholte Tage innerhalb einer Persona und "
              "zeitliche Abhängigkeiten werden durch Wilson-Intervalle nicht modelliert. Vier Medoids "
              "und zwei Seeds erlauben keine Bevölkerungsinferenz. Der Laufordner für Seed 96 ist als "
              "Kontext-Stresstest bezeichnet; ein möglicher Einfluss der Seed-Auswahl wird hier nicht "
              "quantifiziert. Die Gegenüberstellung ist deskriptiv. Binär supportive "
              "schliesst nun auch Score +1 ein; Score 0 bleibt ausdrücklich non_supportive. "
              "Die Intervalle messen keine Unsicherheit der LLM-Wahrscheinlichkeiten.", "",
              "Dateien: Analysis/empirical_context_binary_v1_2.py (separate Auswertung), "
              "Analysis/tests/test_empirical_context_binary_v1_2.py (ausschliesslich synthetisch), "
              "Analysis/empirical_context_binary_v1_2_review.md (Prüf- und Reproduktionsnotiz). "
              "Die MA-Routine und Simulation-Dateien wurden nicht geändert. "
              "summary.csv und provenance.json enthalten nur Aggregate bzw. Prüfsummen. "
              "Testresultate stehen in der Prüfnotiz."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed14-dir", type=Path, required=True)
    parser.add_argument("--seed96-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise FileExistsError("Refusing to overwrite output directory")
    roots = {14: args.seed14_dir, 96: args.seed96_dir}
    before = {seed: source_hashes(root) for seed, root in roots.items()}
    runs = {seed: load_run(root, seed) for seed, root in roots.items()}
    personas = sorted({r["persona_id"] for r in runs[14][0]})
    if set(personas) != {r["persona_id"] for r in runs[96][0]}:
        raise ValueError("Medoids differ between seeds")
    aliases = {persona: f"M{i+1}" for i, persona in enumerate(personas)}
    rows = [row for seed, (records, contexts) in runs.items()
            for row in classify_records(records, contexts, seed, aliases)]
    if len(rows) != 720:
        raise ValueError("Expected all 720 observations")
    after = {seed: source_hashes(root) for seed, root in roots.items()}
    if before != after:
        raise RuntimeError("Source files changed during analysis")
    table = summarize(rows)
    args.output_dir.mkdir(parents=True)
    with (args.output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    provenance = {"observations": len(rows), "sources_unchanged": True, "source_sha256": before,
                  "classifier_sha256": hashlib.sha256(Path(__file__).with_name("final_h1_h4_analysis.py").read_bytes()).hexdigest(),
                  "analysis_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "api_calls": 0}
    (args.output_dir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    write_report(args.output_dir / "report.md", table, rows)
    print(f"Analysed {len(rows)} observations; sources unchanged; aggregates: {args.output_dir}")


if __name__ == "__main__":
    main()
