"""Layer 1 evals: assert the router returns the correct tool categories.

Each test case is (user question, minimum expected categories).
The router is allowed to return extra categories — that's fine.
A test fails only when an expected category is missing from the result.
"""
import pytest
from agent.router import route_tools


cases = [
    # Single-category questions — router should be precise
    ("how was my sleep last night?",            {"sleep"}),
    ("what's my VO2max?",                       {"performance"}),
    ("how far did I run this week?",            {"activity"}),
    ("what is my resting heart rate?",          {"health"}),
    ("how many steps did I take today?",        {"body"}),
    ("what are my personal records?",           {"goals"}),
    ("what devices do I have connected?",       {"profile"}),

    # Multi-category questions — router must return all relevant categories
    ("am I overtraining?",                      {"training", "sleep", "health"}),
    ("should I run tomorrow?",                  {"training", "sleep", "health"}),
    ("how is my recovery looking?",             {"training", "health"}),
    ("compare my sleep and training this week", {"sleep", "training"}),
]


@pytest.mark.parametrize("question, expected_categories", cases)
async def test_router_returns_expected_categories(question, expected_categories):
    result = await route_tools(question)
    result_set = set(result)
    missing = expected_categories - result_set
    assert not missing, (
        f"\nQuestion:  {question!r}"
        f"\nExpected at least: {expected_categories}"
        f"\nGot:       {result_set}"
        f"\nMissing:   {missing}"
    )
