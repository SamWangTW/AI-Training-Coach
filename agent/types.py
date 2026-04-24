"""Shared TypedDicts for agent node input/output contracts."""
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]  # in-memory chat history for the current session
    user_id: str
    memories: list[str]  # long-term facts retrieved from mem0 that persist across sessions


# Return types for each node — forces correct key names at the call site
class MemoryUpdate(TypedDict):
    memories: list[str]


class ModelUpdate(TypedDict):
    messages: list[BaseMessage]
