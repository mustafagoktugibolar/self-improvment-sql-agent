import logging
from contextlib import asynccontextmanager

from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import create_graph
from app.config import CHECKPOINT_DB_PATH, CORS_ORIGINS, SHOULD_RUN_INIT
from app.db import init_db

AGUI_PATH = "/agent"
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(should_init=SHOULD_RUN_INIT)
    # Async saver: the AG-UI adapter streams the graph asynchronously.
    async with AsyncSqliteSaver.from_conn_string(str(CHECKPOINT_DB_PATH)) as checkpointer:
        app.state.graph = create_graph(checkpointer)
        agent = LangGraphAgent(
            name="sql_agent",
            description="Answers questions about the SQLite database with SQL tools.",
            graph=app.state.graph,
            # Use the AG-UI standard interrupt flow (RUN_FINISHED outcome + resume[])
            # instead of the legacy on_interrupt custom event. Needed for ask_user.
            emit_interrupt_outcome=True,
        )
        add_langgraph_fastapi_endpoint(app, agent, AGUI_PATH)

        yield


app = FastAPI(title="SQL Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_error(request: Request, _exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path, exc_info=_exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}
