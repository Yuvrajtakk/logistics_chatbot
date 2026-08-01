"""
tests/test_categorical_check.py
--------------------------------
Proves categorical_check.py catches a wrong spelling (the exact bug
this whole file exists to prevent) and correctly passes real values.
"""

import sys
import os

# Add project root to the import path, so "from src.xxx import yyy" works
# no matter which folder pytest is run from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.categorical_check import load_real_values, check_categoricals


def test_real_value_passes():
    """A real, correctly-spelled value should pass with no problems."""
    real_values = load_real_values()
    result = check_categoricals(
        "SELECT * FROM olist_orders_dataset WHERE order_status = 'delivered'",
        real_values,
    )
    assert result["ok"] is True
    assert result["problems"] == []


def test_wrong_spelling_is_flagged():
    """
    The exact bug from PROJECT.md: 'cancelled' (two L's) should be
    flagged, because the real data only has 'canceled' (one L).
    """
    real_values = load_real_values()
    result = check_categoricals(
        "SELECT * FROM olist_orders_dataset WHERE order_status = 'cancelled'",
        real_values,
    )
    assert result["ok"] is False
    assert ("order_status", "cancelled") in result["problems"]


def test_in_clause_catches_bad_value_among_good_ones():
    """
    An IN clause with one good value and one bad value should still
    be flagged -- the bad one must not hide behind the good one.
    """
    real_values = load_real_values()
    result = check_categoricals(
        "SELECT * FROM olist_orders_dataset WHERE order_status IN ('delivered', 'cancelled')",
        real_values,
    )
    assert result["ok"] is False
    assert ("order_status", "cancelled") in result["problems"]


def test_non_categorical_column_is_ignored():
    """
    A column not in our tracked list (like customer_id) should never
    be flagged -- it has no fixed real-world value list to check.
    """
    real_values = load_real_values()
    result = check_categoricals(
        "SELECT * FROM olist_orders_dataset WHERE customer_id = 'anything_at_all'",
        real_values,
    )
    assert result["ok"] is True