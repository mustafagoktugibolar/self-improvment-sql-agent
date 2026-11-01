"""Safe execution of model-written SQL: read-only, time-limited and size-aware.

Small results are returned in full. Large results are never handed to the model
row by row (that would be both too big and a biased slice). Instead it gets the
exact row count, a per-column profile computed by the database over *all* rows,
the first rows in query order and a few random rows, and is told to drill down
with narrower queries.

This module knows nothing about LangGraph, so it can be reused outside the agent.
"""
import json
import sqlite3
import time

from app.config import MAX_RESULT_CHARS, MAX_RESULT_ROWS, QUERY_TIMEOUT_SECONDS
from app.db import get_readonly_con

MAX_CELL_CHARS = 200
SAMPLE_ROWS = 5
MAX_TOP_VALUES = 3
# Columns with at most this many distinct values also get their most common values.
CATEGORICAL_MAX_DISTINCT = 20
# How many SQLite VM steps run between timeout checks.
PROGRESS_STEPS = 10_000


class QueryError(Exception):
    """A query problem the model can act on. The message is shown to the model."""


def run_query(query: str) -> dict:
    query = _strip_trailing_semicolons(query)
    con = get_readonly_con()
    deadline = time.monotonic() + QUERY_TIMEOUT_SECONDS

    def stop_if_too_slow():
        # A non-zero return value makes SQLite abort with "interrupted".
        if time.monotonic() > deadline:
            return 1
        return 0

    con.set_progress_handler(stop_if_too_slow, PROGRESS_STEPS)

    try:
        return _execute(con, query)
    except sqlite3.OperationalError as e:
        if _is_timeout(e):
            raise QueryError(
                f"Query exceeded the {QUERY_TIMEOUT_SECONDS:g} s time limit. "
                "Add filters, aggregate, or simplify joins."
            ) from e
        raise QueryError(str(e)) from e
    except sqlite3.Error as e:
        raise QueryError(str(e)) from e
    finally:
        con.close()


def _execute(con: sqlite3.Connection, query: str) -> dict:
    cursor = con.execute(query)
    if cursor.description is None:
        raise QueryError("The statement returned no result set. Only SELECT queries are allowed.")

    columns = _unique_column_names(cursor.description)
    # Fetch one row more than the limit, so we know whether there are more.
    rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
    cursor.close()

    if len(rows) <= MAX_RESULT_ROWS:
        result = {"row_count": len(rows), "columns": columns, "rows": _to_dicts(columns, rows)}
        if len(json.dumps(result, ensure_ascii=False, default=str)) <= MAX_RESULT_CHARS:
            return result

    return _summarize(con, query, columns, rows[:SAMPLE_ROWS])


def _summarize(con: sqlite3.Connection, query: str, columns: list[str], first_rows: list) -> dict:
    summary = {
        "summarized": True,
        "row_count": f"more than {MAX_RESULT_ROWS}",
        "columns": columns,
        "note": "",
        "profile": None,
        "first_rows": _to_dicts(columns, first_rows),
        "random_rows": [],
    }

    try:
        summary["row_count"] = con.execute(f"SELECT COUNT(*) FROM {_wrap(query)}").fetchone()[0]
        summary["profile"] = _profile(con, query, columns)
        random_rows = con.execute(
            f"SELECT * FROM {_wrap(query)} ORDER BY RANDOM() LIMIT {SAMPLE_ROWS}"
        ).fetchall()
        summary["random_rows"] = _to_dicts(columns, random_rows)
    except sqlite3.OperationalError as e:
        # The first rows were already fetched; return what we have instead of failing.
        if not _is_timeout(e):
            raise

    summary["note"] = _summary_note(summary)
    return summary


def _summary_note(summary: dict) -> str:
    note = (
        f"The result has {summary['row_count']} rows, too many to return in full. "
        "This is a summary, not the rows themselves. "
    )
    if summary["profile"] is not None:
        note += "'profile' holds statistics computed over ALL rows. "
    else:
        note += "The full profile could not be computed within the time limit. "
    note += (
        "'first_rows' are the first rows in query order; 'random_rows' are a random sample. "
        "Do not generalize from sample rows: aggregate (GROUP BY, COUNT, SUM, AVG) or filter "
        "with a narrower query to drill down."
    )
    return note


def _profile(con: sqlite3.Connection, query: str, columns: list[str]) -> dict:
    # One pass over the full result computes every column's statistics at once.
    select_parts = []
    for name in columns:
        col = _quote(name)
        select_parts.append(
            f"COUNT({col}), COUNT(DISTINCT {col}), MIN({col}), MAX({col}), "
            f"SUM(typeof({col}) IN ('integer', 'real')), AVG({col})"
        )
    row = con.execute(f"SELECT COUNT(*), {', '.join(select_parts)} FROM {_wrap(query)}").fetchone()

    total = row[0]
    profile = {}
    for i, name in enumerate(columns):
        non_null, distinct, min_value, max_value, numeric_count, avg = row[1 + i * 6 : 7 + i * 6]
        stats = {
            "nulls": total - non_null,
            "distinct": distinct,
            "min": _cell(min_value),
            "max": _cell(max_value),
        }
        is_numeric = non_null > 0 and numeric_count == non_null
        if is_numeric:
            stats["avg"] = round(avg, 4)
        if 0 < distinct <= CATEGORICAL_MAX_DISTINCT:
            stats["top_values"] = _top_values(con, query, name)
        profile[name] = stats
    return profile


def _top_values(con: sqlite3.Connection, query: str, name: str) -> list:
    col = _quote(name)
    rows = con.execute(
        f"SELECT {col}, COUNT(*) FROM {_wrap(query)} "
        f"GROUP BY {col} ORDER BY COUNT(*) DESC LIMIT {MAX_TOP_VALUES}"
    ).fetchall()
    top = []
    for value, count in rows:
        top.append({"value": _cell(value), "count": count})
    return top


def _wrap(query: str) -> str:
    # Newlines keep a trailing "-- comment" in the query from swallowing the ")".
    return f"(\n{query}\n) AS q"


def _strip_trailing_semicolons(query: str) -> str:
    query = query.strip()
    while query.endswith(";"):
        query = query[:-1].rstrip()
    return query


def _unique_column_names(description) -> list[str]:
    # Same scheme SQLite uses in subqueries: id, id:1, id:2 ... so the names also
    # work when the query is wrapped for profiling, and dict rows keep every column.
    names = []
    seen = {}
    for column in description:
        name = column[0]
        if name in seen:
            seen[name] += 1
            name = f"{name}:{seen[name]}"
        else:
            seen[name] = 0
        names.append(name)
    return names


def _to_dicts(columns: list[str], rows: list) -> list[dict]:
    result = []
    for row in rows:
        item = {}
        for name, value in zip(columns, row):
            item[name] = _cell(value)
        result.append(item)
    return result


def _cell(value):
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"
    if isinstance(value, str) and len(value) > MAX_CELL_CHARS:
        return value[:MAX_CELL_CHARS] + "…"
    return value


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _is_timeout(error: sqlite3.OperationalError) -> bool:
    return str(error) == "interrupted"
