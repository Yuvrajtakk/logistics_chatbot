"""
tests/test_retrieval.py
------------------------
Proves the "context" Chroma collection retrieves relevant cards by
MEANING, not just exact keyword match -- the entire point of Phase 5.5a.

NOTE: these tests assume build_context_collection() has already been
run at least once (so data/chroma_db/ exists on disk). We don't rebuild
it inside every test -- rebuilding calls Ollama 24 times and would make
the test suite slow for no reason. If data/chroma_db/ is ever deleted,
re-run build_context_collection() by hand once before running these.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import search_context


def test_returns_requested_number_of_results():
    """Asking for k=3 should return exactly 3 cards, no more, no less."""
    results = search_context("How many orders are there?", k=3)
    assert len(results) == 3


def test_finds_relevant_schema_card_by_meaning():
    """
    A question with NO exact wording from any card should still surface
    the right schema table -- proves this is meaning-based search, not
    keyword matching. 'products with no category' never appears
    verbatim anywhere, but the olist_products_dataset schema card is
    the one that documents this exact fact (610 NULL categories).
    """
    results = search_context("How many products have no category assigned?", k=3)
    tables_found = [r.metadata.get("table") for r in results if r.metadata.get("source") == "schema"]
    assert "olist_products_dataset" in tables_found


def test_finds_relevant_example_by_meaning():
    """
    A rephrased version of an existing example question should still
    surface that example, even with completely different wording.
    Real example: "Which payment type is most common?"
    """
    results = search_context("What's the most popular way people pay?", k=3)
    questions_found = [r.metadata.get("question") for r in results if r.metadata.get("source") == "example"]
    assert any("payment type" in q.lower() for q in questions_found if q)


def test_metadata_correctly_tags_source_type():
    """Every result must be tagged as either a schema card or an example -- never neither."""
    results = search_context("What tables exist in this database?", k=5)
    for r in results:
        assert r.metadata.get("source") in ("schema", "example")