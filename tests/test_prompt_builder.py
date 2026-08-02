"""
tests/test_prompt_builder.py
------------------------------
Proves build_prompt() correctly assembles a retrieval-narrowed prompt:
relevant schema, full glossary, relevant examples, optional recent
conversation, and the question itself -- in that order.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.prompt_builder import build_prompt
from src.memory import ConversationMemory


def test_prompt_contains_all_required_sections():
    """Every section header should be present, every time."""
    prompt = build_prompt("How many orders have been delivered?")

    assert "=== RELEVANT SCHEMA" in prompt
    assert "=== GLOSSARY ===" in prompt
    assert "=== SIMILAR EXAMPLES ===" in prompt
    assert "=== QUESTION ===" in prompt
    assert "How many orders have been delivered?" in prompt


def test_glossary_is_always_included_in_full():
    """
    All 5 glossary terms should appear every time, regardless of the
    question -- glossary is never narrowed by retrieval (see reasoning
    discussed: it's small, and rules can matter even when the question
    doesn't obviously reference them).
    """
    prompt = build_prompt("What is the average freight value?")

    assert "TERM: late_delivery" in prompt
    assert "TERM: unique_customer" in prompt
    assert "TERM: top_seller" in prompt
    assert "TERM: average_delivery_time" in prompt
    assert "TERM: unanswerable_question" in prompt


def test_schema_is_narrowed_not_full_dump():
    """
    The whole point of this refactor: NOT all 9 tables should appear
    for a question clearly about one specific table. Some tables that
    have nothing to do with the question should be absent.
    """
    prompt = build_prompt("How many products have no category assigned?")

    assert "TABLE: olist_products_dataset" in prompt
    # A table genuinely unrelated to this question should NOT show up --
    # if this fails, retrieval isn't actually narrowing anything.
    assert "TABLE: olist_geolocation_dataset" not in prompt


def test_no_memory_means_no_recent_conversation_section():
    """
    Calling build_prompt() with no memory argument (or memory=None)
    should NOT include an empty 'RECENT CONVERSATION' header --
    matches format_for_prompt()'s empty-string behavior.
    """
    prompt = build_prompt("How many orders are there?")
    assert "RECENT CONVERSATION" not in prompt


def test_memory_with_history_is_included():
    """
    Passing a ConversationMemory that already has turns in it should
    surface those turns inside the prompt.
    """
    mem = ConversationMemory()
    mem.add_turn("Which state has the most orders?", "sql", "São Paulo (SP).")

    prompt = build_prompt("What about payment type?", memory=mem)

    assert "RECENT CONVERSATION" in prompt
    assert "Which state has the most orders?" in prompt
    assert "São Paulo (SP)." in prompt