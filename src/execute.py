import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

MAX_RETRIES = 2

class ExecutionError(Exception):
    pass

def get_readonly_connection():
    """
    Opens a connection to olist.db in READ-ONLY mode.
    """
    db_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    conn = sqlite3.connect(db_uri, uri=True)
    return conn

def run_query(sql: str):
    """
    Runs validated SQL against the read-only database.
    
    Args:
        sql (str): The SQL query string.
        
    Returns:
        tuple: (list of column names, list of result rows).
        
    Raises:
        ExecutionError: If the SQL execution fails.
    """
    conn = get_readonly_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        column_names = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        return column_names, rows
    except sqlite3.Error as e:
        raise ExecutionError(str(e))
    finally:
        conn.close()

def run_with_repair(sql: str, regenerate_fn):
    """
    Runs SQL with a bounded repair loop for execution failures.
    
    Args:
        sql (str): Initial SQL attempt.
        regenerate_fn (callable): Function (failed_sql, error_msg) -> new_sql.
        
    Returns:
        tuple: (list of column names, list of result rows).
        
    Raises:
        ExecutionError: If retries are exhausted.
    """
    attempt = 0
    current_sql = sql

    while attempt <= MAX_RETRIES:
        try:
            return run_query(current_sql)
        except ExecutionError as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise ExecutionError(f"Failed after {MAX_RETRIES} retries. Last error: {e}")
            current_sql = regenerate_fn(current_sql, str(e))