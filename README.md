# Garmin Training Coach

> An AI agent that turns your Garmin wearable data into a personal running coach — powered by a LangGraph orchestration layer, MCP tool integration, and mem0 long-term memory.

Not a chatbot with generic fitness tips. A stateful agent that reasons over **your actual training history and personal context** before answering.

---

## Demo

> **You:** Am I overtraining this week?

> **Coach:** Your training load hit 297 this week — up 34% from last week's 221. Your recovery score has been below 50% for 3 consecutive days, and your average heart rate on easy runs is trending 8bpm higher than your baseline. Given the knee tightness you mentioned after Tuesday's run, I'd recommend keeping tomorrow easy — a 30–40 min zone 2 run or a rest day. Back off before your body forces you to.

*Every number came from live Garmin data. The knee context came from mem0 — remembered automatically from a previous conversation.*

---

## Why This Is an AI Infrastructure Project

This isn't a wrapper around the Claude API. The interesting engineering is in the layer between the user and the LLM:

- **Tool orchestration** — LangGraph agent dynamically decides which Garmin MCP tools to call based on the question, retries on failure, and branches on partial results
- **Long-term memory** — mem0 automatically extracts and stores personal context (injuries, goals, subjective feel) across conversations, retrieved semantically at query time
- **Context assembly** — agent combines live Garmin data + mem0 memories into a focused context window, avoiding token waste
- **Observability** — every agent decision, tool call, and token traced in LangSmith

---

## How It Works

```
You ask a question
        ↓
FastAPI receives your prompt
        ↓
LangGraph agent decides what it needs:
  ├── Garmin MCP   →  queries your local SQLite database (garmin.db)
  ├── mem0         →  retrieves your personal context (injuries, goals, how you felt)
  └── Claude API   →  combines everything into a personalized answer
        ↓
Advice based on YOUR data AND your history — not generic templates
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| **LLM** | [Claude API](https://anthropic.com) | Reasoning and response generation |
| **Agent** | [LangGraph](https://langchain-ai.github.io/langgraph/) | Multi-step, stateful agent orchestration |
| **Garmin data** | [garmin-givemydata](https://github.com/nrvim/garmin-givemydata) | Browser-based Garmin Connect extraction into local SQLite |
| **Garmin MCP** | FastMCP (44 tools) | Exposes SQLite data as MCP tools for the agent |
| **Custom tools** | LangChain tools | Training trend, personal records, week comparison |
| **Memory** | [mem0](https://github.com/mem0ai/mem0) | Long-term personal memory across conversations |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com) | REST API layer |
| **UI** | [Streamlit](https://streamlit.io) | Chat interface |
| **Observability** | [LangSmith](https://smith.langchain.com) | Agent trace monitoring |

---

## Features

- **Natural language queries** — ask anything about your training in plain English
- **Local Garmin data** — no cloud dependency, all data stored in a local SQLite database (47 tables, 10+ years of history)
- **44 Garmin MCP tools** — activities, sleep, HRV, body battery, training load, VO2max, race predictions, and more
- **Persistent personal memory** — mem0 automatically remembers your injuries, goals, and how you felt after runs — across every conversation, zero manual setup
- **Stateful agent** — LangGraph decides which tools to call, retries on failure, branches on partial results
- **Full observability** — every agent decision traceable in LangSmith

### Custom Analysis Tools

On top of the 44 Garmin MCP tools, this project adds:

| Tool | What It Does |
|---|---|
| `calculate_training_trend` | Summarizes load trend over N weeks |
| `extract_personal_records` | Best performances by distance bucket |
| `compare_weeks` | Side-by-side current vs last week |

---

## Project Structure

```
garmin-training-coach/
├── agent/
│   ├── graph.py          # LangGraph agent graph definition
│   ├── nodes.py          # Node functions (retrieve_memories, call_model, save_memories)
│   └── tools.py          # Custom analysis tools
├── api/
│   └── main.py           # FastAPI app — connects MCP server at startup
├── memory/
│   └── client.py         # mem0 3-tier setup: hosted → local → JSON fallback
├── ui/
│   └── app.py            # Streamlit chat interface
├── garmin-givemydata/    # Local Garmin data pipeline
│   ├── garmin.db         # SQLite database (47 tables, your full Garmin history)
│   ├── garmin_mcp/
│   │   ├── server.py     # 44 MCP tools over SQLite
│   │   ├── sync.py       # Incremental sync (today + yesterday)
│   │   └── db.py         # SQLite connection layer
│   └── run_mcp.py        # MCP server entry point
├── datasette-metadata.yaml  # Table browser config for garmin.db
├── start.bat             # One-command launcher (backend + frontend)
└── .env.example
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### 1. Clone the repo

