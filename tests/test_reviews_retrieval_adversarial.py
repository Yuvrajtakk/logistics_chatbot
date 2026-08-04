"""
tests/test_reviews_retrieval_adversarial.py
--------------------------------------------
Adversarial tests for search_reviews() -- trying to break it, not
confirm it works. Same standing rule applied to every module.

Each test documents its honest expectation going in and WHY it's
adversarial -- not just "edge case exists."
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import search_reviews, _MAX_SEARCH_K


def test_empty_string_query_does_not_crash():
    """
    An empty string is a genuine malformed input a user or an upstream
    bug could send. It should not raise an unhandled exception.

    Honest prediction: Chroma will embed an empty string and return
    k nearest neighbours anyway -- it doesn't validate that the query
    is meaningful. We're proving the function survives, not that the
    results make sense.
    """
    results = search_reviews("", k=3)
    assert isinstance(results, list)


def test_requesting_more_results_than_exist_does_not_crash():
    """
    Asking for k=100_000 (far more than the ~41k stored reviews) used to
    crash with `InternalError: too many SQL variables` -- Chroma passes k
    straight through to SQLite, which has a hard variable-count limit.
    Even k == collection_size (~41k) crashes because the collection
    exceeds SQLite's default SQLITE_MAX_VARIABLE_NUMBER (32,766).

    search_reviews() now caps k at _MAX_SEARCH_K (16,383) before querying.
    This test verifies that cap works: we get real results back without
    crashing, and the count is at most _MAX_SEARCH_K.
    """
    results = search_reviews("anything at all", k=100_000)
    assert isinstance(results, list)
    assert len(results) > 0
    assert len(results) <= _MAX_SEARCH_K


def test_unicode_and_special_characters_do_not_crash():
    """
    Sending a query full of unicode characters, emoji, and punctuation
    that no embedding model was trained to expect shouldn't raise an
    exception -- graceful degradation is the floor.
    """
    weird_query = "🚚❌💔 ??? /// \\n \\t ñ ç ü ação"
    results = search_reviews(weird_query, k=3)
    assert isinstance(results, list)
    assert len(results) <= 3


def test_very_long_query_does_not_crash():
    """
    A query far longer than any model's context window is another
    real-world edge case (someone pasting a whole paragraph into the
    chatbox). We don't care what comes back -- just that it doesn't
    crash or hang.
    """
    long_query = "late delivery " * 500  # 7000+ characters
    results = search_reviews(long_query, k=3)
    assert isinstance(results, list)


def test_sql_injection_string_does_not_crash():
    """
    A query that looks like SQL injection is harmless here (we're just
    embedding a string, not running it against a database), but it's
    worth confirming the function treats it as a plain string, not
    something special.
    """
    injection = "'; DROP TABLE olist_order_reviews_dataset; --"
    results = search_reviews(injection, k=3)
    assert isinstance(results, list)


def test_results_are_distinct():
    """
    All k returned results should have different review_ids -- the same
    review should not appear twice in one result set.

    NOTE: We check review_id, NOT page_content. Short Brazilian reviews
    like 'Atraso na entrega' appear hundreds of times in the dataset
    (different customers, same exact text), so duplicate page_content
    across a result set is real data, not a Chroma bug. The meaningful
    uniqueness guarantee is: the same individual review row isn't
    duplicated.
    """
    results = search_reviews("delivery problems and damaged goods", k=10)
    review_ids = [r.metadata["review_id"] for r in results]
    unique_ids = set(review_ids)
    assert len(unique_ids) == len(review_ids), (
        f"Duplicate review_id found in results: "
        f"{len(review_ids)} results but only {len(unique_ids)} unique IDs.\n"
        f"Duplicated IDs: {[rid for rid in review_ids if review_ids.count(rid) > 1]}"
    )
