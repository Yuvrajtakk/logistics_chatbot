import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from validator import validate_sql, ValidationError


def test_valid_select_passes():
    result = validate_sql("SELECT order_id FROM olist_orders_dataset")
    assert "LIMIT 1000" in result


def test_delete_blocked():
    with pytest.raises(ValidationError):
        validate_sql("DELETE FROM olist_orders_dataset WHERE order_id = '123'")


def test_drop_blocked():
    with pytest.raises(ValidationError):
        validate_sql("DROP TABLE olist_orders_dataset")


def test_disallowed_table_blocked():
    with pytest.raises(ValidationError):
        validate_sql("SELECT * FROM secret_table")


def test_valid_join_passes():
    sql = """
        SELECT o.order_id, i.price
        FROM olist_orders_dataset o
        JOIN olist_order_items_dataset i ON o.order_id = i.order_id
    """
    result = validate_sql(sql)
    assert "olist_orders_dataset" in result
    assert "olist_order_items_dataset" in result


def test_cte_join_passes():
    sql = """
        WITH recent_orders AS (
            SELECT order_id FROM olist_orders_dataset
        )
        SELECT r.order_id, i.price
        FROM recent_orders r
        JOIN olist_order_items_dataset i ON r.order_id = i.order_id
    """
    result = validate_sql(sql)
    assert "LIMIT 1000" in result


def test_multi_statement_injection_blocked():
    with pytest.raises(Exception):
        validate_sql("SELECT * FROM olist_orders_dataset; DROP TABLE olist_orders_dataset;")

def test_subquery_to_banned_table_blocked():
    sql = """
        SELECT order_id
        FROM olist_orders_dataset
        WHERE order_id IN (SELECT order_id FROM secret_table)
    """
    with pytest.raises(ValidationError):
        validate_sql(sql)

