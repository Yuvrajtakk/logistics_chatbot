"""
tests/test_categorical_check_adversarial.py
----------------------------------------------
Adversarial tests -- trying to break the new suggest_similar_value()
function, not confirm it works.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.categorical_check import suggest_similar_value


def test_empty_real_set_does_not_crash():
    """
    If real_set is empty (e.g. a column with zero real values recorded,
    or a bug upstream passing the wrong dict), does difflib handle an
    empty set to search against gracefully, or does it throw?
    HONEST PREDICTION: uncertain -- difflib.get_close_matches() searching
    against an empty possibilities list is not something I've verified
    by hand before writing this.
    """
    result = suggest_similar_value("cancelled", set())
    assert result is None


def test_empty_bad_value_does_not_crash():
    """
    An empty string as the 'bad value' itself -- e.g. from a malformed
    query like order_status = ''. Should not crash, and definitely
    should not return a nonsense suggestion just because empty strings
    are technically 'close' to short real values.
    """
    real_values = {"delivered", "shipped", "canceled"}
    result = suggest_similar_value("", real_values)
    # Either None, or -- if difflib does something surprising -- at
    # least confirm it's a real string from the set, not garbage.
    assert result is None or result in real_values


def test_bad_value_identical_to_a_real_value_is_impossible_input(): 
    """
    Sanity/edge case: if the 'bad value' passed in is ACTUALLY a real
    value (meaning check_categoricals() should never have called this
    in the first place, since it only calls this when value NOT in
    real_set) -- this function alone should still behave sanely and
    not error out, even on input that violates its own normal calling
    contract.
    """
    real_values = {"delivered", "shipped", "canceled"}
    result = suggest_similar_value("delivered", real_values)
    assert result == "delivered"  # matches itself perfectly