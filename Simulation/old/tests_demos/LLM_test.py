from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

api_key = os.getenv("UNI_LLM_API_KEY")

if not api_key:
    raise ValueError("UNI_LLM_API_KEY nicht gefunden. Prüfe deine .env-Datei.")

client = OpenAI(
    api_key=api_key,
    base_url="https://gpustack.unibe.ch/v1"
)

response = client.chat.completions.create(
    model="gpt-oss-120b",
    messages=[
        {
            "role": "system",
            "content": (
                "You simulate one agent's daily physical activity decision. "
                "Return valid JSON only. Do not add explanations outside the JSON."
            ),
        },
        {
            "role": "user",
            "content": """
Agent data:
- planned_activity: 20 minute outdoor walk
- planned_time: 13:00
- daily_schedule: work from 08:00-12:00, free from 12:00-14:00, study from 14:00-17:00
- weather: heavy rain
- spatial_context: outdoor route available, indoor gym available
- energy_level: medium
- habit_strength: low
- intention: medium
- perceived_behavioral_control: medium
- stress_level: high

Task:
Decide whether the agent performs the planned activity.
If the planned activity is not performed, decide whether an alternative activity is selected.

Return exactly this JSON structure:
{
  "activity_performed": true/false,
  "selected_action": "planned_activity" or "alternative_activity" or "no_activity",
  "reasoning_short": "...",
  "diary_entry": "...",
  "habit_relevance": "..."
}
"""
        },
    ],
    temperature=0,
    max_tokens=500,
)

print(response.choices[0].message.content)
print(response.usage)