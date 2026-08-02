"""
tests/test_retrieval_adversarial.py
-------------------------------------
Adversarial tests -- trying to break retrieval.py, not confirm it works.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import build_context_collection, search_context


def test_rebuilding_does_not_duplicate_cards():
    """
    build_context_collection()'s own docstring claims it's safe to
    re-run and won't 'silently accumulate duplicates' -- but the code
    never actually deletes the old collection first. This test checks
    whether that claim is TRUE, rather than trusting the comment.

    Honest prediction going in: uncertain. If Chroma upserts on
    matching IDs, count stays at 24. If it errors or blindly appends,
    this will fail or crash -- either way, we now KNOW instead of assume.
    """
    build_context_collection()  # first build
    build_context_collection()  # rebuild -- same ids, same source data

    # Ask for way more results than exist (24 total cards), forcing
    # Chroma to return everything it actually has.
    results = search_context("orders", k=100)

    assert len(results) == 24, (
        f"BUG or unverified claim: expected 24 cards after rebuilding twice, "
        f"got {len(results)}. The docstring's 'safe to re-run' claim is "
        f"either wrong, or k=100 isn't actually returning everything."
    )


def test_requesting_more_results_than_exist_does_not_crash():
    """
    Asking for k=1000 results (way more than the 24 real cards) should
    NOT crash -- it should just return however many actually exist.
    """
    results = search_context("delivery time", k=1000)
    assert len(results) <= 24
    assert len(results) > 0


def test_empty_string_query_does_not_crash():
    """
    An empty question string is a genuinely malformed input a real
    user (or a bug upstream) could send. This should not throw an
    unhandled exception.
    """
    results = search_context("", k=3)
    assert isinstance(results, list)