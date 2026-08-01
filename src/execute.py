# sqlite3 is Python's built-in library for talking to SQLite databases —
# no separate install needed.
import sqlite3

# os.path lets us build a file path that works regardless of which
# folder PowerShell happens to be sitting in when the script runs.
import os

# __file__ is the path to THIS script (execute.py). os.path.dirname()
# strips the filename, leaving just the folder it's in (src/).
# ".." then steps one folder up to the repo root, then into data/olist.db.
# This means execute.py finds the database correctly no matter where
# you run it from.
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

MAX_RETRIES = 2


class ExecutionError(Exception):
    pass


def get_readonly_connection():
    """
    Opens a connection to olist.db in READ-ONLY mode. This is a second,
    independent safety layer underneath validator.py — even if some SQL
    somehow got past validate_sql(), this connection is physically
    incapable of writing to the database.
    """
    # SQLite's URI syntax: "file:" prefix + "?mode=ro" tells SQLite itself
    # to open this file read-only. uri=True tells Python's sqlite3 module
    # to interpret the string as a URI instead of a plain file path.
    # os.path.abspath() converts our relative path into a full path,
    # which SQLite's URI mode requires to work reliably.
    db_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    return conn


def run_query(sql: str):
    """
    Runs already-validated SQL against the read-only database.
    Returns (column_names, rows) on success.
    Raises ExecutionError on failure — caller decides whether to retry.
    """
    conn = get_readonly_connection()
    try:
        # A cursor is the object you actually use to run SQL and fetch
        # results — the connection itself just represents "being linked
        # to the database file."
        cursor = conn.cursor()
        cursor.execute(sql)

        # cursor.description holds metadata about each returned column;
        # [0] of each entry is the column's name.
        column_names = [description[0] for description in cursor.description]

        rows = cursor.fetchall()
        return column_names, rows

    except sqlite3.Error as e:
        # Catch ANY sqlite-specific error (bad column name, bad table,
        # syntax sqlite doesn't like, etc.) and re-raise as our own
        # exception type, carrying the original error message forward —
        # this message is what gets fed back to the LLM during repair.
        raise ExecutionError(str(e))

    finally:
        # Always close the connection, whether it succeeded or failed.
        conn.close()


def run_with_repair(sql: str, regenerate_fn):
    """
    Runs SQL with a bounded repair loop, per the hard rule: plain Python
    while-loop, max 2 retries — not LangGraph, not an autonomous agent.

    sql: the first SQL attempt (already passed validator.py).
    regenerate_fn: a function that takes (failed_sql, error_message) and
        returns a new SQL string to try instead. In real use, this will
        call the LLM. For now (no LLM connected yet), we'll pass in a
        simple stand-in function during testing.
    """
    attempt = 0
    current_sql = sql

    while attempt <= MAX_RETRIES:
        try:
            return run_query(current_sql)

        except ExecutionError as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                # Retries exhausted — give up and let the caller know
                # exactly what the last failure was.
                raise ExecutionError(f"Failed after {MAX_RETRIES} retries. Last error: {e}")

            # Ask regenerate_fn for a new attempt, feeding it the error
            # message so it knows what went wrong last time.
            current_sql = regenerate_fn(current_sql, str(e))