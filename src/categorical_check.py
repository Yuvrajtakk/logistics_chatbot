"""
categorical_check.py
---------------------
Phase 3 safety layer: checks that literal values compared against known
categorical columns actually exist in the real data.

Why this file exists (plain English):
    A SQL query can be perfectly well-formed (passes validator.py) and
    still be silently WRONG if it compares a column to a value that
    doesn't really exist -- e.g. order_status = 'cancelled' when the
    real data only ever has 'canceled' (one L). No error is thrown.
    The query just quietly returns 0 or wrong rows.

    This file's only job: catch that, BEFORE the query runs.
    It never fixes the value automatically -- it only flags it and
    hands the decision back to the user. (Hard Rule 9 in PROJECT.md)
"""

import sqlite3
import sqlglot
from sqlglot import exp

# ----------------------------------------------------------------------
# STEP 1: Which columns actually need this check?
# ----------------------------------------------------------------------
# Only columns with a fixed, real-world list of valid values need this.
# Numeric columns (price, freight_value) or IDs don't have a "real list"
# to check against, so we deliberately leave them out.
#
# Each entry maps: column_name -> which table it lives in (needed to
# query the real distinct values from the database).
CATEGORICAL_COLUMNS = {
    "order_status": "olist_orders_dataset",
    "payment_type": "olist_order_payments_dataset",
    "customer_state": "olist_customers_dataset",
    "seller_state": "olist_sellers_dataset",
    "product_category_name": "olist_products_dataset",
}


# ----------------------------------------------------------------------
# STEP 2: Load the REAL distinct values from the live database.
# ----------------------------------------------------------------------
def load_real_values(db_path="data/olist.db"):
    """
    Connects to olist.db (read-only) and, for each tracked categorical
    column, runs SELECT DISTINCT to get the real ground-truth values.

    Returns a dictionary like:
        {
            "order_status": {"delivered", "shipped", "canceled", ...},
            "payment_type": {"credit_card", "boleto", ...},
            ...
        }

    We use a SET (not a list) because checking "is X in this set" is
    fast and exactly the kind of membership test sets are built for.
    """
    # Open read-only -- this file must NEVER be able to write to the DB.
    # Same read-only URI trick used in execute.py.
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cursor = conn.cursor()

    real_values = {}

    for column, table in CATEGORICAL_COLUMNS.items():
        # NOTE: column/table names here come from our own trusted
        # CATEGORICAL_COLUMNS dict above, never from user input -- so
        # it's safe to put them directly in the f-string. If this ever
        # took user-supplied names, we'd need to guard against SQL
        # injection here.
        query = f"SELECT DISTINCT {column} FROM {table}"
        cursor.execute(query)

        # cursor.fetchall() returns a list of 1-tuples like
        # [('delivered',), ('shipped',), ...] so we pull out row[0]
        # from each, and drop any None (missing/null) values.
        values = {row[0] for row in cursor.fetchall() if row[0] is not None}

        real_values[column] = values

    conn.close()
    return real_values


# ----------------------------------------------------------------------
# STEP 3: Pull out (column, value) pairs from a parsed SQL tree.
# ----------------------------------------------------------------------
def extract_comparisons(tree):
    """
    Walks a parsed sqlglot tree and returns a list of (column_name, value)
    pairs found in EQ (column = 'value') and IN (column IN ('a','b'))
    comparisons. This is exactly what we proved by hand in scratch_test.py.

    Handles BOTH directions for EQ:
        order_status = 'cancelled'   (column on left -- the normal case)
        'cancelled' = order_status   (column on right -- rare, but valid
                                       SQL, and we don't want to silently
                                       miss it)
    """
    pairs = []

    # ---- EQ nodes: column = 'value' ----
    for eq_node in tree.find_all(exp.EQ):
        left = eq_node.this
        right = eq_node.expression

        # Case 1: normal order -> column = 'value'
        if isinstance(left, exp.Column) and isinstance(right, exp.Literal) and right.is_string:
            column_name = left.this.this
            value = right.this
            pairs.append((column_name, value))

        # Case 2: reversed order -> 'value' = column
        elif isinstance(right, exp.Column) and isinstance(left, exp.Literal) and left.is_string:
            column_name = right.this.this
            value = left.this
            pairs.append((column_name, value))

        # If neither side is a plain column/literal pair (e.g. comparing
        # two columns, or a function call), we skip it -- that already
        # passed validator.py's structural checks, so it's not unsafe,
        # just not something this file needs to look at.

    # ---- IN nodes: column IN ('a', 'b', ...) ----
    for in_node in tree.find_all(exp.In):
        left = in_node.this

        if isinstance(left, exp.Column):
            column_name = left.this.this

            # in_node.expressions is the list of literals. But an IN
            # can ALSO hold a subquery, e.g. "col IN (SELECT ...)" --
            # in that case in_node.expressions is EMPTY and the real
            # content lives elsewhere. We only handle the literal-list
            # form here; a subquery has no fixed literal to check
            # against our ground-truth list, so we safely skip it.
            for item in in_node.expressions:
                if isinstance(item, exp.Literal) and item.is_string:
                    pairs.append((column_name, item.this))

    return pairs


# ----------------------------------------------------------------------
# STEP 4: The main check -- combine steps 2 and 3, decide pass/fail.
# ----------------------------------------------------------------------
def check_categoricals(sql_text, real_values):
    """
    Takes a SQL string (already passed validator.py) and the real_values
    dictionary from load_real_values().

    Returns a dictionary:
        {
            "ok": True/False,
            "problems": [ (column, bad_value), ... ]   # empty list if ok
        }

    Design choice: this checks the WHOLE query and collects ALL bad
    values, rather than stopping at the first one -- so if a query has
    two typos, you find out about both at once instead of fixing one,
    re-running, and hitting the second.
    """
    tree = sqlglot.parse_one(sql_text)
    pairs = extract_comparisons(tree)

    problems = []

    for column_name, value in pairs:
        # Only check columns we actually track (order_status, etc).
        # A comparison like "customer_id = 'abc123'" is correctly
        # ignored -- customer_id has no fixed real-world value list.
        if column_name not in CATEGORICAL_COLUMNS:
            continue

        real_set = real_values.get(column_name, set())

        if value not in real_set:
            problems.append((column_name, value))

    return {
        "ok": len(problems) == 0,
        "problems": problems,
    }