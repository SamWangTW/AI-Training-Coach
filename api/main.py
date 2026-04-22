"""FastAPI backend for the Garmin Training Coach.

Startup sequence:
  1. Sync latest Garmin data (today + yesterday)
  2. Connect to Garmin MCP server (stdio subprocess via langchain-mcp-adapters)
  3. Load custom analysis tools
  4. Compile the LangGraph agent with all tools
  5. Serve /chat and /health endpoints

Run with:
    uvicorn api.main:app --reload
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage
from pydantic import BaseModel

from agent.graph import create_graph
from agent.tools import get_custom_tools

# ── MCP server config ─────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parent.parent
_GARMIN_DIR = _REPO_ROOT / "garmin-givemydata"
_PYTHON = _GARMIN_DIR / "venv" / "Scripts" / "python.exe" if sys.platform == "win32" else _GARMIN_DIR / "venv" / "bin" / "python"

GARMIN_MCP = {
    "command": str(_PYTHON),
    "args": [str(_GARMIN_DIR / "run_mcp.py")],
    "transport": "stdio",
    "cwd": str(_GARMIN_DIR),
    "env": {"GARMIN_DATA_DIR": str(_GARMIN_DIR)},
}


# ── Lifespan ──────────────────────────────────────────────────────────────────

def _auto_sync():
    """Run incremental Garmin sync at startup. Non-blocking — failures are logged, not raised."""
    import sys
    sys.path.insert(0, str(_GARMIN_DIR))
    try:
        from garmin_mcp.sync import incremental_sync
        print("[startup] syncing latest Garmin data...")
        result = incremental_sync()
        if result.get("status") == "ok":
            print(f"[startup] sync complete — {result.get('total_upserted', 0)} records upserted")
        else:
            print(f"[startup] sync failed: {result.get('message', 'unknown error')}")
    except Exception as e:
        print(f"[startup] sync skipped ({e})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _auto_sync()

    custom_tools = get_custom_tools()

    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
        # v0.1.0+ — no longer a context manager; create client and await get_tools()
        mcp_client = MultiServerMCPClient({"garmin": GARMIN_MCP})
        mcp_tools = await mcp_client.get_tools()
        app.state.mcp_client = mcp_client  # keep reference alive for the process lifetime
        print(f"[startup] loaded {len(mcp_tools)} Garmin MCP tools + {len(custom_tools)} custom tools")
        app.state.graph = create_graph(mcp_tools + custom_tools)
    except Exception as e:
        print(f"[startup] Garmin MCP unavailable ({e}) — running with custom tools only")
        app.state.graph = create_graph(custom_tools)

    yield


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Garmin Training Coach API", version="0.1.0", lifespan=lifespan)


# ── Schemas ───────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"


class ChatResponse(BaseModel):
    response: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": request.user_id}}

    try:
        result = await graph.ainvoke(
            {
                "messages": [{"role": "user", "content": request.message}],
                "user_id": request.user_id,
                "memories": [],
            },
            config=config,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Return the last non-tool-call AI message
    for msg in reversed(result.get("messages", [])):
        if (
            isinstance(msg, AIMessage)
            and isinstance(msg.content, str)
            and msg.content
            and not getattr(msg, "tool_calls", None)
        ):
            return ChatResponse(response=msg.content)

    raise HTTPException(status_code=500, detail="Agent produced no response")


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    graph = app.state.graph
    config = {"configurable": {"thread_id": request.user_id}}

    async def generate():
        async for event in graph.astream_events(
            {
                "messages": [{"role": "user", "content": request.message}],
                "user_id": request.user_id,
                "memories": [],
            },
            config=config,
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream": #Ignore everything except token events. Skip node starts, tool calls, tool results — only care about text being generated.
                chunk = event["data"]["chunk"] 
                if isinstance(chunk.content, str) and chunk.content: #Make sure the token is actual text and not empty. During tool calls the model sometimes emits empty chunks.
                    yield chunk.content #Send this token out immediately. yield is what makes generate() a stream — instead of returning everything at once, it hands out one token at a time as they're ready

    return StreamingResponse(generate(), media_type="text/plain")
