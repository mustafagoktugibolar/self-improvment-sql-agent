# self-improvment-sql-agent

LangGraph SQL agent (SQLite) + FastAPI backend + Next.js/CopilotKit frontend.
The AG-UI integration between them is **intentionally left for you to implement**.

## Layout

```
backend/app/{main.py,config.py,db.py,agent/{graph.py,tools.py}}   FastAPI + agent
backend/tests/test_tools.py                                       offline SQL tool tests
frontend/                                                         Next.js (TypeScript)
agent.db, seed_agent.sql                                          database + seed
```

## Run

```bash
cp .env.example .env            # set OPENAI_API_KEY
uv sync
uv run uvicorn app.main:app --app-dir backend --reload --port 8000   # http://localhost:8000/health
uv run pytest                                                         # no OpenAI calls

cd frontend && cp .env.example .env.local && npm install && npm run dev   # http://localhost:3000
```

## AG-UI wiring

- `backend/app/main.py`: `LangGraphAgent(name="sql_agent", graph=...)` registered with `add_langgraph_fastapi_endpoint(app, agent, "/agent")`.
- `frontend/app/api/copilotkit/route.ts`: `CopilotRuntime` with an `HttpAgent` -> `${BACKEND_URL}/agent`.
- `frontend/app/providers.tsx`: `<CopilotKit runtimeUrl="/api/copilotkit" agent="sql_agent">`.
- `frontend/app/page.tsx`: `<CopilotChat agentId="sql_agent" />`.
