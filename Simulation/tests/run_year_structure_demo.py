from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from persona_wrappers import StudentHoursWrapper
from year_structure import YearStructureGenerator


def main() -> None:
    persona = StudentHoursWrapper.from_zve_student_generic(name="demo_student")
    generator = YearStructureGenerator()
    year = generator.generate_year(persona_id=persona.name, persona_seed=123, parameters=persona)

    block_counts: dict[str, int] = {}
    for week in year.weeks:
        if week.fixed_block_tag:
            block_counts[week.fixed_block_tag] = block_counts.get(week.fixed_block_tag, 0) + 1

    public_holiday_events = [e for e in year.events if e.event_type == "public_holiday"]
    illness_events = [e for e in year.events if e.event_type == "illness"]

    print(f"persona_id: {year.persona_id}")
    print(f"phase_counts: {year.phase_counts}")
    print(f"block_counts: {block_counts}")
    print(f"public_holiday_count: {len(public_holiday_events)}")
    print(f"illness_event_count: {len(illness_events)}")

    high_stress_weeks = [week.week_index for week in year.weeks if week.phase == "high_stress"]
    high_stress_blocks: list[list[int]] = []
    for week_idx in high_stress_weeks:
        if high_stress_blocks and week_idx == high_stress_blocks[-1][-1] + 1:
            high_stress_blocks[-1].append(week_idx)
        else:
            high_stress_blocks.append([week_idx])
    print("high_stress_blocks:")
    for block in high_stress_blocks:
        print(f"  - weeks={block[0]:02d}-{block[-1]:02d} length={len(block)}")

    print("full_year_week_overview:")
    for week in year.weeks:
        print(
            f"  - week={week.week_index:02d} phase={week.phase} "
            f"block={week.fixed_block_tag or '-'} events={week.active_event_ids}"
        )

    print("example_holiday_weeks:")
    holiday_examples = [w for w in year.weeks if w.fixed_block_tag in {"winter_holiday", "summer_holiday"}][:6]
    if not holiday_examples:
        print("  - none")
    for week in holiday_examples:
        print(f"  - week={week.week_index:02d} tag={week.fixed_block_tag} phase={week.phase}")

    print("example_illness_events:")
    if not illness_events:
        print("  - none")
    for event in illness_events[:8]:
        print(
            "  - "
            f"id={event.event_id}, start_week={event.start_week}, start_day={event.start_day}, "
            f"duration_days={event.duration_days}, intensity={event.intensity}, source={event.source}"
        )

    print("example_public_holiday_events:")
    if not public_holiday_events:
        print("  - none")
    for event in public_holiday_events[:8]:
        print(
            "  - "
            f"id={event.event_id}, start_week={event.start_week}, start_day={event.start_day}, "
            f"duration_days={event.duration_days}, intensity={event.intensity if event.intensity is not None else '-'}, source={event.source}"
        )


if __name__ == "__main__":
    main()
