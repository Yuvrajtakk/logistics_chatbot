"""
tests/test_memory_adversarial.py
----------------------------------
Adversarial test -- NOT written to confirm memory.py works, written to
try to BREAK it. Specifically: does get_recent_turns() leak a direct
reference to the internal buffer, letting a caller corrupt memory's
state from outside, completely bypassing the MAX_TURNS cap?
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory import ConversationMemory


def test_external_mutation_does_not_corrupt_internal_state():
    mem = ConversationMemory(max_turns=3)
    mem.add_turn("q1", "sql", "a1")

    # Grab what get_recent_turns() hands back, then attack it directly --
    # bypass add_turn() completely and try to smuggle in 10 fake turns.
    leaked_reference = mem.get_recent_turns()
    for i in range(10):
        leaked_reference.append({"question": f"fake{i}", "tool": "sql", "answer": "fake"})

    # If get_recent_turns() properly protects internal state, mem's
    # REAL buffer should still be untouched -- just the 1 real turn.
    real_turns = mem.get_recent_turns()
    assert len(real_turns) == 1, (
        f"BUG: external code mutated memory's internal buffer directly. "
        f"Buffer now has {len(real_turns)} turns, MAX_TURNS cap was bypassed."
    )