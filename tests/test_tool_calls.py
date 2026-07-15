"""Layer 2 evals: assert the model picks the correct tools for each question.

Calls agent/nodes.py's call_model directly — the single model decision that
picks which tool(s) to invoke — rather than running the full agent graph.
This means the chosen tools are never actually executed (no database read
ever happens), so these tests don't depend on a real garmin.db and can run
in CI. Only the tools' schemas (name, docstring, args) need to exist for the
model to choose from — the underlying functions never run.

A test passes when:
  - every tool in must_call appears in the model's tool calls
  - every tool in must_not_call does NOT appear
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.tools import StructuredTool
from langchain_core.messages import HumanMessage

# Make garmin_mcp importable and point it at the real database
_GARMIN_DIR = Path(__file__).parent.parent / "garmin-givemydata"
os.environ.setdefault("GARMIN_DATA_DIR", str(_GARMIN_DIR))
if str(_GARMIN_DIR) not in sys.path:
    sys.path.insert(0, str(_GARMIN_DIR))

from garmin_mcp import server as _server

from agent.nodes import make_nodes
from agent.tools import get_custom_tools


# ── Wrap real server functions as LangChain tools ─────────────────────────────

def _wrap(fn) -> StructuredTool:
    """Wrap a garmin_mcp server function as a LangChain StructuredTool."""
    return StructuredTool.from_function(func=fn, name=fn.__name__)


def _all_real_tools() -> list:
    """Real Garmin tool schemas + custom analysis tools.

    Only used here for their name/docstring/args — call_model never
    executes them, so none of these functions actually run.
    """
    server_fns = [
        _server.garmin_schema,
        _server.garmin_query,
        _server.garmin_health_summary,
        _server.garmin_activities,
        _server.garmin_trends,
        _server.garmin_sync,
        _server.garmin_today,
        _server.garmin_activity_detail,
        _server.garmin_sleep,
        _server.garmin_training_load,
        _server.garmin_compare,
        _server.garmin_records,
        _server.garmin_fitness_age,
        _server.garmin_hrv,
        _server.garmin_body_battery,
        _server.garmin_stress,
        _server.garmin_heart_rate,
        _server.garmin_spo2,
        _server.garmin_body_composition,
        _server.garmin_devices,
        _server.garmin_week_summary,
        _server.garmin_recovery,
        _server.garmin_training_status,
        _server.garmin_workouts,
        _server.garmin_badges,
        _server.garmin_hydration,
        _server.garmin_respiration,
        _server.garmin_intensity_minutes,
        _server.garmin_floors,
        _server.garmin_steps,
        _server.garmin_calories,
        _server.garmin_blood_pressure,
        _server.garmin_goals,
        _server.garmin_challenges,
        _server.garmin_user_profile,
        _server.garmin_race_predictions,
        _server.garmin_endurance_score,
        _server.garmin_hill_score,
        _server.garmin_vo2max,
        _server.garmin_health_snapshot,
        _server.garmin_gear,
        _server.garmin_daily_events,
        _server.garmin_activity_types,
        _server.garmin_hr_zones,
    ]
    return [_wrap(fn) for fn in server_fns] + get_custom_tools()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def call_model():
    """The agent's model-decision node, with a no-op memory client.

    make_nodes() calls get_memory_client() once up front even though
    call_model itself never uses it — patched here to avoid initializing a
    real mem0 client for a test that doesn't need one.
    """
    with patch("agent.nodes.get_memory_client") as mock_mc:
        mock_mc.return_value = MagicMock()
        _, call_model_fn, _, _, _ = make_nodes(_all_real_tools())
        yield call_model_fn


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("question, must_call_any_of, must_not_call", [
    (
        # garmin_today is a general-purpose "everything about today" tool
        # bound on every request — calling it first for a sleep/steps
        # question is a valid answer on its own, not just garmin_sleep.
        "how did I sleep last night?",
        ["garmin_sleep", "garmin_today"],
        ["garmin_activities"],
    ),
    (
        "what were my runs this week?",
        ["garmin_activities"],
        ["garmin_sleep"],
    ),
    (
        "what's my current VO2max?",
        ["garmin_vo2max"],
        ["garmin_sleep", "garmin_activities"],
    ),
    (
        "how many steps did I take today?",
        ["garmin_steps", "garmin_today"],
        ["garmin_activities", "garmin_sleep"],
    ),
])
async def test_model_picks_correct_tools(question, must_call_any_of, must_not_call, call_model):
    state = {"messages": [HumanMessage(content=question)], "memories": []}
    result = await call_model(state)

    response = result["messages"][0]
    called = [tc["name"] for tc in (getattr(response, "tool_calls", None) or [])]

    assert any(tool in called for tool in must_call_any_of), (
        f"\nQuestion:        {question!r}"
        f"\nExpected one of: {must_call_any_of}"
        f"\nActually called: {called}"
    )

    for tool in must_not_call:
        assert tool not in called, (
            f"\nQuestion:            {question!r}"
            f"\nExpected NOT called: {tool!r}"
            f"\nActually called:     {called}"
        )
