# 🏃 Garmin Training Coach

> An AI agent that turns your Garmin wearable data into a personal running coach — powered by a LangGraph orchestration layer, MCP tool integration, and mem0 long-term memory.

Not a chatbot with generic fitness tips. A stateful agent that reasons over **your actual training history and personal context** before answering.

---

## Demo

> **You:** Am I overtraining this week?

> **Coach:** Your training load hit 297 this week — up 34% from last week's 221. Your recovery score has been below 50% for 3 consecutive days, and your average heart rate on easy runs is trending 8bpm higher than your baseline. Given the knee tightness you mentioned after Tuesday's run, I'd recommend keeping tomorrow easy — a 30–40 min zone 2 run or a rest day. Back off before your body forces you to.

*Every number came from live Garmin API calls. The knee context came from mem0 — remembered automatically from a previous conversation.*

---

## Why This Is an AI Infrastructure Project

This isn't a wrapper around the Claude API. The interesting engineering is in the layer between the user and the LLM:

- **Tool orchestration** — LangGraph agent dynamically decides which Garmin MCP tools to call based on the question, retries on failure, and branches on partial results
- **Long-term memory** — mem0 automatically extracts and stores personal context (injuries, goals, subjective feel) across conversations, retrieved semantically at query time
- **Context assembly** — agent combines live Garmin data + mem0 memories into a focused context window, avoiding token waste
- **Evaluation pipeline** — evals test agent behavior on known coaching scenarios, not just LLM output quality
- **Observability** — every agent decision, tool call, and token traced in LangSmith

---

## How It Works

```
You ask a question
        ↓
FastAPI receives your prompt
        ↓
LangGraph agent decides what it needs:
  ├── Garmin MCP   →  fetches your real workout data from Garmin Connect
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
| **Garmin MCP** | [etweisberg/garmin-connect-mcp](https://github.com/etweisberg/garmin-connect-mcp) | Garmin Connect tools via MCP |
| **Custom MCP tools** | Python MCP SDK | Extended training analysis tools |
| **Memory** | [mem0](https://github.com/mem0ai/mem0) | Long-term personal memory across conversations |
| **Backend** | [FastAPI](https://fastapi.tiangolo.com) | REST API layer |
| **UI** | [Streamlit](https://streamlit.io) | Chat interface |
| **Observability** | [LangSmith](https://smith.langchain.com) | Agent trace monitoring |

---

## Features

- **Natural language queries** — ask anything about your training in plain English
- **Live Garmin data** — no manual exports, pulls directly from Garmin Connect
- **Persistent personal memory** — mem0 automatically remembers your injuries, goals, and how you felt after runs — across every conversation, zero manual setup
- **Stateful agent** — LangGraph decides which tools to call, retries on failure, branches on partial results
- **Evaluation suite** — tests agent correctness on known training scenarios
- **Full observability** — every agent decision traceable in LangSmith

### Custom MCP Tools

On top of the tools from [etweisberg/garmin-connect-mcp](https://github.com/etweisberg/garmin-connect-mcp), this project adds:

| Tool | What It Does |
|---|---|
| `get_training_trend(weeks=4)` | Summarizes load trend over N weeks |
| `get_personal_records()` | Best performances by distance |
| `compare_weeks()` | Side-by-side current vs last week |

---

## Example Questions You Can Ask

- *"Am I overtraining this week?"*
- *"What's my optimal race pace based on recent runs?"*
- *"Build me a 10K training plan based on my current fitness"*
- *"Which days of the week do I perform best?"*
- *"My heart rate has been higher than usual — what does that mean?"*
- *"How does this week compare to last week?"*

The more you chat, the more personalized the advice — mem0 builds your profile automatically from every conversation.

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
├── memory/
│   ├── client.py         # mem0 setup and configuration
│   └── patterns.py       # Fitness-specific memory extraction patterns
├── ui/
│   └── app.py            # Streamlit chat interface
├── evals/
│   ├── test_overtraining.py
│   ├── test_race_pace.py
│   ├── test_weekly_summary.py
│   └── test_memory_retrieval.py  # verifies mem0 recalls injury/goal context
├── .env.example
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

```env
ANTHROPIC_API_KEY=your_key_here
LANGSMITH_API_KEY=your_key_here   # optional but recommended
MEM0_API_KEY=your_key_here        # get from app.mem0.ai, or leave blank for local
```

### 4. Authenticate with Garmin Connect

```bash
npx @etweisberg/garmin-connect-mcp
```

### 5. Run the app

```bash
streamlit run ui/app.py
```

Open [http://localhost:8501](http://localhost:8501) and start asking questions about your training.

> **No Docker required.** mem0 runs locally out of the box, or connects to their hosted platform via API key.

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
        at 8km and keep it easy — your half marathon is
        6 months out, no need to risk it now."
```

The agent gets smarter the more you use it — without you doing anything extra.

---

## Running Evals

```bash
uv run pytest evals/ -v
```

Evals test whether the agent gives correct advice on known scenarios. This includes:

- **Data evals** — correctly identifying overtraining from Garmin metrics
- **Memory evals** — verifying mem0 retrieves injury and goal context when relevant
- **Behavior evals** — ensuring the agent doesn't give risky advice when load is high

Testing **agent behavior** — not just LLM output — is what makes this production-grade.

---

## Architecture Decisions

**Why LangGraph over LangChain?**
The agent needs to branch based on what data it finds. If Garmin returns no data for a date range, it should retry with different parameters rather than silently fail. LangGraph's stateful graph model handles this cleanly — LangChain's linear chains don't.

**Why mem0 over a custom RAG pipeline?**
The first version of this project used Qdrant with a manual ingestion script. The problem: users had to explicitly add notes via CLI — most never did, so the memory layer stayed empty and useless.

mem0 solves this by automatically extracting memories from the conversation itself. When a user mentions their knee hurts, mem0 stores it without any extra step from the user. This changes memory from an opt-in feature into something that just works — which matters enormously for real adoption.

The tradeoff is less control over chunking and embedding strategy. For a personal coaching use case where user friction is the biggest risk, mem0 wins.

**Why MCP for Garmin integration?**
MCP (Model Context Protocol) gives the agent a standardized way to discover and call tools at runtime. This makes it trivial to extend with new Garmin endpoints or swap in a different data source without touching the agent logic.

---

## Roadmap

- [ ] Web app with per-user Garmin auth (replacing local session)
- [ ] Automatic post-run analysis triggered by new activity sync
- [ ] Weekly training summary pushed to email
- [ ] Training plan generation with week-by-week structure
- [ ] Contribute Garmin + mem0 cookbook to mem0 open source repo

---

## Acknowledgements

Built on top of [garmin-connect-mcp](https://github.com/etweisberg/garmin-connect-mcp) by [@etweisberg](https://github.com/etweisberg) — an open source MCP server for the Garmin Connect API. Extended with custom training analysis tools for this project.

Memory layer powered by [mem0](https://github.com/mem0ai/mem0) — open source universal memory for AI agents.

---

## License

MIT
