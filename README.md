# self-improvment-sql-agent

A reference repo for two questions:

1. **What should a SQL agent look like?** A small, readable LangGraph agent that answers
   natural-language questions over a SQLite database, safely and with its reasoning visible.
2. **How does such an agent improve itself?** The second half of the repo (in progress, see
   [Roadmap](#roadmap-self-improvement)) adds a feedback loop so the agent gets better from
   its own mistakes and from user corrections, instead of someone hand-editing prompts.

Stack: LangGraph agent + FastAPI backend (Python 3.14, `uv`) + Next.js / CopilotKit frontend,
connected over the AG-UI protocol.

## What a good SQL agent looks like

The design rule behind this repo: **the prompt raises the chance of a correct first query;
safety is enforced by code, never by prompt rules.**

| Concern | How it is handled | Where |
|---|---|---|
| Schema discovery | Agent never guesses names: it lists tables, then reads schemas (DDL, column notes, allowed values, sample rows) on demand | `agent/tools.py` |
| Semantics | Table/column meanings and **business terms** (revenue, profit, active customer...) live in a JSON catalog, not in the system prompt. Hot-reloaded on file change | `schema_catalog.json`, `catalog.py` |
| Ambiguity | If a term is undefined and interpretations differ materially, the agent pauses and asks the user (human-in-the-loop via LangGraph `interrupt()`) | `ask_user` tool, `AskUser.tsx` |
| Safe execution | Read-only SQLite connection, query timeout, trailing-`;` handling, errors returned to the model so it can fix the query | `sql/runner.py` |
| Large results | Never dumped into context. The model gets the exact row count, per-column statistics computed over *all* rows, and a few sample rows, then drills down with narrower queries | `sql/runner.py` |
| Prompting | Short prompt describing *how to work* (workflow, SQLite quirks, empty-result checks), not what the data means | `agent/prompts.py` |
| Transparency | Every tool call is rendered in the UI; the agent states assumptions in its answer | `ToolCalls.tsx` |

## Layout

```
backend/app/
  main.py            FastAPI app, AG-UI endpoint (/agent), /health
  config.py          Environment-driven settings
  db.py              SQLite connections (read-only for the agent)
  catalog.py         Loads schema_catalog.json (hot reload)
  agent/graph.py     LangGraph graph (model <-> tools loop, MemorySaver checkpointer)
  agent/tools.py     list_tables, schema, business_definitions, ask_user, query
  agent/prompts.py   System prompt
  sql/runner.py      Safe, size-aware query execution (no LangGraph dependency)
backend/tests/       Offline tests (no OpenAI calls)
frontend/            Next.js + CopilotKit chat UI
schema_catalog.json  Table/column descriptions + business term definitions
seed_agent.sql       Demo e-commerce data (customers, products, orders, payments)
```

## Run

Requirements: Python 3.14, [`uv`](https://docs.astral.sh/uv/), Node.js.

```bash
cp .env.example .env            # set OPENAI_API_KEY
uv sync

# backend  ->  http://localhost:8000/health
uv run uvicorn app.main:app --app-dir backend --reload --port 8000

# tests (offline, no OpenAI calls)
uv run pytest

# frontend  ->  http://localhost:3000
cd frontend && cp .env.example .env.local && npm install && npm run dev
```

Configuration (`.env`):

| Variable | Default | Meaning |
|---|---|---|
| `OPENAI_API_KEY` | - | Required |
| `OPENAI_MODEL` | `gpt-5.5` | Model used by the agent |
| `SHOULD_RUN_INIT` | `false` | `true` re-creates `agent.db` from `seed_agent.sql` (**drops tables**) |
| `DEBUG_MODE` | `false` | Read in `config.py`, not used yet |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed frontend origins |

## AG-UI wiring

- `backend/app/main.py`: `LangGraphAgent(name="sql_agent", graph=...)` registered with
  `add_langgraph_fastapi_endpoint(app, agent, "/agent")`.
- `frontend/app/api/copilotkit/route.ts`: `CopilotRuntime` with an `HttpAgent` -> `${NEXT_PUBLIC_BACKEND_URL}/agent` (default `http://localhost:8000`).
- `frontend/app/providers.tsx`: `<CopilotKit runtimeUrl="/api/copilotkit" agent="sql_agent">`.
- `frontend/app/page.tsx`: `<CopilotChat agentId="sql_agent" />`.

## Roadmap: self-improvement

The agent above is static: when it gets something wrong, a human has to notice and edit the
catalog or prompt. Self-improvement closes that loop. Planned stages:

1. **Capture**: log every run (question, tool calls, SQL, result summary, final answer,
   user answers to `ask_user`, thumbs up/down or corrections).
2. **Evaluate**: a growing eval set of questions with verified SQL/answers, plus an automatic
   judge to score runs (execution success, result match, assumption stated).
3. **Learn**: turn failures and user clarifications into proposed changes - new business
   term definitions, column notes, few-shot examples, prompt rules - written to the catalog
   as *proposals*.
4. **Gate**: a proposal is applied only if it improves the eval set without regressions
   (and optionally after human approval). Everything is versioned, so changes can be rolled back.

The existing design already supports this: semantics live in `schema_catalog.json` (hot
reloaded, so applying a learned change needs no restart), and the agent's behavior is
separated from its knowledge.
