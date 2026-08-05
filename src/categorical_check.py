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

# difflib is Python's built-in library for comparing strings and
# finding the closest matches -- no install needed, same spirit as
# sqlite3 already being built-in.
import difflib
import os
import sqlite3
import sqlglot
from sqlglot import exp

# __file__-relative path, same pattern as execute.py and retrieval.py.
# This makes load_real_values() work regardless of what directory the
# process was launched from -- not just when run from the repo root.
_DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

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
def load_real_values(db_path=None):
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
    # Default to the __file__-relative path when no explicit path is given.
    # Using `None` sentinel instead of the value directly in the signature
    # so that the computed default is evaluated at call time, not at import
    # time -- avoids any edge cases with module-level path resolution.
    if db_path is None:
        db_path = _DEFAULT_DB_PATH

    # Open read-only -- this file must NEVER be able to write to the DB.
    # Same read-only URI trick used in execute.py.
    conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
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
# STEP 2b: Suggest what a flagged value MIGHT have meant (never auto-fix).
# ----------------------------------------------------------------------

def suggest_similar_value(bad_value: str, real_set: set):
    """
    Given a wrong value and the set of real valid values for that
    column, returns the single closest real match, or None if nothing
    is close enough to be a useful suggestion.

    This is ONLY a suggestion. Per Rule 9, categorical_check.py never
    auto-corrects -- this function's return value gets shown to the
    user alongside the flag, never substituted into the query itself.

    n=1: only want the single best guess, not a list of options.
    cutoff=0.6: difflib's similarity score runs 0.0 (nothing alike) to
        1.0 (identical). 0.6 is difflib's own suggested default --
        loose enough to catch real typos ('cancelled' vs 'canceled'
        scores well above this), tight enough to not suggest something
        wildly unrelated just because SOME letters happen to overlap.
    """
    matches = difflib.get_close_matches(bad_value, real_set, n=1, cutoff=0.6)

    # get_close_matches returns a list (possibly empty). We only want
    # the single best match, or None if the list came back empty.
    return matches[0] if matches else None

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
    tree = sqlglot.parse_one(sql_text)
    pairs = extract_comparisons(tree)

    problems = []
    suggestions = {}  # NEW: (column, bad_value) -> suggested real value, or None

    for column_name, value in pairs:
        if column_name not in CATEGORICAL_COLUMNS:
            continue

        real_set = real_values.get(column_name, set())

        if value not in real_set:
            problems.append((column_name, value))

            # NEW: try to find the closest real value as a suggestion.
            # Stored separately from `problems` -- problems stays the
            # exact same shape it always was, so nothing that already
            # reads it (run_eval.py, the existing tests) breaks.
            suggestions[(column_name, value)] = suggest_similar_value(value, real_set)

    return {
        "ok": len(problems) == 0,
        "problems": problems,
        "suggestions": suggestions,  # NEW
    }