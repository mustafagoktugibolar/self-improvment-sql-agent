"""Offline checks of the SQL tools against agent.db (read-only, no OpenAI calls)."""
import json

from app.agent.tools import sql_db_list_tables, sql_db_query, sql_db_schema


def test_list_tables():
    tables = sql_db_list_tables.invoke({}).split(", ")
    assert "customers" in tables and "orders" in tables


def test_schema():
    out = json.loads(sql_db_schema.invoke({"table_names": "categories,nope"}))
    assert "create_sql" in out[0]
    assert out[1]["error"] == "Table not found"


def test_query_select():
    out = json.loads(sql_db_query.invoke({"query": "SELECT COUNT(*) AS n FROM customers"}))
    assert out[0]["n"] > 0


def test_query_is_read_only():
    out = sql_db_query.invoke({"query": "DELETE FROM customers"})
    assert out.startswith("Error:")
