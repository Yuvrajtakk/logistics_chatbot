"""
categorical_check.py
---------------------
Phase 3 safety layer: checks that literal values compared against known
categorical columns actually exist in the real data.
"""

import difflib
import os
import sqlite3
import sqlglot
from sqlglot import exp

_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

CATEGORICAL_COLUMNS = {
    "order_status": "olist_orders_dataset",
    "payment_type": "olist_order_payments_dataset",
    "customer_state": "olist_customers_dataset",
    "seller_state": "olist_sellers_dataset",
    "product_category_name": "olist_products_dataset",
}

def load_real_values(db_path=None):
    """
    Connects to olist.db (read-only) and retrieves the real distinct values
    for tracked categorical columns.

    Args:
        db_path (str, optional): Path to the SQLite database. Defaults to _DEFAULT_DB_PATH.

    Returns:
        dict: A mapping of column names to sets of distinct valid string values.
    """
    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
    cursor = conn.cursor()

    real_values = {}
    for column, table in CATEGORICAL_COLUMNS.items():
        query = f"SELECT DISTINCT {column} FROM {table}"
        cursor.execute(query)
        values = {row[0] for row in cursor.fetchall() if row[0] is not None}
        real_values[column] = values

    conn.close()
    return real_values

def suggest_similar_value(bad_value: str, real_set: set):
    """
    Suggests the single closest real match for an invalid categorical value.
    This suggestion is returned to the user, not auto-corrected.

    Args:
        bad_value (str): The invalid value.
        real_set (set): The set of valid values.

    Returns:
        str or None: The closest match, or None if no match is found.
    """
    matches = difflib.get_close_matches(bad_value, real_set, n=1, cutoff=0.6)
    return matches[0] if matches else None

def extract_comparisons(tree):
    """
    Extracts (column_name, value) pairs from EQ and IN comparisons
    within a parsed sqlglot AST.

    Args:
        tree (exp.Expression): The root of the sqlglot AST.

    Returns:
        list of tuple: List of (column_name, literal_value) pairs.
    """
    pairs = []

    for eq_node in tree.find_all(exp.EQ):
        left = eq_node.this
        right = eq_node.expression

        if isinstance(left, exp.Column) and isinstance(right, exp.Literal) and right.is_string:
            pairs.append((left.this.this, right.this))
        elif isinstance(right, exp.Column) and isinstance(left, exp.Literal) and left.is_string:
            pairs.append((right.this.this, left.this))

    for in_node in tree.find_all(exp.In):
        left = in_node.this
        if isinstance(left, exp.Column):
            column_name = left.this.this
            for item in in_node.expressions:
                if isinstance(item, exp.Literal) and item.is_string:
                    pairs.append((column_name, item.this))

    return pairs

def check_categoricals(sql_text, real_values):
    """
    Checks if all literal values used against categorical columns in a SQL
    query are valid. Also provides fuzzy suggestions for invalid values.

    Args:
        sql_text (str): The SQL query string.
        real_values (dict): Ground-truth valid values mapping.

    Returns:
        dict: Check results containing 'ok' (bool), 'problems' (list), and 'suggestions' (dict).
    """
    tree = sqlglot.parse_one(sql_text)
    pairs = extract_comparisons(tree)

    problems = []
    suggestions = {}

    for column_name, value in pairs:
        if column_name not in CATEGORICAL_COLUMNS:
            continue

        real_set = real_values.get(column_name, set())
        if value not in real_set:
            problems.append((column_name, value))
            suggestions[(column_name, value)] = suggest_similar_value(value, real_set)

    return {
        "ok": len(problems) == 0,
        "problems": problems,
        "suggestions": suggestions,
    }