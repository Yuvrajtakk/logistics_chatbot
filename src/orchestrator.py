"""
orchestrator.py
---------------
Phase 5.5b: the entry point for a single question from the user.

Responsibility: ONE classification call (sql / reviews / both),
then dispatch to the fixed pipelines that already exist. That's it.

What this file is NOT:
  - Not an autonomous agent. It makes exactly one LLM call per question
    (the classification call), then runs deterministic code paths.
  - Not a loop. It does not re-classify or re-decide mid-flight.
  - Not a database accessor. It calls execute.py's run_with_repair()
    instead of touching sqlite3 directly -- same Rule 3 boundary as
    every other file.

The three routes:
  "sql"     -- build a prompt, generate SQL, validate, execute, return rows.
  "reviews" -- semantic search over the ~41k review corpus, return docs.
  "both"    -- run both pipelines, return both results.
"""

from src.llm_client import get_llm
from src.prompt_builder import build_prompt
from src.validator import validate_sql, ValidationError
from src.execute import run_with_repair, ExecutionError
from src.retrieval import search_reviews
from src.memory import ConversationMemory


# The classification prompt is intentionally tiny -- one decision,
# three valid outputs, no explanation. Temperature=0 (set in llm_client)
# means the same question always gets the same classification.
_CLASSIFY_PROMPT = """\
You are a question router for a Brazilian e-commerce chatbot.
Classify the user's question into exactly ONE of these three categories:
  sql      -- the question needs database numbers (counts, totals, averages, rankings, etc.)
  reviews  -- the question needs customer review text (sentiment, complaints, opinions, quotes)
  both     -- the question needs database numbers AND customer review text

Reply with ONLY the single word: sql, reviews, or both.
No explanation. No punctuation. No extra words.

Question: {question}
Category:"""


def classify_question(question: str) -> str:
    """
    Sends the question to the LLM with a single-word-reply prompt.
    Returns one of: "sql", "reviews", "both".

    Falls back to "sql" if the LLM returns something unexpected -- sql
    is the safer default (it runs through validator + executor, so
    errors surface cleanly) rather than silently dropping a query.
    """
    llm = get_llm()
    prompt = _CLASSIFY_PROMPT.format(question=question)

    # .invoke() is the standard LangChain call -- returns an AIMessage.
    # .content strips the wrapper and gives us the raw reply string.
    raw = llm.invoke(prompt).content.strip().lower()

    if raw in ("sql", "reviews", "both"):
        return raw

    # LLM returned something unexpected (extra words, punctuation,
    # a full sentence). Log it visibly and fall back safely.
    print(f"[orchestrator] Unexpected classification '{raw}' — falling back to 'sql'.")
    return "sql"


def run_sql_pipeline(question: str, memory: ConversationMemory = None):
    """
    The existing SQL path: build prompt → generate SQL → validate →
    execute (with up-to-2-retry repair loop). Returns (columns, rows)
    on success, or raises ExecutionError / ValidationError if it fails
    after retries.

    Kept as a named function so orchestrate() can call it cleanly for
    both the "sql" and "both" routes without duplicating the logic.
    """
    llm = get_llm()

    # Build the retrieval-augmented prompt -- only relevant schema
    # cards + examples for THIS question, not the entire manifest.
    prompt = build_prompt(question, memory=memory)

    def regenerate_fn(failed_sql: str, error_message: str) -> str:
        """
        Repair stub: feed the failed SQL + error back to the LLM and
        ask for a corrected version. Called by run_with_repair() on
        each retry -- same bounded-retry pattern from execute.py.
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

    # First LLM call: generate SQL from the prompt.
    raw_sql = llm.invoke(prompt).content.strip()

    # The prompt tells the LLM to reply with exactly "REFUSE: <reason>"
    # when it can't answer the question. Detect that here before trying
    # to parse it as SQL -- validate_sql() would raise ParseError on it,
    # which is confusing and misleading. Raise ValidationError directly
    # so orchestrate()'s error-handling sees a clean, descriptive message.
    if raw_sql.upper().startswith("REFUSE:"):
        raise ValidationError(raw_sql)

    # Validate before touching the database.
    validated_sql = validate_sql(raw_sql)

    # Execute with repair loop (max 2 retries, per execute.py's MAX_RETRIES).
    columns, rows = run_with_repair(validated_sql, regenerate_fn)
    return columns, rows


def run_reviews_pipeline(question: str, k: int = 5):
    """
    The semantic-search path: embed the question, find k nearest
    review comments in the "reviews" Chroma collection. Returns a
    list of LangChain Document objects (each has .page_content and
    .metadata with source="review" and review_id).

    k=5 default: enough to see a meaningful spread of sentiment without
    flooding the next stage. Caller can override for the "both" route
    if we want a wider sample when SQL results are also present.
    """
    return search_reviews(question, k=k)


def orchestrate(question: str, memory: ConversationMemory = None) -> dict:
    """
    The single public entry point for the whole chatbot pipeline.

    Takes a plain-English question, classifies it, runs the right
    pipeline(s), and returns a result dict. Always returns a dict --
    never raises to the caller. Errors are captured and returned as
    {"error": ...} so chat_cli.py (Phase 8) can present them cleanly.

    Return shape per route:
      "sql":
        {"route": "sql", "columns": [...], "rows": [...]}
      "reviews":
        {"route": "reviews", "documents": [Document, ...]}
      "both":
        {"route": "both",
         "columns": [...], "rows": [...],
         "documents": [Document, ...]}

    On any unhandled error:
        {"route": route, "error": "...", "detail": "..."}
    """
    route = classify_question(question)

    if route == "sql":
        try:
            columns, rows = run_sql_pipeline(question, memory=memory)
            return {"route": "sql", "columns": columns, "rows": rows}
        except (ValidationError, ExecutionError) as e:
            return {"route": "sql", "error": type(e).__name__, "detail": str(e)}
        except Exception as e:
            # Safety net: any other unexpected exception (e.g. LLM network
            # error, Chroma timeout) should still return a dict, not crash
            # the caller. Log it visibly so it's not silently swallowed.
            print(f"[orchestrator] Unexpected error in sql pipeline: {type(e).__name__}: {e}")
            return {"route": "sql", "error": type(e).__name__, "detail": str(e)}

    elif route == "reviews":
        try:
            documents = run_reviews_pipeline(question)
            return {"route": "reviews", "documents": documents}
        except Exception as e:
            return {"route": "reviews", "error": type(e).__name__, "detail": str(e)}

    else:  # "both"
        result = {"route": "both"}

        try:
            columns, rows = run_sql_pipeline(question, memory=memory)
            result["columns"] = columns
            result["rows"] = rows
        except (ValidationError, ExecutionError) as e:
            result["sql_error"] = str(e)

        try:
            documents = run_reviews_pipeline(question)
            result["documents"] = documents
        except Exception as e:
            result["reviews_error"] = str(e)

        return result
