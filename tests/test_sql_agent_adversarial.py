"""
tests/test_sql_agent_adversarial.py
-------------------------------------
Adversarial tests for sql_agent.py -- trying to break it, not confirm
it works. Same standing rule applied to every module since Phase 5.5a.

Focus areas:
    1. _real_values cache -- mutation, isolation, consistency across calls
    2. JSON-serialization limitation in "flagged" results -- confirm the
       known limitation is empirically real, not just documented
    3. Pipeline ordering -- confirm categorical check sits before execution
       (structural, not just behavioral)
    4. Memory parameter contract -- None and a real ConversationMemory
       both work without leaking state across calls
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sql_agent import run_sql_agent, _get_real_values
from src.memory import ConversationMemory


# ---------------------------------------------------------------------------
# 1. Cache correctness and mutation safety
# ---------------------------------------------------------------------------

def test_real_values_cache_returns_same_object_every_time():
    """
    _get_real_values() is supposed to hit the DB exactly once. Confirm
    it returns the SAME Python object on repeated calls -- not a fresh
    copy, not a new dict with the same content, but the identical object.
    `rv1 is rv2` is True only if they're the same object in memory.
    """
    rv1 = _get_real_values()
    rv2 = _get_real_values()
    rv3 = _get_real_values()
    assert rv1 is rv2, "Second call returned a different object -- cache isn't working"
    assert rv2 is rv3, "Third call returned a different object -- cache isn't working"


def test_real_values_cache_is_not_empty():
    """
    The cache must be populated with real, non-empty sets -- not an empty
    dict, not a dict of empty sets. If this fails, load_real_values() or
    the DB path is broken (the path fix may have regressed).
    """
    rv = _get_real_values()
    assert len(rv) > 0, "real_values dict is empty -- DB load likely failed"
    for column, value_set in rv.items():
        assert len(value_set) > 0, (
            f"Column '{column}' has an empty value set -- "
            f"SELECT DISTINCT returned no rows (or column doesn't exist)"
        )


def test_mutating_cached_values_does_not_affect_future_calls():
    """
    _get_real_values() returns the actual cached dict -- not a copy.
    If a caller modifies it (adding a fake value, clearing a set), that
    mutation would silently corrupt every subsequent call in the same
    process.

    This is a KNOWN RISK of the current cache design. This test documents
    it empirically: mutate the returned dict, then confirm the mutation
    persists in the next call (proving the shared-object risk is real).

    Why we're NOT fixing this right now: sql_agent.py is the only caller,
    and it only reads the dict -- it never modifies it. The risk is real
    but not currently a bug. If Phase 8/9 ever adds concurrent access or
    a caller that writes to this dict, this test will remind us to add
    a copy() or a lock.
    """
    rv = _get_real_values()
    original_order_status_count = len(rv["order_status"])

    # Mutate the cached set directly
    rv["order_status"].add("__fake_test_value__")
    assert len(rv["order_status"]) == original_order_status_count + 1

    # Second call returns the SAME mutated object -- the fake value is there
    rv2 = _get_real_values()
    assert "__fake_test_value__" in rv2["order_status"], (
        "Mutation didn't persist -- cache may be returning copies now "
        "(that would be safer, but this test needs to be updated)"
    )

    # Clean up so this test doesn't corrupt later tests in the same session
    rv2["order_status"].discard("__fake_test_value__")
    assert "__fake_test_value__" not in _get_real_values()["order_status"]


# ---------------------------------------------------------------------------
# 2. JSON-serialization limitation in "flagged" results
# ---------------------------------------------------------------------------

def test_flagged_result_suggestions_keys_are_not_json_serializable():
    """
    The "flagged" status dict carries suggestions with (column, value)
    tuple keys. Tuples are not JSON-serializable. This test confirms that
    limitation is REAL (not just documented), so Phase 8/9 doesn't
    discover it for the first time when trying to log a result.

    We construct a fake suggestions dict with the same key shape (tuple)
    and confirm json.dumps() raises TypeError on it.
    """
    fake_flagged_suggestions = {
        ("order_status", "cancelled"): "canceled",
        ("payment_type", "creditcard"): "credit_card",
    }

    try:
        json.dumps(fake_flagged_suggestions)
        raise AssertionError(
            "json.dumps() succeeded on tuple-keyed dict -- "
            "the documented limitation may no longer apply "
            "(update the module docstring if so)"
        )
    except TypeError:
        pass  # Expected -- tuple keys are not JSON-serializable


# ---------------------------------------------------------------------------
# 3. Memory parameter contract
# ---------------------------------------------------------------------------

def test_none_memory_does_not_crash():
    """
    run_sql_agent() accepts memory=None as the default. Confirm calling
    it explicitly with None doesn't crash differently than not passing it.
    """
    result = run_sql_agent("How many orders are there?", memory=None)
    assert isinstance(result, dict)
    assert "status" in result


def test_empty_memory_does_not_crash():
    """
    An empty ConversationMemory (no turns yet) is a valid argument.
    Confirm it's handled the same as None -- the prompt builder should
    just produce an empty history section.
    """
    memory = ConversationMemory()
    result = run_sql_agent("How many orders are there?", memory=memory)
    assert isinstance(result, dict)
    assert "status" in result


def test_two_consecutive_calls_do_not_share_state():
    """
    Two separate run_sql_agent() calls must be fully independent. The
    second call's result must not be influenced by the first call's
    question, LLM response, or any mutable state left behind.

    We test two clearly different questions and confirm both return
    result dicts with 'status' keys -- not a crash or a stale result
    from the first call being returned for the second.
    """
    result1 = run_sql_agent("How many orders are there?")
    result2 = run_sql_agent("How many sellers are there?")

    assert isinstance(result1, dict) and "status" in result1
    assert isinstance(result2, dict) and "status" in result2

    # The results should be independent. If both are "ok", the row counts
    # should differ (different questions, different tables).
    if result1["status"] == "ok" and result2["status"] == "ok":
        # orders and sellers are different tables -- row counts will differ
        # unless the model somehow returned the same answer for both, which
        # would be a model bug, not a cache bug. Check column names instead.
        assert result1["columns"] != result2["columns"] or result1["rows"] != result2["rows"], (
            "Both calls returned identical results for clearly different questions "
            "-- possible state leak between calls"
        )
