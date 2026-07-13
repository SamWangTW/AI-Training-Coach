"""Layer 2 evals: assert the agent calls the correct tools for each question.

Uses the real tool implementations from garmin_mcp/server.py wrapped as
LangChain tools, querying the real garmin.db. Only the memory client is
mocked since mem0 is not needed to test tool selection.

A test passes when:
  - every tool in must_call appears in the agent's tool calls
  - every tool in must_not_call does NOT appear
"""
import os
import sys
from pathlib import Path
import pytest
from unittest.mock import MagicMock, patch
from langchain_core.tools import StructuredTool
from langchain_core.messages import AIMessage

# Make garmin_mcp importable and point it at the real database
_GARMIN_DIR = Path(__file__).parent.parent / "garmin-givemydata"
os.environ.setdefault("GARMIN_DATA_DIR", str(_GARMIN_DIR))
if str(_GARMIN_DIR) not in sys.path:
    sys.path.insert(0, str(_GARMIN_DIR))

from garmin_mcp import server as _server

from agent.graph import create_graph
from agent.tools import get_custom_tools


# ── Wrap real server functions as LangChain tools ─────────────────────────────

def _wrap(fn) -> StructuredTool:
    """Wrap a garmin_mcp server function as a LangChain StructuredTool."""
    return StructuredTool.from_function(func=fn, name=fn.__name__)


def _all_real_tools() -> list:
    """Real Garmin tool implementations + custom analysis tools."""
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
def graph():
    """Agent graph with real Garmin tools and a no-op memory client."""
    with patch("agent.nodes.get_memory_client") as mock_mc:
        mock_instance = MagicMock()
        mock_instance.search_for_user.return_value = []
        mock_instance.add.return_value = None
        mock_mc.return_value = mock_instance
        yield create_graph(_all_real_tools())


def _tools_called(result: dict) -> list[str]:
    """Return all tool names the agent called during the run."""
    return [
        tc["name"]
        for msg in result.get("messages", [])
        if isinstance(msg, AIMessage)
        for tc in (getattr(msg, "tool_calls", None) or [])
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

_CONFIG = {"configurable": {"thread_id": "test"}}


@pytest.mark.parametrize("question, must_call, must_not_call", [
    (
        "how did I sleep last night?",
        ["garmin_sleep"],
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
        ["garmin_steps"],
        ["garmin_activities", "garmin_sleep"],
    ),
])
async def test_agent_calls_correct_tools(question, must_call, must_not_call, graph):
    result = await graph.ainvoke(
        {
            "messages": [{"role": "user", "content": question}],
            "user_id": "test",
            "memories": [],
        },
        config=_CONFIG,
    )

    called = _tools_called(result)

    for tool in must_call:
        assert tool in called, (
            f"\nQuestion:        {question!r}"
            f"\nExpected call:   {tool!r}"
            f"\nActually called: {called}"
        )

    for tool in must_not_call:
        assert tool not in called, (
            f"\nQuestion:            {question!r}"
            f"\nExpected NOT called: {tool!r}"
            f"\nActually called:     {called}"
        )
