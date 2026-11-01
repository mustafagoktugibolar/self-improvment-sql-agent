import sqlite3

from app.config import DB_PATH, INIT_SQL_PATH


def get_db_con() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


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
