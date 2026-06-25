from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Mapping

from run_behavior_probability_estimation import BEHAVIOR_PROBABILITY_KEYS, MODEL_NAME, TEMPERATURE, TOP_P, MAX_TOKENS, load_behavior_probability_prompt, parse_and_validate_behavior_probabilities


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare_probability_outputs(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    stats = {}
    for key in BEHAVIOR_PROBABILITY_KEYS:
        values = [float(r["parsed_policy"][key]) for r in results]
        stats[key] = {"mean": mean(values), "standard_deviation": pstdev(values) if len(values) > 1 else 0.0, "minimum": min(values), "maximum": max(values), "maximum_absolute_difference": max(abs(v - values[0]) for v in values)}
    return {"repetitions": len(results), "input_hashes_identical": len({r["serialized_input_hash"] for r in results}) == 1, "raw_output_hashes_identical": len({r["raw_output_hash"] for r in results}) == 1, "parsed_policies_identical": len({json.dumps(r["parsed_policy"], sort_keys=True) for r in results}) == 1, "category_statistics": stats}


def run_live(serialized_input: str, prompt: str, repetitions: int, *, model: str, seed: int | None) -> list[dict[str, Any]]:
    from run_behavior_probability_estimation import get_client
    client = get_client()
    out = []
    for _ in range(repetitions):
        kwargs: dict[str, Any] = {"model": model, "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": serialized_input}], "temperature": TEMPERATURE, "top_p": TOP_P, "max_tokens": MAX_TOKENS}
        if seed is not None:
            kwargs["seed"] = seed
        response = client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content or ""
        out.append({"prompt_hash": sha256_text(prompt), "serialized_input_hash": sha256_text(serialized_input), "raw_output_hash": sha256_text(raw), "parsed_policy": parse_and_validate_behavior_probabilities(raw)["probabilities"]})
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Optional LLM1 repeatability diagnostic; not used by normal simulations.")
    p.add_argument("--serialized-input-file", type=Path, required=True)
    p.add_argument("--prompt-path", type=Path, default=Path(__file__).with_name("BehaviorProbability_Prompt.md"))
    p.add_argument("--repetitions", type=int, default=10)
    p.add_argument("--model", default=MODEL_NAME)
    p.add_argument("--llm-seed", type=int)
    args = p.parse_args()
    serialized = args.serialized_input_file.read_text(encoding="utf-8")
    prompt = load_behavior_probability_prompt(args.prompt_path)
    results = run_live(serialized, prompt, args.repetitions, model=args.model, seed=args.llm_seed)
    print(json.dumps({"runs": results, "comparison": compare_probability_outputs(results)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
