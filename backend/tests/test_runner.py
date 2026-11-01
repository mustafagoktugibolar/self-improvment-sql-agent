"""Offline checks of the SQL runner against agent.db (read-only, no OpenAI calls)."""
import sqlite3

import pytest
from app.sql import runner
from app.sql.runner import QueryError, run_query

LARGE_QUERY = "SELECT order_id, quantity, discount_rate FROM order_items"  # 1508 rows


def test_small_result_is_returned_in_full():
    result = run_query("SELECT id, name FROM categories ORDER BY id")
    assert "summarized" not in result
    assert result["row_count"] == len(result["rows"])
    assert result["rows"][0].keys() == {"id", "name"}


def test_large_result_is_summarized_over_all_rows():
    result = run_query(LARGE_QUERY)
    assert result["summarized"] is True
    assert result["row_count"] == 1508
    assert "rows" not in result

    discount = result["profile"]["discount_rate"]
    assert discount["avg"] == 0.0596
    assert discount["nulls"] == 0
    assert {"value": 0, "count": 604} in discount["top_values"]

    assert len(result["first_rows"]) == runner.SAMPLE_ROWS
    assert len(result["random_rows"]) == runner.SAMPLE_ROWS
    assert "Do not generalize" in result["note"]


def test_duplicate_column_names_are_kept():
    query = "SELECT o.id, c.id, c.name FROM orders o JOIN customers c ON c.id = o.customer_id"
    small = run_query(query + " LIMIT 2")
    assert small["columns"] == ["id", "id:1", "name"]
    assert small["rows"][0].keys() == {"id", "id:1", "name"}

    large = run_query(query)
    assert large["profile"]["id:1"]["distinct"] == 100


def test_trailing_semicolon_and_comment():
    assert run_query(LARGE_QUERY + " ;")["row_count"] == 1508
    assert run_query(LARGE_QUERY + " -- the model's comment")["row_count"] == 1508


def test_profile_timeout_falls_back_to_partial_summary(monkeypatch):
    def slow_profile(*args):
        raise sqlite3.OperationalError("interrupted")

    monkeypatch.setattr(runner, "_profile", slow_profile)
    result = run_query(LARGE_QUERY)
    assert result["summarized"] is True
    assert result["profile"] is None
    assert len(result["first_rows"]) == runner.SAMPLE_ROWS
    assert "could not be computed" in result["note"]


def test_slow_query_times_out(monkeypatch):
    monkeypatch.setattr(runner, "QUERY_TIMEOUT_SECONDS", 0.2)
    endless = "WITH RECURSIVE r(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM r) SELECT COUNT(*) FROM r"
    with pytest.raises(QueryError, match="time limit"):
        run_query(endless)


@pytest.mark.parametrize("query", [
    "DELETE FROM customers",
    "UPDATE customers SET city = 'X'",
    "SELECT 1; DELETE FROM customers",
])
def test_writes_are_rejected(query):
    with pytest.raises(QueryError):
        run_query(query)


def test_statement_without_result_set_is_rejected():
    with pytest.raises(QueryError, match="no result set"):
        run_query("PRAGMA query_only = OFF")
