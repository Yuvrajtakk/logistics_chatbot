"""
tests/test_answer_synth_adversarial.py
--------------------------------------
Phase 7: Adversarial tests for answer_synth.py

Focus areas:
1. LLM summarization call throws an exception (network error, rate limit)
2. Malformed orchestrate() output shape (missing keys)
3. Empty documents list
4. Never raises an exception up to the caller
"""

import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.answer_synth import synthesize_answer
from langchain_core.documents import Document

def test_llm_summarization_throws_exception():
    """
    If the LLM summarization call fails for any reason, synthesize_answer
    must catch it and return a fallback string, not raise.
    """
    result = {
        "route": "reviews",
        "documents": [Document(page_content="Test review")]
    }
    
    # Mock get_llm to raise an Exception
    with patch("src.answer_synth.get_llm", side_effect=Exception("Fake API Timeout")):
        ans = synthesize_answer("Question", result)
        
    assert "couldn't summarize them right now" in ans
    assert "Fake API Timeout" not in ans


def test_malformed_output_missing_route():
    """
    If the orchestrator returns a dict without a 'route' key, 
    the synthesizer should handle it gracefully.
    """
    result = {"random_key": "random_value"}
    ans = synthesize_answer("Question", result)
    assert "couldn't understand the result" in ans


def test_malformed_output_missing_rows_for_sql():
    """
    If route="sql" but "rows" is missing (which shouldn't happen unless error, 
    but what if it does?), it shouldn't crash.
    """
    result = {"route": "sql", "columns": ["id"]}
    ans = synthesize_answer("Question", result)
    assert "No matching records were found" in ans


def test_empty_documents_list_reviews():
    """
    If route="reviews" but documents is empty, it should not call the LLM
    and should return a friendly empty-state message.
    """
    result = {"route": "reviews", "documents": []}
    
    with patch("src.answer_synth.get_llm") as mock_get_llm:
        ans = synthesize_answer("Question", result)
        mock_get_llm.assert_not_called()
        
    assert "couldn't find any relevant comments" in ans


def test_empty_documents_list_both():
    """
    If route="both" and documents is empty, it handles the SQL part normally
    and appending the empty review message.
    """
    result = {
        "route": "both",
        "columns": ["id"],
        "rows": [(1,)],
        "documents": []
    }
    ans = synthesize_answer("Question", result)
    assert "The result is id: 1" in ans
    assert "couldn't find any relevant comments" in ans


def test_never_raises_outer_try_except():
    """
    Even if something fundamentally breaks (e.g. result is None instead of dict),
    the outer try/except should catch it and return a string.
    """
    # Result is None instead of dict. result.get() will raise AttributeError
    ans = synthesize_answer("Question", None) 
    assert "encountered an error while trying to summarize" in ans
