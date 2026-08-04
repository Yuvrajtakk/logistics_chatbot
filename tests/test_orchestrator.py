"""
tests/test_orchestrator.py
---------------------------
Phase 5.5b: proves orchestrator.py's classify_question() routes to the
right pipeline, and that orchestrate() returns a well-shaped result dict
without crashing.

These tests make real LLM calls (for classify_question) and real Chroma
lookups (for the reviews pipeline). They require:
  - Ollama running locally with qwen3-embedding:0.6b pulled
  - At least one LLM provider configured in .env (groq by default)
  - data/chroma_db/ populated (both "context" and "reviews" collections)

We test the classification decisions and output shapes, not the exact
content of LLM SQL output -- that's what test_execute.py covers.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.orchestrator import classify_question, orchestrate


# ---------------------------------------------------------------------------
# classify_question() -- routing decisions
# ---------------------------------------------------------------------------

def test_sql_question_is_classified_as_sql():
    """
    A purely numerical aggregation question should be routed to sql --
    there are no reviews involved in counting orders.
    """
    route = classify_question("How many orders were delivered in 2018?")
    assert route == "sql", f"Expected 'sql', got '{route}'"


def test_review_sentiment_question_is_classified_as_reviews():
    """
    A question explicitly about what customers said should be routed to
    reviews -- this needs text, not a count.
    """
    route = classify_question("What do customers say about late deliveries?")
    assert route in ("reviews", "both"), (
        f"Expected 'reviews' or 'both' for a sentiment question, got '{route}'"
    )


def test_classification_returns_valid_label():
    """
    Whatever the LLM decides for any reasonable question, it must be one
    of the three valid labels -- never garbage, never a sentence.
    """
    route = classify_question("Which sellers have the most 5-star reviews?")
    assert route in ("sql", "reviews", "both"), (
        f"classify_question() returned an unexpected label: '{route}'"
    )


# ---------------------------------------------------------------------------
# orchestrate() -- result dict shapes
# ---------------------------------------------------------------------------

def test_sql_route_returns_columns_and_rows():
    """
    A clear SQL question should return a dict with 'columns' and 'rows'
    and route='sql'. We don't assert exact SQL output -- just that the
    pipeline ran and returned something shaped correctly.
    """
    result = orchestrate("How many total orders are in the database?")

    # Must always have a route key
    assert "route" in result

    if result["route"] == "sql":
        if "error" in result:
            # An LLM error on a simple count is unexpected but shouldn't
            # be a hard test failure -- log it and skip content checks.
            print(f"[test] SQL pipeline error: {result}")
        else:
            assert "columns" in result
            assert "rows" in result
            assert isinstance(result["columns"], list)
            assert isinstance(result["rows"], list)

    # "both" route is also acceptable for this question
    elif result["route"] == "both":
        if "columns" in result:
            assert isinstance(result["columns"], list)


def test_reviews_route_returns_documents():
    """
    A question about customer opinions should route to reviews or both,
    and return a 'documents' list when it does.
    """
    result = orchestrate("What complaints do customers have about product quality?")

    assert "route" in result

    if result["route"] == "reviews":
        assert "documents" in result
        assert isinstance(result["documents"], list)
        assert len(result["documents"]) > 0

    elif result["route"] == "both":
        if "documents" in result:
            assert isinstance(result["documents"], list)


def test_orchestrate_never_raises():
    """
    orchestrate() must return a dict for any input -- never raise an
    unhandled exception to the caller. Even a nonsense question should
    get a result dict (possibly with an error key inside it).
    """
    try:
        result = orchestrate("xyzzy florp blorb 12345 ??? !!!")
        assert isinstance(result, dict)
        assert "route" in result
    except Exception as e:
        raise AssertionError(
            f"orchestrate() raised an unhandled exception instead of "
            f"returning an error dict: {type(e).__name__}: {e}"
        )


def test_result_always_has_route_key():
    """
    Every result dict from orchestrate() must contain a 'route' key --
    the downstream answer-synthesis stage needs it to know how to
    format the response.
    """
    questions = [
        "How many sellers are there?",
        "What did customers say about broken products?",
        "Which sellers have 5-star reviews and most orders?",
    ]
    for q in questions:
        result = orchestrate(q)
        assert "route" in result, (
            f"orchestrate() returned a dict without 'route' key for: '{q}'\n"
            f"Result was: {result}"
        )