```bash
git clone https://github.com/SamWangTW/AI-Training-Coach
cd AI-Training-Coach
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=your_key_here
MEM0_API_KEY=your_key_here        # get from app.mem0.ai, or leave blank for local
LANGSMITH_API_KEY=your_key_here   # optional but recommended
```

### 4. Set up Garmin data

Install dependencies for the Garmin data pipeline:

```bash
cd garmin-givemydata
bash setup.sh     # macOS/Linux
setup.bat         # Windows
```

Add your Garmin credentials to `garmin-givemydata/.env`:

```env
GARMIN_EMAIL=your@email.com
GARMIN_PASSWORD=yourpassword
```

Fetch your full Garmin history (first run takes ~30 min for 10 years of data):

```bash
venv/Scripts/python.exe garmin_givemydata.py   # Windows
venv/bin/python garmin_givemydata.py           # macOS/Linux
```

### 5. Run the app

```bash
.\start.bat     # Windows — opens backend + frontend in two terminals
```

Or manually:

```bash
# Terminal 1 — backend
.venv\Scripts\uvicorn api.main:app --reload

# Terminal 2 — frontend
.venv\Scripts\streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) and start asking questions about your training.

---

## Syncing New Activities

After a run, sync your latest data in one of two ways:

**Via the chat UI:**
```
"Sync my latest Garmin data"
```

**Via the terminal:**
```bash
cd garmin-givemydata
venv/Scripts/python.exe -m garmin_mcp.sync
```

The sync fetches today and yesterday from Garmin Connect, skips activities already in the database, and completes in under a minute once the browser session is established.

---

## Browsing Your Data

To explore the raw SQLite database in a web UI (similar to Supabase):

```bash
datasette garmin-givemydata/garmin.db --metadata datasette-metadata.yaml
```

Open [http://localhost:8001](http://localhost:8001) — browse all 47 tables, filter rows, and run SQL queries.

Alternatively, install the **SQLite Viewer** extension in VS Code and click `garmin.db` directly.

---

## How Memory Works

mem0 automatically builds your personal profile from conversations — no manual setup needed.

Just chat naturally:

```
You: "My left knee felt tight around km 7 today"
          ↓
mem0 automatically stores:
  → "experiences left knee tightness on longer efforts"

You (3 days later): "Should I do a long run today?"
          ↓
mem0 retrieves: knee history + your half marathon goal
          ↓
Coach: "Given your recent knee tightness, I'd cap today
        at 8km and keep it easy."
```

The agent gets smarter the more you use it — without you doing anything extra. View stored memories at [app.mem0.ai](https://app.mem0.ai).

---

## Architecture Decisions

**Why LangGraph over a simple LangChain chain?**
The agent needs to loop. If Claude decides it needs multiple tools to answer a question, LangGraph's graph model handles the tool → model → tool cycle cleanly. A linear chain can't branch or retry based on what data comes back.

**Why local SQLite over a cloud database?**
Health data (sleep, HRV, stress, location) is sensitive. Keeping it local means it never leaves your machine. The MCP server exposes a read-only query interface so the agent can't modify data. If you want multi-device access or to build a multi-user product, migrating to Supabase (same schema, Postgres) is a straightforward next step.

**Why mem0 over a custom RAG pipeline?**
RAG is the right tool for unstructured documents. Your Garmin data is structured and queryable — SQL is more precise than embedding similarity search for "what was my training load last week." mem0 is used only for the unstructured personal context that comes out of conversation: injuries, goals, how you felt. It extracts and stores these automatically, which is the key difference from a manual note-taking approach.

**Why a local MCP server over the npm Garmin package?**
Garmin deployed aggressive bot detection in March 2026 that broke all Python HTTP libraries. The local MCP server ([garmin-givemydata](https://github.com/nrvim/garmin-givemydata)) uses a browser-based approach to bypass this, stores data in a local SQLite database, and exposes it via 44 MCP tools. This gives the agent precise, structured access to 10+ years of history without re-fetching from Garmin on every query.

---

## Roadmap

- [ ] Interval training analysis — detect and compare track/interval sessions
- [ ] Automatic post-run analysis triggered after each sync
- [ ] Weekly training summary pushed to email
- [ ] Training plan generation with week-by-week structure
- [ ] Evaluation suite — test agent correctness on known coaching scenarios

---

## Acknowledgements

Garmin data pipeline powered by [garmin-givemydata](https://github.com/nrvim/garmin-givemydata) — browser-based Garmin Connect extraction with 44 MCP tools and a local SQLite database.

Memory layer powered by [mem0](https://github.com/mem0ai/mem0) — open source universal memory for AI agents.

---

## License

MIT
