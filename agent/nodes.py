"""LangGraph node functions for the training coach agent."""
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt import ToolNode

from memory.client import get_memory_client
from agent.types import MemoryUpdate, ModelUpdate

SYSTEM_PROMPT = """\
You are a personal AI running coach with direct access to the user's Garmin Connect data.

You have Garmin MCP tools to fetch real workout history, heart rate, sleep, HRV, recovery scores,
training load, and more. You also have custom analysis tools for trends, PRs, and week comparisons.

When answering questions:
1. Always call a Garmin tool to fetch fresh data before answering — never rely on data mentioned earlier in the conversation, as it may be stale.
2. Consider the full picture: training load, sleep quality, HRV, stress, and recovery scores.
3. Give specific, actionable coaching advice — not generic fitness tips.
4. Reference personal context (injuries, goals, past feelings) from memory when relevant.

Be direct and coach-like. Lead with the insight, then back it up with data.\
"""


def make_nodes(tools: list) -> tuple:
    """Return all node functions and the tool node, closed over the given tools."""
    memory_client = get_memory_client()

    model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0)
    model_with_tools = model.bind_tools(tools)
    tool_node = ToolNode(tools)

    async def retrieve_memories(state: dict) -> MemoryUpdate:
        user_id = state.get("user_id", "default")
        messages = state.get("messages", [])

        query = ""
        for m in reversed(messages):  # most recent message first
            if isinstance(m, HumanMessage) and isinstance(m.content, str):
                query = m.content
                break

        if not query:
            return MemoryUpdate(memories=[])

        try:
            memories = memory_client.search_for_user(query, user_id=user_id)
        except Exception as e:
            print(f"[memory] retrieve failed (non-critical): {e}")
            memories = []
        return MemoryUpdate(memories=memories)

    async def call_model(state: dict) -> ModelUpdate:
        memories = state.get("memories", [])

        system_content = SYSTEM_PROMPT
        if memories:
            system_content += "\n\n## Personal context from previous conversations:\n"
            system_content += "\n".join(f"- {m}" for m in memories)

        messages = [SystemMessage(content=system_content)] + list(state["messages"])
        response = await model_with_tools.ainvoke(messages)
        return ModelUpdate(messages=[response])

    async def save_memories(state: dict) -> dict:
        user_id = state.get("user_id", "default")
        messages = state.get("messages", [])

        to_save = []
        for m in messages[-4:]:
            if isinstance(m, HumanMessage) and isinstance(m.content, str):
                to_save.append({"role": "user", "content": m.content})
            elif (
                isinstance(m, AIMessage)
                and isinstance(m.content, str)
                and m.content
                and not getattr(m, "tool_calls", None)
            ):
                to_save.append({"role": "assistant", "content": m.content})

        if to_save:
            try:
                memory_client.add(to_save, user_id=user_id)
            except Exception as e:
                print(f"[memory] save failed (non-critical): {e}")

        return {}

    def should_continue(state: dict) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "save_memories"

    return retrieve_memories, call_model, save_memories, should_continue, tool_node
