import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("DB_PATH", PROJECT_ROOT / "agent.db"))
INIT_SQL_PATH = PROJECT_ROOT / "seed_agent.sql"

SHOULD_RUN_INIT = os.getenv("SHOULD_RUN_INIT", "false").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
