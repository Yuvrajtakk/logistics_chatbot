"""
tests/test_answer_synth.py
--------------------------
Phase 7: verifies that synthesize_answer() correctly formats the result dicts
from orchestrator into plain English.

Most of these tests use hardcoded result dicts to test the formatting logic
directly. Tests that touch the 'reviews' or 'both' routes will trigger a real
LLM call for summarization.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.answer_synth import synthesize_answer
from langchain_core.documents import Document

def test_sql_route_ok_zero_rows():
    result = {
        "route": "sql",
        "sql": "SELECT * FROM nothing",
        "columns": ["id"],
        "rows": []
    }
    ans = synthesize_answer("How many?", result)
    assert "No matching records" in ans


def test_sql_route_ok_single_row():
    result = {
        "route": "sql",
        "columns": ["customer_state", "count"],
        "rows": [("SP", 41746)]
    }
    ans = synthesize_answer("Which state has the most?", result)
    assert "customer_state: SP" in ans
    assert "count: 41746" in ans
    assert "The result is" in ans


def test_sql_route_ok_multiple_rows():
    result = {
        "route": "sql",
        "columns": ["state", "avg_delivery"],
        "rows": [("SP", 8.2), ("RJ", 12.1), ("MG", 10.5)]
    }
    ans = synthesize_answer("Average delivery by state?", result)
    assert "Here are the results:" in ans
    assert "- state: SP, avg_delivery: 8.2" in ans
    assert "..." not in ans


def test_sql_route_refused():
    result = {
        "route": "sql",
        "refused": True,
        "reason": "REFUSE: I cannot answer questions about employees."
    }
    ans = synthesize_answer("Who works there?", result)
    assert "I cannot answer questions about employees." in ans
    assert "REFUSE" not in ans


def test_sql_route_flagged_with_suggestion():
    result = {
        "route": "sql",
        "flagged": True,
        "problems": [("order_status", "cancelled")],
        "suggestions": {("order_status", "cancelled"): "canceled"}
    }
    ans = synthesize_answer("Show cancelled orders", result)
    assert "'cancelled' isn't a recognized order_status" in ans
    assert "did you mean 'canceled'?" in ans


def test_sql_route_flagged_no_suggestion_small_set():
    result = {
        "route": "sql",
        "flagged": True,
        "problems": [("payment_type", "bitcoin")],
        "suggestions": {}
    }
    ans = synthesize_answer("Orders paid with bitcoin", result)
    # payment_type has 5 values, so it should list them
    assert "'bitcoin' isn't a recognized payment_type" in ans
    assert "Valid values are: " in ans
    assert "credit_card" in ans


def test_sql_route_flagged_no_suggestion_large_set():
    result = {
        "route": "sql",
        "flagged": True,
        "problems": [("product_category_name", "spaceships")],
        "suggestions": {}
    }
    ans = synthesize_answer("Orders of spaceships", result)
    # product_category_name has ~73 values, shouldn't list them
    assert "'spaceships' isn't a recognized product_category_name" in ans
    assert "Valid values are" not in ans


def test_sql_route_error():
    result = {
        "route": "sql",
        "error": "ExecutionError",
        "detail": "no such column: xyz"
    }
    ans = synthesize_answer("Show xyz", result)
    assert "technical issue" in ans
    assert "xyz" not in ans  # Should not leak internal detail


def test_reviews_route_ok():
    # Needs real LLM call
    docs = [
        Document(page_content="O produto chegou quebrado e atrasado. Pessimo!"),
        Document(page_content="Comprei para dar de presente e a caixa veio amassada."),
    ]
    result = {
        "route": "reviews",
        "documents": docs
    }
    ans = synthesize_answer("What do customers complain about?", result)
    # The LLM should summarize this in English and include a Portuguese quote in parens
    assert len(ans) > 20
    assert "error" not in ans.lower()
    # It's an LLM call so we can't assert exact words, just that it returns a valid string


def test_reviews_route_error():
    result = {
        "route": "reviews",
        "error": "Timeout",
        "detail": "..."
    }
    ans = synthesize_answer("Reviews?", result)
    assert "couldn't search customer reviews" in ans
    assert "Timeout" not in ans


def test_both_route_partial_sql_error():
    docs = [Document(page_content="Muito bom, recomendo!")]
    result = {
        "route": "both",
        "sql_error": "Syntax error",
        "documents": docs
    }
    ans = synthesize_answer("How many orders and what did they say?", result)
    assert "couldn't query the database" in ans
    assert "Syntax error" not in ans
    assert len(ans) > 50  # Should include the reviews summary too


def test_both_route_total_failure():
    result = {
        "route": "both",
        "sql_error": "Timeout",
        "reviews_error": "Timeout"
    }
    ans = synthesize_answer("Fail me", result)
    assert "couldn't answer this question right now" in ans
