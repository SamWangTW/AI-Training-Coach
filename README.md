# 🏃 Garmin Training Coach

A conversational AI training coach that connects to your Garmin Connect account and gives you **personalized training advice based on your actual workout history** — not generic fitness tips.

> *"Should I run hard tomorrow?"* → asks your data, not Google.

---

## Demo

> **You:** Am I overtraining this week?

> **Coach:** Your training load hit 297 this week — up 34% from last week's 221. Your recovery score has been below 50% for 3 consecutive days, and your average heart rate on easy runs is trending 8bpm higher than your baseline. I'd recommend keeping tomorrow easy — a 30–40 min zone 2 run or a rest day. Back off before your body forces you to.

---

## How It Works

```
You ask a question
        ↓
FastAPI receives your prompt
        ↓
LangGraph agent decides what it needs:
  ├── Garmin MCP   →  fetches your real workout data from Garmin Connect
  ├── RAG engine   →  retrieves your personal training notes from Qdrant
  └── Claude API   →  combines everything into a personalized answer
        ↓
Advice based on YOUR data, not generic templates
```

---

## Tech Stack

| Layer | Tool | Purpose |
|---|---|---|
| **LLM** | [Claude API](https://anthropic.com) | Reasoning and response generation |
| **Agent** | [LangGraph](https://langchain-ai.github.io/langgraph/) | Multi-step, stateful agent orchestration |
| **Garmin MCP** | [taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp) | 95+ Garmin Connect tools via MCP |
| **Custom MCP tools** | Python MCP SDK | Extended training analysis tools |
| **Vector DB** | [Qdrant](https://qdrant.tech) | Stores and searches personal training notes |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com) | REST API layer |
| **UI** | [Streamlit](https://streamlit.io) | Chat interface |
| **Observability** | [LangSmith](https://smith.langchain.com) | Agent trace monitoring |

---

## Features

- **Natural language queries** — ask anything about your training in plain English
- **Live Garmin data** — no manual exports, pulls directly from Garmin Connect
- **Personal memory** — remembers your notes, injury history, and goals via RAG
- **Smart agent** — LangGraph decides which tools to use and retries on failure
- **Traceable** — every agent decision visible in LangSmith

### Custom Tools (extended from base MCP)

On top of the 95+ tools from [taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp), this project adds:

| Tool | What it does |
|---|---|
| `get_training_trend(weeks=4)` | Summarizes your load trend over N weeks |
| `get_personal_records()` | Your best performances by distance |
| `compare_weeks()` | Side-by-side current vs last week |

---

## Example Questions You Can Ask

- *"Am I overtraining this week?"*
- *"What's my optimal race pace based on recent runs?"*
- *"Build me a 10K training plan based on my current fitness"*
- *"Which days of the week do I perform best?"*
- *"My heart rate has been higher than usual — what does that mean?"*
- *"How does this week compare to last week?"*

---

## Project Structure

```
garmin-training-coach/
├── agent/
│   ├── graph.py          # LangGraph agent definition
│   ├── nodes.py          # Individual agent nodes
│   └── tools.py          # Tool wrappers for MCP calls
├── api/
│   └── main.py           # FastAPI app
├── mcp/
│   └── custom_tools.py   # Extended Garmin MCP tools
├── rag/
│   ├── ingest.py         # Load notes into Qdrant
│   └── retriever.py      # Search personal notes
├── ui/
│   └── app.py            # Streamlit chat interface
├── evals/
│   ├── test_overtraining.py
│   ├── test_race_pace.py
│   └── test_weekly_summary.py
├── .env.example
├── docker-compose.yml    # Runs Qdrant locally
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Garmin Connect account
- Anthropic API key

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/garmin-training-coach
cd garmin-training-coach
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

```
ANTHROPIC_API_KEY=your_key_here
LANGSMITH_API_KEY=your_key_here   # optional but recommended
QDRANT_URL=http://localhost:6333
```

### 4. Authenticate with Garmin Connect

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp-auth

# Verify it worked
uv run garmin-mcp-auth --verify
```

### 5. Start Qdrant

```bash
docker compose up -d
```

### 6. Run the app

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) and start asking questions about your training.

---

## Adding Personal Notes to RAG

The more context you give it, the more personalized the advice:

```bash
uv run python rag/ingest.py --note "I always feel sluggish when my weekly load exceeds 280"
uv run python rag/ingest.py --note "My left knee gets tight after back-to-back long runs"
uv run python rag/ingest.py --note "Targeting a half marathon in October 2026"
```

Notes are stored in Qdrant and automatically retrieved when relevant to your question.

---

## Running Evals

```bash
uv run pytest evals/ -v
```

Evals test whether the agent gives correct advice on known scenarios — for example, correctly identifying overtraining given a high-load week with low recovery scores.

---

## Architecture Decisions

**Why LangGraph over LangChain?**
The agent needs to branch based on what data it finds. If Garmin returns no data for a date range, it should retry with different parameters rather than silently fail. LangGraph's stateful graph model handles this cleanly — LangChain's linear chains don't.

**Why RAG for personal notes instead of system prompt?**
The system prompt has a fixed size limit. As your notes grow over months of training, RAG scales infinitely and only retrieves what's relevant to your current question — keeping Claude's context window focused.

**Why Qdrant over ChromaDB?**
Qdrant is production-ready with a proper client library, Docker support, and persistent storage out of the box. ChromaDB is easier to get started with but harder to run reliably in the long term.

---

## Acknowledgements

Built on top of [garmin_mcp](https://github.com/Taxuspt/garmin_mcp) by [@Taxuspt](https://github.com/Taxuspt) — an excellent open source MCP server covering 95%+ of the Garmin Connect API. Extended with custom training analysis tools for this project.

---

## License

MIT
