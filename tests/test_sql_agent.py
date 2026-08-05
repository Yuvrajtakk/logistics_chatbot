"""
tests/test_sql_agent.py
------------------------
Phase 6: runs the gold set from eval/gold_set.jsonl through the REAL
pipeline for the first time -- real LLM generating SQL, real validator,
real categorical check, real execute.

What this file proves that run_eval.py (Phase 4) did NOT:
    - The LLM actually generates SQL that's at least structurally valid
      for the normal questions
    - The four-status return dict from run_sql_agent() has the right shape
      for every status type
    - Unanswerable questions get "refused" (or "error"), never silent rows
    - Bad categoricals get "flagged" before any DB hit, not after
    - should_block SQL (DELETE, bad table) gets "error", not rows

We do NOT assert exact SQL text or exact row values -- the LLM is
non-deterministic and we're testing pipeline behavior, not the model.

Requires:
    - Ollama running locally with nomic-embed-text and qwen3-embedding:0.6b
    - Groq API key in .env (or whatever DEFAULT_PROVIDER resolves to)
    - data/chroma_db/ populated (both collections)
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sql_agent import run_sql_agent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_gold_set(path="eval/gold_set.jsonl"):
    """Reads gold_set.jsonl into a list of dicts, one per line."""
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


# ---------------------------------------------------------------------------
# Tests by case type
# ---------------------------------------------------------------------------

def test_normal_questions_return_ok_or_error_never_refused_never_flagged():
    """
    The 8 "normal" gold-set questions have real, answerable SQL.
    run_sql_agent() should return status="ok" (LLM wrote valid SQL and
    it ran) or status="error" (LLM wrote broken SQL and retries failed).
    It must NOT return "refused" (LLM wrongly declared the question
    unanswerable) or "flagged" (categorical check wrongly tripped on a
    correct value).

    We accept "error" here because the LLM is non-deterministic -- the
    goal of this test is to confirm the pipeline *routes* correctly,
    not that the model is perfect. Record the real accuracy below.
    """
    cases = [c for c in load_gold_set() if c["type"] == "normal"]
    assert len(cases) > 0, "No normal cases found in gold_set.jsonl"

    ok_count = 0
    error_count = 0
    refused_count = 0  # should be 0 -- normal questions are answerable

    for case in cases:
        result = run_sql_agent(case["question"])

        # Always a dict, always has status
        assert isinstance(result, dict), f"#{case['id']}: result is not a dict"
        assert "status" in result, f"#{case['id']}: result has no 'status' key"

        status = result["status"]
        assert status != "refused", (
            f"#{case['id']} (normal): LLM refused an answerable question.\n"
            f"  Question: {case['question']}\n"
            f"  Reason: {result.get('reason')}"
        )
        assert status != "flagged", (
            f"#{case['id']} (normal): categorical check tripped on a correct value.\n"
            f"  Question: {case['question']}\n"
            f"  Problems: {result.get('problems')}"
        )

        if status == "ok":
            # Confirm the ok dict shape
            assert "sql" in result, f"#{case['id']}: ok result missing 'sql'"
            assert "columns" in result, f"#{case['id']}: ok result missing 'columns'"
            assert "rows" in result, f"#{case['id']}: ok result missing 'rows'"
            assert isinstance(result["columns"], list)
            assert isinstance(result["rows"], list)
            ok_count += 1
        else:
            error_count += 1

    total = len(cases)
    print(f"\n[normal questions] {ok_count}/{total} ok, {error_count}/{total} error")
    # We don't assert a minimum accuracy here -- record what you get and
    # report it honestly. Low accuracy = model issue, not pipeline issue.


def test_bad_categorical_questions_return_flagged():
    """
    Gold-set cases with type="bad_categorical" have SQL that compares
    a categorical column to a value that doesn't exist in the real data
    (e.g. order_status = 'cancelled' instead of 'canceled').

    The correct pipeline behavior: the LLM may or may not reproduce the
    bad value from the question. If it does, the result must be "flagged"
    -- the categorical check caught it before the query ran.

    If the LLM happens to write the CORRECT value (self-correcting from
    context), the result will be "ok" -- that's acceptable and not a bug.
    What's NOT acceptable: "error" from trying to run a bad-value query
    (means categorical check is missing), or "refused" (wrong route).
    """
    cases = [c for c in load_gold_set() if c["type"] == "bad_categorical"]
    assert len(cases) > 0, "No bad_categorical cases found in gold_set.jsonl"

    for case in cases:
        result = run_sql_agent(case["question"])

        assert isinstance(result, dict)
        assert "status" in result
        status = result["status"]

        # "flagged" or "ok" (LLM self-corrected) are both acceptable.
        # "error" would mean the bad value got through to the DB -- that's a bug.
        assert status in ("flagged", "ok"), (
            f"#{case['id']} (bad_categorical): expected 'flagged' or 'ok', got '{status}'.\n"
            f"  Question: {case['question']}\n"
            f"  Note: {case.get('note')}\n"
            f"  Result: {result}"
        )

        if status == "flagged":
            # Confirm flagged dict shape
            assert "sql" in result, f"#{case['id']}: flagged result missing 'sql'"
            assert "problems" in result, f"#{case['id']}: flagged result missing 'problems'"
            assert "suggestions" in result, f"#{case['id']}: flagged result missing 'suggestions'"
            assert len(result["problems"]) > 0, (
                f"#{case['id']}: flagged result has empty problems list"
            )


def test_unanswerable_questions_return_refused_or_error():
    """
    Gold-set cases with type="unanswerable" have no valid SQL (profit
    margins, currency, etc. -- data that simply doesn't exist).
    Expected behavior: LLM returns "REFUSE: <reason>", pipeline returns
    status="refused". An "error" (LLM tried to write SQL and it broke)
    is also acceptable. What's NOT acceptable: "ok" with rows -- the
    LLM hallucinated an answer.
    """
    cases = [c for c in load_gold_set() if c["type"] == "unanswerable"]
    assert len(cases) > 0, "No unanswerable cases found in gold_set.jsonl"

    for case in cases:
        result = run_sql_agent(case["question"])

        assert isinstance(result, dict)
        assert "status" in result
        status = result["status"]

        assert status != "ok", (
            f"#{case['id']} (unanswerable): pipeline returned 'ok' with rows -- "
            f"LLM hallucinated SQL for a question with no valid answer.\n"
            f"  Question: {case['question']}\n"
            f"  Note: {case.get('note')}\n"
            f"  SQL generated: {result.get('sql')}"
        )

        if status == "refused":
            assert "reason" in result, f"#{case['id']}: refused result missing 'reason'"


def test_should_block_cases_return_error_never_ok():
    """
    Gold-set cases with type="should_block" are DELETE statements or
    queries touching banned tables. validate_sql() must block these.
    Expected: status="error" (caught by validator). Never "ok".
    """
    cases = [c for c in load_gold_set() if c["type"] == "should_block"]
    assert len(cases) > 0, "No should_block cases found in gold_set.jsonl"

    for case in cases:
        # For should_block cases, the LLM sees the question and should
        # ideally refuse or generate blocked SQL. Either way, never "ok".
        result = run_sql_agent(case["question"])

        assert isinstance(result, dict)
        assert "status" in result
        status = result["status"]

        assert status != "ok", (
            f"#{case['id']} (should_block): pipeline returned 'ok' -- "
            f"a DELETE or disallowed table got past the validator.\n"
            f"  Question: {case['question']}\n"
            f"  Note: {case.get('note')}\n"
            f"  SQL: {result.get('sql')}"
        )


def test_result_dict_always_has_status_key():
    """
    Every call to run_sql_agent() must return a dict with a 'status' key,
    regardless of question type or LLM behavior. This is the contract
    answer_synth.py (Phase 7) relies on unconditionally.
    """
    cases = load_gold_set()
    for case in cases:
        result = run_sql_agent(case["question"])
        assert isinstance(result, dict), (
            f"#{case['id']}: run_sql_agent() returned {type(result).__name__}, not dict"
        )
        assert "status" in result, (
            f"#{case['id']}: result dict has no 'status' key\nResult: {result}"
        )
        assert result["status"] in ("ok", "refused", "flagged", "error"), (
            f"#{case['id']}: result has unexpected status '{result['status']}'"
        )


def test_run_sql_agent_never_raises():
    """
    run_sql_agent() must never raise an unhandled exception -- all errors
    are caught internally and returned as {"status": "error", ...}.
    Test with the full gold set plus a few adversarial inputs.
    """
    adversarial = [
        "",                              # empty question
        "xyzzy florp blorb ??? !!!",    # nonsense
        "'; DROP TABLE olist_orders_dataset; --",  # SQL injection in question
    ]

    all_questions = [c["question"] for c in load_gold_set()] + adversarial

    for q in all_questions:
        try:
            result = run_sql_agent(q)
            assert isinstance(result, dict), f"Got {type(result).__name__} for: '{q[:60]}'"
        except Exception as e:
            raise AssertionError(
                f"run_sql_agent() raised {type(e).__name__} instead of returning "
                f"an error dict.\n  Question: '{q[:60]}'\n  Error: {e}"
            )
