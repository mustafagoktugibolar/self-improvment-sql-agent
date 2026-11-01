"""Offline checks of the SQL tools against agent.db (read-only, no OpenAI calls)."""
import json
import os

from app import catalog
from app.agent.tools import (
    business_definitions,
    sql_db_list_tables,
    sql_db_query,
    sql_db_schema,
)


def test_list_tables():
    lines = sql_db_list_tables.invoke({}).splitlines()
    assert any(line.startswith("customers: ") for line in lines)
    assert any(line.startswith("orders: ") for line in lines)


def test_schema():
    out = json.loads(sql_db_schema.invoke({"table_names": "orders,nope"}))
    assert "create_sql" in out[0]
    assert out[0]["description"]
    assert "cancelled" in out[0]["column_notes"]["status"]["values"]
    assert out[1]["error"] == "Table not found"


def test_catalog_reloads_when_file_changes(tmp_path, monkeypatch):
    path = tmp_path / "catalog.json"
    monkeypatch.setattr(catalog, "CATALOG_PATH", path)
    monkeypatch.setattr(catalog, "_cache", {"mtime": None, "catalog": None})

    path.write_text('{"tables": {}, "terms": [{"name": "v1"}]}', encoding="utf-8")
    assert catalog.term_names() == ["v1"]

    # Set mtimes explicitly: back-to-back writes can share a timestamp on some filesystems.
    path.write_text('{"tables": {}, "terms": [{"name": "v2"}]}', encoding="utf-8")
    os.utime(path, ns=(1, 1_000_000_000))
    assert catalog.term_names() == ["v2"]

    path.write_text('{"tables": {', encoding="utf-8")  # half-saved edit
    os.utime(path, ns=(1, 2_000_000_000))
    assert catalog.term_names() == ["v2"]


def test_business_definitions(monkeypatch):
    catalog = {"tables": {}, "terms": [
        {"name": "revenue", "synonyms": ["Ciro"], "definition": "sum of paid payments"},
    ]}
    monkeypatch.setattr("app.catalog.load_catalog", lambda: catalog)

    assert json.loads(business_definitions.invoke({"terms": "ciro"}))[0]["name"] == "revenue"
    assert business_definitions.invoke({"terms": "profit"}) == (
        "No definition found. Defined terms: revenue"
    )

    monkeypatch.setattr("app.catalog.load_catalog", lambda: {"tables": {}, "terms": []})
    assert business_definitions.invoke({"terms": "revenue"}).startswith("No business definitions")


def test_query_select():
    out = json.loads(sql_db_query.invoke({"query": "SELECT COUNT(*) AS n FROM customers"}))
    assert out["rows"][0]["n"] > 0


def test_query_is_read_only():
    out = sql_db_query.invoke({"query": "DELETE FROM customers"})
    assert out.startswith("Error:")
