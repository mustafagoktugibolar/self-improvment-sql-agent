"""Semantic metadata for the database (descriptions, allowed values, business terms).

Loaded from a JSON file so it lives next to the data instead of in the system prompt.
Column entries are passed through as-is, so extra fields (type, unit, ...) just work.
The file is re-read whenever it changes on disk, so edits apply without a restart.
"""
import json
import logging

from app.config import CATALOG_PATH

logger = logging.getLogger(__name__)

_cache = {"mtime": None, "catalog": None}


def load_catalog() -> dict:
    """Return the catalog, re-reading the file only when its modification time changes."""
    if not CATALOG_PATH.exists():
        return {"tables": {}, "terms": []}

    mtime = CATALOG_PATH.stat().st_mtime_ns
    if mtime == _cache["mtime"]:
        return _cache["catalog"]

    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # A half-saved edit should not break the agent: keep the last valid version.
        if _cache["catalog"] is None:
            raise
        logger.warning("Invalid JSON in %s, keeping the previous catalog", CATALOG_PATH)
        return _cache["catalog"]

    _cache["mtime"] = mtime
    _cache["catalog"] = catalog
    return catalog


def table_info(table_name: str) -> dict:
    """Description and column notes for one table ({} if not documented)."""
    return load_catalog()["tables"].get(table_name, {})


def find_terms(terms: list[str]) -> list[dict]:
    """Business terms whose name or synonyms match any of `terms` (case-insensitive)."""
    wanted = {t.strip().lower() for t in terms if t.strip()}
    return [
        term
        for term in load_catalog()["terms"]
        if wanted & {n.lower() for n in [term["name"], *term.get("synonyms", [])]}
    ]


def term_names() -> list[str]:
    return [term["name"] for term in load_catalog()["terms"]]
