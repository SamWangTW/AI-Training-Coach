"""LangGraph agent graph for the Garmin Training Coach."""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from agent.nodes import make_nodes


# State is a dictionary that holds everything the graph needs to pass between nodes for one conversation
class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]  # in-memory chat history for the current session
    user_id: str
    memories: list[str]  # long-term facts retrieved from mem0 that persist across sessions


def create_graph(tools: list):
    """Build and compile the training coach agent graph.

    Args:
        tools: Combined list of Garmin MCP tools + custom analysis tools.

    Returns:
        A compiled LangGraph graph with in-memory checkpointing.
    """
    retrieve_memories, call_model, save_memories, should_continue, tool_node = make_nodes(tools)

    builder = StateGraph(State)

    # ("node name", function to run)
    builder.add_node("retrieve_memories", retrieve_memories)
    builder.add_node("call_model", call_model)
    builder.add_node("tools", tool_node)
    builder.add_node("save_memories", save_memories)

    builder.add_edge(START, "retrieve_memories")
    builder.add_edge("retrieve_memories", "call_model")
    builder.add_conditional_edges(
        "call_model",       # 1. which node this decision comes FROM
        should_continue,    # 2. the function that decides where to go (tools or save_memories)
        {"tools": "tools", "save_memories": "save_memories"},
    )
    builder.add_edge("tools", "call_model")
    builder.add_edge("save_memories", END)

    return builder.compile(checkpointer=MemorySaver())
