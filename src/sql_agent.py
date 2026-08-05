"""
sql_agent.py
------------
Phase 6: the complete SQL pipeline for one question.

Responsibility: take a plain-English question, turn it into safe,
validated, categorically-correct SQL, run it, and return a result dict.

Pipeline order (this ordering is not negotiable -- see Hard Rule 9):
    1. Build prompt (retrieval-narrowed)
    2. LLM generates SQL
    3. REFUSE detection -- catch "I can't answer this" before validator
    4. validate_sql() -- structure check (SELECT only, allowed tables)
    5. check_categoricals() -- catches 'cancelled' vs 'canceled'-style bugs
    6. run_with_repair() -- execute, retry up to 2x on execution errors

Why categorical check comes BEFORE execute:
    A flagged categorical value (e.g. order_status = 'cancelled') must
    NEVER reach the database. The query would run silently and return
    wrong results with no error thrown -- that's the exact bug this
    check exists to prevent. So we stop here and return a "flagged"
    status, not an execution error, letting the caller (orchestrator.py)
    surface it to the user for correction.

Return contract -- always a dict, one of four statuses:
    {"status": "ok",      "sql": "...", "columns": [...], "rows": [...]}
    {"status": "refused", "sql": None,  "reason": "REFUSE: <text>"}
    {"status": "flagged", "sql": "...", "problems": [...], "suggestions": {...}}
    {"status": "error",   "sql": "...", "error": "TypeName", "detail": "..."}

Note on "flagged" status: `suggestions` uses (column, bad_value) tuples
as dict keys. This is fine as a Python object but NOT JSON-serializable.
If Phase 8/9 ever needs to serialize a result dict (log file, web UI,
etc.), suggestions must be re-keyed to strings like "column:bad_value"
first. Documenting here so it doesn't get discovered the hard way later.
"""

import os

from src.llm_client import get_llm
from src.prompt_builder import build_prompt
from src.validator import validate_sql, ValidationError
from src.categorical_check import load_real_values, check_categoricals
from src.execute import run_with_repair, ExecutionError
from src.memory import ConversationMemory


# ----------------------------------------------------------------------
# Module-level cache for categorical ground-truth values.
#
# load_real_values() runs five SELECT DISTINCT queries against the DB
# every time it's called. The categorical values (order_status, payment
# type, etc.) are static -- they don't change while the DB is running.
# Calling it fresh on every question would be 5 unnecessary round-trips
# per turn.
#
# Fix: load once on first call, then return the cached result forever.
# _real_values starts as None (cache empty). _get_real_values() fills
# it on the first call and just returns it on every call after that.
# ----------------------------------------------------------------------
_real_values = None  # type: dict | None


def _get_real_values() -> dict:
    """
    Returns the cached categorical ground-truth values dict, loading
    it from the database on the very first call and reusing it after.

    Callers don't need to know whether this is a fresh DB hit or a cache
    hit -- they just call this and get the dict either way.
    """
    global _real_values
    if _real_values is None:
        # First call -- actually hit the DB. After this line, _real_values
        # is populated and every future call skips straight to the return.
        _real_values = load_real_values()
    return _real_values


# ----------------------------------------------------------------------
# The one public function this file exposes.
# ----------------------------------------------------------------------

