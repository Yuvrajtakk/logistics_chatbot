"""
run_eval.py
-----------
Phase 4 test harness. Runs every case in gold_set.jsonl and checks
whether the pipeline behaved the way it SHOULD, given the case type.

IMPORTANT: no LLM is connected yet. For "normal" cases, the SQL in
gold_set.jsonl stands in for what an LLM would generate later. This
proves the harness itself works before any model is added -- so a
future low accuracy score can be blamed on the model, not a broken test.

MATCHES YOUR REAL FUNCTIONS:
    validate_sql(sql) -> returns fixed SQL string on success,
                          raises ValidationError on failure.
    run_query(sql)    -> returns (columns, rows) tuple on success,
                          raises ExecutionError on failure.
    check_categoricals(sql, real_values) -> returns a dict
                          {"ok": bool, "problems": [...]}  (this one
                          IS a dict, we wrote it that way in Phase 3).
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.validator import validate_sql, ValidationError
from src.categorical_check import load_real_values, check_categoricals
from src.execute import run_query, ExecutionError


def load_gold_set(path="eval/gold_set.jsonl"):
    """Reads gold_set.jsonl, one JSON object per line, into a list."""
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_case(case, real_values):
    """
    Runs ONE gold-set case through the real safety pipeline and
    returns whether it behaved as expected for its type.
    """
    case_type = case["type"]

    # "unanswerable" cases have no SQL at all -- correct behavior is a
    # refusal, which nothing needs to be run to prove at this stage.
    if case_type == "unanswerable":
        return {"expected": "refusal, no SQL", "actual": "no SQL provided (correct)", "passed": True}

    sql = case["sql"]

    # ---- Step 1: validator.py -- try/except, since it raises on failure ----
    try:
        validated_sql = validate_sql(sql)
        validator_passed = True
    except ValidationError as e:
        validated_sql = None
        validator_passed = False
        validator_error = str(e)

    if case_type == "should_block":
        passed = not validator_passed
        return {
            "expected": "blocked by validator",
            "actual": "blocked" if passed else "NOT blocked -- BUG",
            "passed": passed,
        }

    if case_type == "bad_table_name" or case_type == "bad_column_name":
        # Either validator rejects it (bad table -- not on allow-list),
        # or it passes validator (bad column names aren't checked there)
        # and then execute.py errors when it actually runs.
        if not validator_passed:
            return {"expected": "error somewhere", "actual": f"caught by validator: {validator_error}", "passed": True}
        try:
            run_query(validated_sql)
            return {"expected": "should error", "actual": "ran with NO error -- BUG", "passed": False}
        except ExecutionError as e:
            return {"expected": "should error", "actual": f"errored as expected: {e}", "passed": True}

    # For "normal" and "bad_categorical" cases, SQL must pass validator first.
    if not validator_passed:
        return {"expected": "should pass validator", "actual": f"BLOCKED -- BUG: {validator_error}", "passed": False}

    # ---- Step 2: categorical_check.py -- this one IS a dict ----
    cat_result = check_categoricals(validated_sql, real_values)

    if case_type == "bad_categorical":
        passed = not cat_result["ok"]
        return {
            "expected": "flagged by categorical_check",
            "actual": f"flagged: {cat_result['problems']}" if passed else "NOT flagged -- BUG",
            "passed": passed,
        }

    if case_type == "normal":
        if not cat_result["ok"]:
            return {"expected": "should pass categorical check", "actual": f"BLOCKED -- BUG: {cat_result['problems']}", "passed": False}

        # ---- Step 3: execute.py -- returns (columns, rows) tuple ----
        try:
            columns, rows = run_query(validated_sql)
            return {"expected": "runs successfully", "actual": f"ran, got {len(rows)} row(s), columns: {columns}", "passed": True}
        except ExecutionError as e:
            return {"expected": "runs successfully", "actual": f"ERRORED -- BUG: {e}", "passed": False}

    return {"expected": "unknown case type", "actual": f"unhandled type: {case_type}", "passed": False}


def main():
    cases = load_gold_set()
    real_values = load_real_values()

    total = len(cases)
    passed_count = 0

    print(f"Running {total} gold-set cases...\n")

    for case in cases:
        result = run_case(case, real_values)
        status = "PASS" if result["passed"] else "FAIL"
        if result["passed"]:
            passed_count += 1

        print(f"[{status}] #{case['id']} ({case['type']}): {case['question']}")
        print(f"       expected: {result['expected']}")
        print(f"       actual:   {result['actual']}")
        print()

    print(f"---- {passed_count}/{total} passed ----")


if __name__ == "__main__":
    main()