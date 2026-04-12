"""Custom training analysis tools that extend the Garmin MCP toolset.

These are pure-computation LangChain tools. The agent fetches raw data
via Garmin MCP tools first, then passes it here for analysis.
"""
import json
from datetime import datetime
from langchain_core.tools import tool


@tool
def calculate_training_trend(activities_json: str, weeks: int = 4) -> str:
    """Analyze training load trend over N weeks from a JSON list of Garmin activities.

    Pass the JSON output from list_activities or get_activity_summaries.
    Returns weekly distance, duration, and trend direction.
    """
    try:
        activities = json.loads(activities_json) if isinstance(activities_json, str) else activities_json
        if not isinstance(activities, list):
            activities = activities.get("activities", [])
    except (json.JSONDecodeError, AttributeError):
        return "Error: could not parse activities JSON"

    weekly: dict[tuple, list] = {}
    for act in activities:
        date_str = (act.get("startTimeLocal") or act.get("startTimeGMT") or "")[:10]
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            key = date.isocalendar()[:2]  # (year, week_number)
            weekly.setdefault(key, []).append(act)
        except ValueError:
            continue

    if not weekly:
        return "No activity data found to analyze trends."

    lines = [f"Training trend — last {weeks} weeks:"]
    sorted_weeks = sorted(weekly.items())[-weeks:]
    week_distances = []

    for (year, week), acts in sorted_weeks:
        dist_km = sum(a.get("distance", 0) for a in acts) / 1000
        dur_h = sum(a.get("duration", 0) for a in acts) / 3600
        week_distances.append(dist_km)
        lines.append(f"  {year}-W{week:02d}: {len(acts)} activities | {dist_km:.1f} km | {dur_h:.1f} h")

    if len(week_distances) >= 2:
        delta = week_distances[-1] - week_distances[-2]
        pct = (delta / week_distances[-2] * 100) if week_distances[-2] else 0
        direction = "↑" if delta > 0 else "↓"
        lines.append(f"  Week-over-week: {direction} {abs(pct):.0f}%")

    return "\n".join(lines)


@tool
def extract_personal_records(activities_json: str) -> str:
    """Find best pace performances by distance bucket from a JSON list of Garmin activities.

    Pass the JSON output from list_activities. Returns PRs grouped by approximate distance.
    """
    try:
        activities = json.loads(activities_json) if isinstance(activities_json, str) else activities_json
        if not isinstance(activities, list):
            activities = activities.get("activities", [])
    except (json.JSONDecodeError, AttributeError):
        return "Error: could not parse activities JSON"

    records: dict[int, dict] = {}
    for act in activities:
        dist_m = act.get("distance", 0)
        speed = act.get("averageSpeed", 0)  # m/s
        if dist_m <= 0 or speed <= 0:
            continue

        dist_km = dist_m / 1000
        # Bucket into common race distances
        if dist_km < 2:
            bucket = 1
        elif dist_km < 7:
            bucket = 5
        elif dist_km < 12:
            bucket = 10
        elif dist_km < 17:
            bucket = 15
        elif dist_km < 25:
            bucket = 21
        else:
            bucket = 42

        pace = 1 / speed * 1000 / 60  # min/km
        if bucket not in records or pace < records[bucket]["pace"]:
            records[bucket] = {
                "pace": pace,
                "pace_str": f"{int(pace)}:{int((pace % 1) * 60):02d} /km",
                "dist": f"{dist_km:.1f} km",
                "date": (act.get("startTimeLocal") or "")[:10],
                "name": act.get("activityName", ""),
            }

    if not records:
        return "No running activities with speed data found."

    lines = ["Personal Records (best pace per distance):"]
    for bucket in sorted(records):
        r = records[bucket]
        lines.append(f"  ~{bucket}km: {r['pace_str']}  ({r['dist']} on {r['date']})")

    return "\n".join(lines)


@tool
def compare_weeks(activities_json: str) -> str:
    """Compare this week vs last week from a JSON list of Garmin activities.

    Pass the JSON output from list_activities. Returns side-by-side metrics.
    """
    try:
        activities = json.loads(activities_json) if isinstance(activities_json, str) else activities_json
        if not isinstance(activities, list):
            activities = activities.get("activities", [])
    except (json.JSONDecodeError, AttributeError):
        return "Error: could not parse activities JSON"

    now = datetime.now()
    this_iso = now.isocalendar()

    this_week, last_week = [], []
    for act in activities:
        date_str = (act.get("startTimeLocal") or act.get("startTimeGMT") or "")[:10]
        if not date_str:
            continue
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            y, w, _ = d.isocalendar()
            if (y, w) == (this_iso[0], this_iso[1]):
                this_week.append(act)
            elif w == this_iso[1] - 1 and y == this_iso[0]:
                last_week.append(act)
        except ValueError:
            continue

    def summarize(acts: list) -> dict:
        dist = sum(a.get("distance", 0) for a in acts) / 1000
        dur = sum(a.get("duration", 0) for a in acts) / 3600
        hrs = [a.get("averageHR", 0) for a in acts if a.get("averageHR")]
        avg_hr = round(sum(hrs) / len(hrs)) if hrs else 0
        return {"n": len(acts), "dist": round(dist, 1), "dur": round(dur, 1), "hr": avg_hr}

    t = summarize(this_week)
    l = summarize(last_week)
    dist_change = ((t["dist"] - l["dist"]) / l["dist"] * 100) if l["dist"] else 0

    return (
        f"This week : {t['n']} activities | {t['dist']} km | {t['dur']} h | avg HR {t['hr']} bpm\n"
        f"Last week : {l['n']} activities | {l['dist']} km | {l['dur']} h | avg HR {l['hr']} bpm\n"
        f"Change    : {dist_change:+.0f}% distance"
    )


def get_custom_tools() -> list:
    return [calculate_training_trend, extract_personal_records, compare_weeks]
