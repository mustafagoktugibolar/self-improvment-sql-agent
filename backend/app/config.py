import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "agent.db"))
# Conversation state (LangGraph checkpoints); separate from the data the agent queries.
CHECKPOINT_DB_PATH = Path(os.getenv("CHECKPOINT_DB_PATH", PROJECT_ROOT / "checkpoints.db"))
INIT_SQL_PATH = PROJECT_ROOT / "seed_agent.sql"
CATALOG_PATH = Path(os.getenv("CATALOG_PATH", PROJECT_ROOT / "schema_catalog.json"))

SHOULD_RUN_INIT = os.getenv("SHOULD_RUN_INIT", "false").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")

# Limits for model-written queries (see app/sql/runner.py).
QUERY_TIMEOUT_SECONDS = float(os.getenv("QUERY_TIMEOUT_SECONDS", "10"))
MAX_RESULT_ROWS = int(os.getenv("MAX_RESULT_ROWS", "100"))
MAX_RESULT_CHARS = int(os.getenv("MAX_RESULT_CHARS", "12000"))
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
