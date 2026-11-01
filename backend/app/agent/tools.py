import json
import sqlite3

from langchain.tools import tool

from app.config import DB_PATH
from app.db import get_db_con


@tool
def sql_db_list_tables() -> str:
    """Return a comma-separated list of database table names."""
    con = get_db_con()

    try:
        tables = [
            row[0]
            for row in con.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
            """)
        ]

        return ", ".join(tables)
    finally:
        con.close()


@tool
def sql_db_query(query: str) -> str:
    """Execute a read-only SQL query and return results as JSON.
    If the query fails, inspect the schema and correct the query.
    """
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)

    try:
        con.execute("PRAGMA query_only = ON")

        cursor = con.execute(query)
        column_names = [col[0] for col in cursor.description]

        rows = cursor.fetchmany(100)

        results = [
            dict(zip(column_names, row))
            for row in rows
        ]

        return json.dumps(results, indent=2, default=str)

    except sqlite3.Error as e:
        return f"Error: {e}"

    finally:
        con.close()


@tool
def sql_db_schema(table_names: str) -> str:
    """Get schemas and sample rows for comma-separated table names."""
    con = get_db_con()

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

            results.append({
                "table": table_name,
                "create_sql": schema[0],
                "sample_rows": sample_rows
            })

        return json.dumps(results, indent=2, default=str)

    finally:
        con.close()


TOOLS = [sql_db_list_tables, sql_db_schema, sql_db_query]
