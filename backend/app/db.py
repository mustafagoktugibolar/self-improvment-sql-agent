import sqlite3

from app.config import DB_PATH, INIT_SQL_PATH


def get_db_con() -> sqlite3.Connection:
    """Read-write connection. Only for init_db; agent tools use get_readonly_con."""
    return sqlite3.connect(DB_PATH)


def get_readonly_con() -> sqlite3.Connection:
    """Connection that cannot write: the file is opened read-only and query_only is on."""
    con = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    con.execute("PRAGMA query_only = ON")
    return con


def list_tables() -> list[str]:
    con = get_readonly_con()

    try:
        tables = []
        for row in con.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
        """):
            tables.append(row[0])
        return tables
    finally:
        con.close()


def init_db(should_init: bool) -> None:
    if not should_init:
        print("Skipping init...")
        return

    sql = INIT_SQL_PATH.read_text(encoding="utf-8")

    con = get_db_con()
    try:
        con.executescript(sql)
        print("Database initialized successfully.")
    finally:
        con.close()
