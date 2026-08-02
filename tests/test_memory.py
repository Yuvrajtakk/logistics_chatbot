"""
tests/test_memory.py
---------------------
Proves ConversationMemory stores turns correctly, trims to the size
cap, and formats itself into prompt-ready text.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory import ConversationMemory


def test_add_turn_stores_question_tool_answer():
    """A freshly added turn should be retrievable exactly as stored."""
    mem = ConversationMemory()
    mem.add_turn("How many orders?", "sql", "There are 99,441 orders.")

    turns = mem.get_recent_turns()
    assert len(turns) == 1
    assert turns[0]["question"] == "How many orders?"
    assert turns[0]["tool"] == "sql"
    assert turns[0]["answer"] == "There are 99,441 orders."


def test_buffer_caps_at_max_turns():
    """
    Adding more turns than max_turns should drop the OLDEST ones,
    keeping the buffer size fixed -- not growing forever.
    """
    mem = ConversationMemory(max_turns=3)

    for i in range(5):
        mem.add_turn(f"question {i}", "sql", f"answer {i}")

    turns = mem.get_recent_turns()
    assert len(turns) == 3

    # Should have kept the 3 MOST RECENT turns (2, 3, 4) and dropped
    # the oldest two (0, 1).
    assert turns[0]["question"] == "question 2"
    assert turns[-1]["question"] == "question 4"


def test_format_for_prompt_empty_buffer():
    """A brand new conversation with no history should format to an empty string."""
    mem = ConversationMemory()
    assert mem.format_for_prompt() == ""


def test_format_for_prompt_includes_all_turns():
    """The formatted text block should contain every question and answer in the buffer."""
    mem = ConversationMemory()
    mem.add_turn("Which state has the most orders?", "sql", "São Paulo (SP).")
    mem.add_turn("What about payment type?", "sql", "Credit card is most common.")

    formatted = mem.format_for_prompt()

    assert "Which state has the most orders?" in formatted
    assert "São Paulo (SP)." in formatted
    assert "What about payment type?" in formatted
    assert "Credit card is most common." in formatted


def test_clear_empties_the_buffer():
    """clear() should wipe the buffer back to empty."""
    mem = ConversationMemory()
    mem.add_turn("Some question", "sql", "Some answer")
    mem.clear()

    assert mem.get_recent_turns() == []