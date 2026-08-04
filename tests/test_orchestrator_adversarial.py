"""
tests/test_orchestrator_adversarial.py
---------------------------------------
Adversarial tests for orchestrator.py -- trying to break it, not
confirm it works. Same standing rule applied to every module.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import classify_question, orchestrate


def test_empty_question_classify_does_not_crash():
    """
    An empty string sent to classify_question() should not raise --
    it will either fall back to 'sql' (the default) or get an unexpected
    LLM response that our fallback catches. Either way: no crash.
    """
    route = classify_question("")
    assert route in ("sql", "reviews", "both")


def test_empty_question_orchestrate_does_not_crash():
    """
    An empty string sent to orchestrate() must return a result dict,
    not raise an exception.
    """
    result = orchestrate("")
    assert isinstance(result, dict)
    assert "route" in result


def test_very_long_question_does_not_crash():
    """
    A question far longer than any model context window is a genuine
    edge case (copy-paste accident). Should not crash.
    """
    long_q = "How many orders? " * 300
    result = orchestrate(long_q)
    assert isinstance(result, dict)
    assert "route" in result


def test_sql_injection_in_question_does_not_crash():
    """
    A question that looks like SQL injection (e.g. attempting to
    DROP a table) should be routed and processed like any other
    question -- the validator.py layer catches bad SQL, and the
    classify step just sees a string.
    """
    injection_q = "'; DROP TABLE olist_orders_dataset; SELECT * FROM olist_orders_dataset --"
    result = orchestrate(injection_q)
    assert isinstance(result, dict)
    assert "route" in result


def test_classify_never_returns_unexpected_label():
    """
    10 diverse questions -- every single classify_question() call must
    return one of the three valid labels, never garbage.
    """
    questions = [
        "What is the average delivery time?",
        "Do customers complain about sellers?",
        "Which states buy the most electronics?",
        "Are reviews positive for fast deliveries?",
        "How much revenue did the top 10 sellers generate?",
        "What language do reviews use most?",
        "Show me broken or damaged product reviews",
        "Count orders per month in 2017",
        "xyzzy 12345 ??? blorb",         # nonsense
        "SELECT * FROM orders",           # SQL-looking input
    ]
    for q in questions:
        route = classify_question(q)
        assert route in ("sql", "reviews", "both"), (
            f"classify_question() returned invalid label '{route}' for: '{q}'"
        )


def test_orchestrate_error_result_is_still_a_valid_dict():
    """
    When the SQL pipeline fails (e.g. LLM generates genuinely broken SQL
    for a trick question), orchestrate() must still return a dict, and
    that dict must still have a 'route' key.

    We use a question deliberately designed to be hard to answer with
    valid SQL -- not to assert the SQL fails, but to confirm the
    error-handling branch returns a properly shaped dict if it does.
    """
    tricky_q = "What is the average review score for orders that haven't happened yet?"
    result = orchestrate(tricky_q)
    assert isinstance(result, dict)
    assert "route" in result
    # If there was an error, the error key must carry a non-empty message
    if "error" in result:
        assert result["error"]  # non-empty
