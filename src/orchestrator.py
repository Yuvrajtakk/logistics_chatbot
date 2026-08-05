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
from src.sql_agent import run_sql_agent  # Phase 6: owns the full SQL pipeline


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
    Phase 6 shim: delegates to sql_agent.run_sql_agent(), which owns
    the complete, correctly-ordered pipeline:
        generate → REFUSE check → validate → categorical check → execute+repair

    Kept as a named function for any code that still calls it by name,
    but orchestrate() now calls run_sql_agent() directly so it can
    surface all four statuses (ok / refused / flagged / error) in the
    result dict without losing information.

    This shim translates back to (columns, rows)-or-raise for callers
    that expect the old tuple interface. The "flagged" status collapses
    to ValidationError here -- callers that need the full flagged detail
    (problems list, suggestions dict) should call run_sql_agent() directly.
    """
    result = run_sql_agent(question, memory=memory)

    if result["status"] == "ok":
        return result["columns"], result["rows"]
    elif result["status"] == "refused":
        raise ValidationError(result["reason"])
    elif result["status"] == "flagged":
        # Collapse to ValidationError -- loses suggestions, but this shim
        # exists only for backward compat; use run_sql_agent() for full info.
        raise ValidationError(f"Categorical flag: {result['problems']}")
    else:  # "error"
        err_type = result.get("error", "ExecutionError")
        detail = result.get("detail", "unknown error")
        if err_type == "ExecutionError":
            raise ExecutionError(detail)
        raise ValidationError(detail)


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
            # Call run_sql_agent() directly -- it handles all four outcomes
            # (ok / refused / flagged / error) and always returns a dict.
            agent_result = run_sql_agent(question, memory=memory)

            if agent_result["status"] == "ok":
                # Success: query ran, rows returned.
                return {
                    "route": "sql",
                    "sql": agent_result["sql"],
                    "columns": agent_result["columns"],
                    "rows": agent_result["rows"],
                }
            elif agent_result["status"] == "refused":
                # LLM said the question is out of scope.
                return {
                    "route": "sql",
                    "refused": True,
                    "reason": agent_result["reason"],
                }
            elif agent_result["status"] == "flagged":
                # Categorical check caught a bad value -- never ran the query.
                return {
                    "route": "sql",
                    "flagged": True,
                    "sql": agent_result["sql"],
                    "problems": agent_result["problems"],
                    "suggestions": agent_result["suggestions"],
                }
            else:  # "error"
                return {
                    "route": "sql",
                    "error": agent_result["error"],
                    "detail": agent_result["detail"],
                }
        except Exception as e:
            # Safety net: run_sql_agent() should never raise (it catches
            # internally), but keep this here in case of import errors,
            # etc. Log it visibly so it's not silently swallowed.
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
            agent_result = run_sql_agent(question, memory=memory)
            if agent_result["status"] == "ok":
                result["sql"] = agent_result["sql"]
                result["columns"] = agent_result["columns"]
                result["rows"] = agent_result["rows"]
            elif agent_result["status"] == "refused":
                result["sql_refused"] = agent_result["reason"]
            elif agent_result["status"] == "flagged":
                result["sql_flagged"] = agent_result["problems"]
                result["sql_suggestions"] = agent_result["suggestions"]
            else:  # "error"
                result["sql_error"] = agent_result.get("detail", "unknown error")
        except Exception as e:
            result["sql_error"] = str(e)

        try:
            documents = run_reviews_pipeline(question)
            result["documents"] = documents
        except Exception as e:
            result["reviews_error"] = str(e)

        return result
