"""Tool router — classifies user intent and returns only the relevant tools.

Instead of binding all 44 Garmin tools on every request, a lightweight Haiku
call first classifies the user's question into categories, then only the tools
for those categories are bound to the main Sonnet model call.

This cuts tool description tokens by ~80-90% per request.
"""
import json

from langchain_anthropic import ChatAnthropic

# ── Category → tool name mapping ─────────────────────────────────────────────

TOOL_CATEGORIES: dict[str, list[str]] = {
    "activity": [
        "garmin_activities",
        "garmin_activity_detail",
        "garmin_activity_types",
        "garmin_compare",
        "garmin_week_summary",
        "calculate_training_trend",
        "extract_personal_records",
        "compare_weeks",
    ],
    "sleep": [
        "garmin_sleep",
    ],
    "health": [
        "garmin_heart_rate",
        "garmin_hrv",
        "garmin_body_battery",
        "garmin_stress",
        "garmin_spo2",
        "garmin_respiration",
        "garmin_blood_pressure",
        "garmin_health_snapshot",
        "garmin_health_summary",
    ],
    "training": [
        "garmin_training_load",
        "garmin_training_status",
        "garmin_recovery",
        "garmin_intensity_minutes",
    ],
    "performance": [
        "garmin_vo2max",
        "garmin_endurance_score",
        "garmin_hill_score",
        "garmin_race_predictions",
        "garmin_fitness_age",
    ],
    "body": [
        "garmin_body_composition",
        "garmin_hydration",
        "garmin_calories",
        "garmin_steps",
        "garmin_floors",
    ],
    "goals": [
        "garmin_records",
        "garmin_goals",
        "garmin_badges",
        "garmin_challenges",
        "garmin_workouts",
    ],
    "profile": [
        "garmin_user_profile",
        "garmin_devices",
        "garmin_gear",
        "garmin_hr_zones",
        "garmin_activity_types",
    ],
}

# Always included regardless of category — broad context and utility tools
GENERAL_TOOLS: list[str] = [
    "garmin_today",
    "garmin_query",
    "garmin_schema",
    "garmin_trends",
    "garmin_daily_events",
]

ROUTER_PROMPT = """\
You are a tool router for a Garmin training coach. Given the user's message,
return a JSON array of ONLY the necessary categories from this list:

- activity    : workouts, runs, rides, activity history, pace, distance, lap splits
- sleep       : sleep quality, sleep duration, sleep score, sleep stages
- health      : heart rate, HRV, stress, body battery, SpO2, respiration, blood pressure
- training    : training load, training status, recovery time, intensity minutes
- performance : VO2max, endurance score, hill score, race predictions, fitness age
- body        : weight, body composition, hydration, calories, steps, floors
- goals       : personal records, PRs, goals, badges, challenges, planned workouts
- profile     : user profile, devices, gear, heart rate zones

Rules:
- Return ONLY a JSON array of strings, nothing else. Example: ["sleep"]
- Be minimal — only include categories directly needed to answer the question
- DO NOT include categories that are not relevant to the question
- "show me my run" → ["activity"]
- "how was my sleep?" → ["sleep"]
- "what are my PRs?" → ["goals"]
- "am I overtraining?" → ["training", "sleep", "health"]
- "should I run tomorrow?" → ["training", "sleep", "health"]
- "what is my VO2max?" → ["performance"]
- "how many steps today?" → ["body"]
- For general greetings with no specific topic, return ["activity"]
"""

_router_model = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0)


async def route_tools(user_message: str) -> list[str]:
    """Classify user intent and return the relevant category names."""
    response = await _router_model.ainvoke(
        [
            {"role": "system", "content": [{"type": "text", "text": ROUTER_PROMPT, "cache_control": {"type": "ephemeral"}}]},
            {"role": "user", "content": user_message},
        ]
    )
    try:
        content = response.content
        if isinstance(content, list):
            content = next((b["text"] for b in content if isinstance(b, dict) and b.get("type") == "text"), "")
        print(f"[router] raw response: {content!r}")
        # Strip markdown code fences if present (e.g. ```json ... ```)
        content = content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        categories = json.loads(content)
        if isinstance(categories, list):
            return [c for c in categories if c in TOOL_CATEGORIES]
    except (json.JSONDecodeError, TypeError):
        pass
    # Fallback — return all categories if parsing fails
    return list(TOOL_CATEGORIES.keys())


def select_tools(all_tools: list, categories: list[str]) -> list:
    """Filter all_tools down to those in the selected categories + general tools."""
    allowed_names = set(GENERAL_TOOLS)
    for cat in categories:
        allowed_names.update(TOOL_CATEGORIES.get(cat, []))

    selected = [t for t in all_tools if t.name in allowed_names]
    return selected
