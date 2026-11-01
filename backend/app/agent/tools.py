import json

from langchain.tools import tool
from langgraph.types import interrupt

from app.catalog import find_terms, table_info, term_names
from app.db import get_readonly_con, list_tables
from app.sql.runner import QueryError, run_query


@tool
def sql_db_list_tables() -> str:
    """List the database tables, one per line, with a short description of each."""
    lines = []
    for name in list_tables():
        description = table_info(name).get("description")
        lines.append(f"{name}: {description}" if description else name)
    return "\n".join(lines)


@tool
def sql_db_query(query: str) -> str:
    """Execute a read-only SQL query and return the result as JSON.
    Small results come back in full. Large results come back summarized: exact row
    count, per-column statistics over all rows, and a few sample rows.
    If the query fails, inspect the schema and correct the query.
    """
    try:
        result = run_query(query)
    except QueryError as e:
        return f"Error: {e}"
    return json.dumps(result, ensure_ascii=False, default=str)


@tool
def sql_db_schema(table_names: str) -> str:
    """Get schemas, column descriptions, allowed values and sample rows
    for comma-separated table names."""
    con = get_readonly_con()

    try:
        def fetch_as_dict(query: str) -> list[dict]:
            cursor = con.execute(query)
            column_names = [col[0] for col in cursor.description]

            return [
                dict(zip(column_names, row))
                for row in cursor.fetchall()
            ]

        results = []

        for table_name in table_names.split(","):
            table_name = table_name.strip()

            schema = con.execute(
                """
                SELECT sql
                FROM sqlite_master
                WHERE type = 'table' AND name = ?
                """,
                (table_name,)
            ).fetchone()

            if schema is None:
                results.append({
                    "table": table_name,
                    "error": "Table not found"
                })
                continue

            safe_name = table_name.replace('"', '""')

            sample_rows = fetch_as_dict(
                f'SELECT * FROM "{safe_name}" LIMIT 3'
            )

            info = table_info(table_name)

            results.append({
                "table": table_name,
                "description": info.get("description"),
                "create_sql": schema[0],
                "column_notes": info.get("columns", {}),
                "sample_rows": sample_rows
            })

        return json.dumps(results, indent=2, default=str)

    finally:
        con.close()


@tool
def business_definitions(terms: str) -> str:
    """Look up how business terms (e.g. revenue, profit, active customer) are
    defined for this database. Pass comma-separated terms."""
    matches = find_terms(terms.split(","))
    if matches:
        return json.dumps(matches, indent=2, ensure_ascii=False)

    available = term_names()
    if not available:
        return "No business definitions are available. State the interpretation you use."
    return f"No definition found. Defined terms: {', '.join(available)}"


@tool
def ask_user(question: str, options: list[str]) -> str:
    """Ask the user a clarifying question and wait for the answer.
    Use it only when a term is not defined in business_definitions and the possible
    interpretations would give materially different results. Offer 2-4 short options.
    Call it alone, never together with other tools."""
    # Pauses the graph; the client shows the question and resumes with the answer.
    # On resume the tool runs again from the top and interrupt() returns that answer.
    answer = interrupt({"reason": "ask_user", "message": question, "options": options})

    if isinstance(answer, str) and answer.strip():
        return f"The user answered: {answer}"
    return "The user did not answer. Pick the most reasonable interpretation and state it."


TOOLS = [sql_db_list_tables, sql_db_schema, business_definitions, ask_user, sql_db_query]
