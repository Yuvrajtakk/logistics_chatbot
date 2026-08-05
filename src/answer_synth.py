"""
answer_synth.py
---------------
Phase 7: Synthesizes the result dict from orchestrator() into a plain-English
answer for the user. Handles all four SQL statuses, the reviews path (via a
summarization LLM call), and the "both" path.

Never raises an exception to the caller. Always returns a plain string.
"""

from src.llm_client import get_llm
from src.sql_agent import _get_real_values

_REVIEWS_PROMPT = """\
You are an assistant for a Brazilian e-commerce company.
You have been asked: "{question}"

Here are relevant customer review snippets (in Portuguese):
{reviews_text}

Write 2-3 sentences in English summarizing the main themes. 
Include exactly ONE short quote from the reviews to illustrate the point.
The quote should be kept in the original Portuguese, followed immediately by a brief English translation in parentheses.

Do not write anything else. Just the summary.
"""

def synthesize_answer(question: str, result: dict) -> str:
    """
    Takes the orchestrator's result dict and the original question,
    and returns a plain-English answer. Never raises an exception.
    """
    try:
        route = result.get("route")
        
        if route == "sql":
            return _synthesize_sql(result)
        elif route == "reviews":
            return _synthesize_reviews(question, result)
        elif route == "both":
            return _synthesize_both(question, result)
        else:
            return "I couldn't understand the result from the system."
    except Exception as e:
        print(f"[answer_synth] Unexpected error in synthesize_answer: {type(e).__name__}: {e}")
        return "I found some information, but encountered an error while trying to summarize it."


def _synthesize_sql(result: dict) -> str:
    if result.get("refused"):
        reason = result.get("reason", "I cannot answer this question.")
        if reason.upper().startswith("REFUSE:"):
            reason = reason[7:].strip()
        return reason
        
    if result.get("flagged"):
        return _format_flagged(result.get("problems", []), result.get("suggestions", {}))
        
    if "error" in result:
        return "I encountered a technical issue while trying to answer that."

    return _narrate_sql_rows(result.get("columns", []), result.get("rows", []))


def _synthesize_reviews(question: str, result: dict) -> str:
    if "error" in result:
        return "I couldn't search customer reviews for this question."
        
    documents = result.get("documents", [])
    if not documents:
        return "I searched the customer reviews, but couldn't find any relevant comments for that question."
        
    return _summarize_documents(question, documents)


def _summarize_documents(question: str, documents: list) -> str:
    reviews_text = "\n".join(f"- {doc.page_content}" for doc in documents)
    prompt = _REVIEWS_PROMPT.format(question=question, reviews_text=reviews_text)
    
    try:
        llm = get_llm()
        reply = llm.invoke(prompt).content.strip()
        return reply
    except Exception as e:
        print(f"[answer_synth] Reviews summarization LLM call failed: {type(e).__name__}: {e}")
        return "I found relevant reviews but couldn't summarize them right now."


def _synthesize_both(question: str, result: dict) -> str:
    if result.get("sql_error") and result.get("reviews_error"):
        return "I encountered a technical issue and couldn't answer this question right now."

    # SQL part
    sql_part = ""
    if result.get("sql_error"):
        sql_part = "I couldn't query the database for this question."
    elif result.get("sql_refused"):
        reason = result["sql_refused"]
        if reason.upper().startswith("REFUSE:"):
            reason = reason[7:].strip()
        sql_part = reason
    elif result.get("sql_flagged"):
        sql_part = _format_flagged(result["sql_flagged"], result.get("sql_suggestions", {}))
    elif "rows" in result:
        sql_part = _narrate_sql_rows(result.get("columns", []), result.get("rows", []))
    else:
        sql_part = "I couldn't find the database records for this question."

    # Reviews part
    reviews_part = ""
    if result.get("reviews_error"):
        reviews_part = "I couldn't search customer reviews for this question."
    elif "documents" in result:
        docs = result["documents"]
        if not docs:
            reviews_part = "I searched the customer reviews, but couldn't find any relevant comments for that question."
        else:
            reviews_part = _summarize_documents(question, docs)
    else:
        reviews_part = "I couldn't search customer reviews for this question."

    # Stitched together separated by double newline
    return f"{sql_part}\n\n{reviews_part}"


def _narrate_sql_rows(columns: list, rows: list) -> str:
    if not rows:
        return "No matching records were found for that question."
        
    if len(rows) == 1:
        row = rows[0]
        pairs = [f"{col}: {val}" for col, val in zip(columns, row)]
        return f"The result is {', '.join(pairs)}."
        
    lines = ["Here are the results:"]
    display_rows = rows[:10]
    for row in display_rows:
        pairs = [f"{col}: {val}" for col, val in zip(columns, row)]
        lines.append(f"- {', '.join(pairs)}")
        
    if len(rows) > 10:
        lines.append(f"...and {len(rows) - 10} more records.")
        
    return "\n".join(lines)


def _format_flagged(problems: list, suggestions: dict) -> str:
    if not problems:
        return "The query contained an unrecognized value."
        
    col, bad_val = problems[0]
    suggestion = suggestions.get((col, bad_val))
    
    if suggestion:
        return f"'{bad_val}' isn't a recognized {col} — did you mean '{suggestion}'?"
    
    try:
        real_values = _get_real_values()
        valid_set = real_values.get(col, set())
    except Exception:
        valid_set = set()
        
    if 0 < len(valid_set) <= 10:
        valid_list = ", ".join(sorted(str(v) for v in valid_set))
        return f"'{bad_val}' isn't a recognized {col}. Valid values are: {valid_list}."
    else:
        return f"'{bad_val}' isn't a recognized {col}."
