# Same import-path setup as test_validator.py, so this file can find
# execute.py inside src/.
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import sqlite3
import pytest
from execute import run_query, run_with_repair, ExecutionError, get_readonly_connection


def test_valid_query_returns_real_data():
    # A simple, known-good query should return real columns and rows
    # from the actual olist.db — not mocked data.
    columns, rows = run_query("SELECT order_id FROM olist_orders_dataset LIMIT 3")
    assert columns == ["order_id"]
    assert len(rows) == 3


def test_bad_column_raises_execution_error():
    # A typo'd column name should be caught and re-raised as our own
    # ExecutionError, not leak a raw sqlite3.Error out to the caller.
    with pytest.raises(ExecutionError):
        run_query("SELECT nonexistent_column FROM olist_orders_dataset")


def test_connection_is_actually_read_only():
    # This is the important one: prove the connection can't write, even
    # if it tried. We attempt an INSERT directly through the read-only
    # connection (bypassing validator.py on purpose, since we're testing
    # this specific layer in isolation) and confirm sqlite3 itself
    # refuses it.
    conn = get_readonly_connection()
    cursor = conn.cursor()
    with pytest.raises(sqlite3.OperationalError):
        cursor.execute("INSERT INTO olist_orders_dataset (order_id) VALUES ('fake_id')")
    conn.close()


def test_repair_loop_succeeds_after_one_retry():
    # Simulates: first SQL is broken, regenerate_fn fixes it on attempt 1.
    def fix_it(failed_sql, error_message):
        return "SELECT order_id FROM olist_orders_dataset LIMIT 1"

    columns, rows = run_with_repair(
        "SELECT bad_column FROM olist_orders_dataset",
        fix_it
    )
    assert columns == ["order_id"]


def test_repair_loop_gives_up_after_max_retries():
    # Simulates: regenerate_fn NEVER produces working SQL. Should raise
    # ExecutionError after exactly MAX_RETRIES attempts, not loop forever.
    def never_fix_it(failed_sql, error_message):
        return "SELECT still_bad_column FROM olist_orders_dataset"

    with pytest.raises(ExecutionError):
        run_with_repair("SELECT bad_column FROM olist_orders_dataset", never_fix_it)