def run_sql_agent(question: str, memory: ConversationMemory = None) -> dict:
    """
    Runs the full SQL pipeline for one question and returns a result dict.

    Parameters:
        question: the plain-English question to answer.
        memory:   optional ConversationMemory for multi-turn context.
                  Pass None for a stateless single-question call.

    Returns one of the four status dicts described in the module docstring.
    Never raises to the caller -- all errors are captured and returned
    as {"status": "error", ...} so orchestrator.py can handle them cleanly.
    """
    # ----------------------------------------------------------------
    # Outer safety net: wraps the ENTIRE function body.
    #
    # Why this is here, not just around step 6:
    # The inner try/excepts only cover validate_sql() and run_with_repair().
    # Steps 1-2 (get_llm, build_prompt, llm.invoke) and step 5
    # (_get_real_values, check_categoricals) were previously unprotected --
    # a RateLimitError or network timeout from the FIRST LLM call would
    # propagate straight to the caller, breaking the "never raises" contract.
    # This outer block catches anything the inner handlers miss.
    # ----------------------------------------------------------------
    try:
        llm = get_llm()

        # ----------------------------------------------------------------
        # Step 1: Build the retrieval-augmented prompt.
        # build_prompt() pulls only the schema cards and examples that are
        # relevant to THIS question via semantic search -- not the entire
        # 9-table/15-example manifest every single time.
        # ----------------------------------------------------------------
        prompt = build_prompt(question, memory=memory)

        # ----------------------------------------------------------------
        # Step 2: Ask the LLM to generate SQL.
        # .invoke() sends the prompt, .content strips the AIMessage wrapper,
        # .strip() removes any trailing whitespace or newlines the LLM added.
        # ----------------------------------------------------------------
        raw_sql = llm.invoke(prompt).content.strip()

        # ----------------------------------------------------------------
        # Step 3: REFUSE detection.
        # The prompt instructs the LLM to reply "REFUSE: <reason>" when the
        # question is genuinely out of scope (no cost data, no currency data,
        # etc.). We catch that HERE, before handing the string to validate_sql()
        # -- parse_one() would throw a confusing ParseError on "REFUSE: ...",
        # and wrapping a refusal as a validation failure loses the message.
        # ----------------------------------------------------------------
        if raw_sql.upper().startswith("REFUSE:"):
            return {
                "status": "refused",
                "sql": None,
                "reason": raw_sql,  # full "REFUSE: <reason>" text for answer_synth.py
            }

        # ----------------------------------------------------------------
        # Step 4: Structural validation.
        # validate_sql() checks:
        #   - the statement IS a SELECT (blocks DELETE, DROP, UPDATE, etc.)
        #   - every table touched is on the 9-table allow-list
        #   - attaches LIMIT 1000 to cap result size
        # Returns the validated+limited SQL string on success.
        # Raises ValidationError on any failure.
        # ----------------------------------------------------------------
        try:
            validated_sql = validate_sql(raw_sql)
        except ValidationError as e:
            return {
                "status": "error",
                "sql": raw_sql,       # the raw string that failed, for debugging
                "error": "ValidationError",
                "detail": str(e),
            }

        # ----------------------------------------------------------------
        # Step 5: Categorical value check.
        # check_categoricals() walks the validated SQL's AST and checks that
        # any literal string value compared against a known categorical column
        # (order_status, payment_type, etc.) actually exists in the real data.
        #
        # WHY this step comes BEFORE execute (Hard Rule 9):
        # A wrong categorical value (e.g. 'cancelled' instead of 'canceled')
        # produces no SQL error -- the query runs, returns 0 rows, and the
        # user gets a silently wrong answer. We must stop here, not after.
        #
        # A flagged categorical is NOT an execution failure -- we don't retry
        # it, because retrying without correction would generate the same
        # wrong query again. We return a "flagged" status and let the caller
        # surface it to the user for correction.
        # ----------------------------------------------------------------
        real_values = _get_real_values()
        cat_result = check_categoricals(validated_sql, real_values)

        if not cat_result["ok"]:
            return {
                "status": "flagged",
                "sql": validated_sql,         # the validated SQL that was flagged
                "problems": cat_result["problems"],     # list of (column, bad_value) tuples
                "suggestions": cat_result["suggestions"],  # (column, bad_value) -> suggestion or None
                # NOTE: suggestions keys are Python tuples -- not JSON-serializable.
                # See module docstring for details on what to do if serialization is needed.
            }

        # ----------------------------------------------------------------
        # Step 6: Execute with repair loop.
        # run_with_repair() runs the SQL. If SQLite throws an error (bad
        # column name, ambiguous reference, etc.), it calls regenerate_fn()
        # with the failed SQL + error message, and tries again -- up to
        # MAX_RETRIES times (currently 2, set in execute.py).
        #
        # regenerate_fn is a closure that captures `prompt` and `llm` --
        # so each repair call is: "here's the original prompt context, here's
        # what went wrong, here's the SQL that failed, write a corrected one."
        # This is more useful than just "fix this SQL" with no context.
        # ----------------------------------------------------------------
        def regenerate_fn(failed_sql: str, error_message: str) -> str:
            """
            Called by run_with_repair() on each retry. Feeds the failed SQL
            and the error back to the LLM so it can write a corrected query.
            """
            repair_prompt = (
                f"{prompt}\n\n"
                f"The previous SQL attempt failed with this error:\n"
                f"  {error_message}\n\n"
                f"The failing SQL was:\n"
                f"  {failed_sql}\n\n"
                f"Write a corrected SQL query. Reply with ONLY the SQL, no explanation.\n"
                f"SQL:"
            )
            return llm.invoke(repair_prompt).content.strip()

        try:
            columns, rows = run_with_repair(validated_sql, regenerate_fn)
            return {
                "status": "ok",
                "sql": validated_sql,   # the actual SQL that ran, for logging/display
                "columns": columns,     # list of column name strings
                "rows": rows,           # list of tuples, one per result row
            }
        except (ValidationError, ExecutionError) as e:
            return {
                "status": "error",
                "sql": validated_sql,
                "error": type(e).__name__,
                "detail": str(e),
            }

    except Exception as e:
        # Outer safety net: catches anything not handled by the inner blocks
        # above -- rate limit errors, network timeouts on the first LLM call,
        # Chroma errors from build_prompt's retrieval step, etc.
        # Log it visibly so it's not silently swallowed.
        print(f"[sql_agent] Unexpected error: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "sql": None,  # may not have gotten far enough to have a sql string
            "error": type(e).__name__,
            "detail": str(e),
        }

