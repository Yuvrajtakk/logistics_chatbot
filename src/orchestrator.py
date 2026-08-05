"""
orchestrator.py
---------------
Phase 5.5b: The entry point for a single question from the user.
Classifies the question and dispatches to the appropriate deterministic pipeline.
"""

from src.llm_client import get_llm
from src.prompt_builder import build_prompt
from src.validator import validate_sql, ValidationError
from src.execute import run_with_repair, ExecutionError
from src.retrieval import search_reviews
from src.memory import ConversationMemory
from src.sql_agent import run_sql_agent 

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

_REWRITE_PROMPT = """\
Given the following conversation history and the user's latest follow-up question, rewrite the follow-up question into a standalone, fully-contextualized question. 
If the user's latest question is already standalone, just return it exactly as is.
Do not answer the question. Reply ONLY with the rewritten question. No explanation.

Conversation History:
{history}

Latest Question: {question}
Rewritten Question:"""


def rewrite_question(question: str, memory: ConversationMemory = None) -> str:
    """
    Rewrites a follow-up question into a standalone question using the conversation history.
    """
    if not memory:
        return question
        
    history = memory.format_for_prompt()
    if not history:
        return question
        
    llm = get_llm()
    prompt = _REWRITE_PROMPT.format(history=history, question=question)
    rewritten = llm.invoke(prompt).content.strip()
    return rewritten


def classify_question(question: str) -> str:
    """
    Classifies the user's question into 'sql', 'reviews', or 'both'.
    Falls back to 'sql' on unexpected output.
    """
    llm = get_llm()
    prompt = _CLASSIFY_PROMPT.format(question=question)
    raw = llm.invoke(prompt).content.strip().lower()

    if raw in ("sql", "reviews", "both"):
        return raw

    print(f"[orchestrator] Unexpected classification '{raw}' — falling back to 'sql'.")
    return "sql"


def run_sql_pipeline(question: str, memory: ConversationMemory = None):
    """
    Delegates to sql_agent.run_sql_agent() and translates back to the legacy
    (columns, rows) tuple interface. Kept for backward compatibility.
    """
    result = run_sql_agent(question, memory=memory)

    if result["status"] == "ok":
        return result["columns"], result["rows"]
    elif result["status"] == "refused":
        raise ValidationError(result["reason"])
    elif result["status"] == "flagged":
        raise ValidationError(f"Categorical flag: {result['problems']}")
    else:
        err_type = result.get("error", "ExecutionError")
        detail = result.get("detail", "unknown error")
        if err_type == "ExecutionError":
            raise ExecutionError(detail)
        raise ValidationError(detail)


def run_reviews_pipeline(question: str, k: int = 5):
    """
    Executes a semantic search over customer reviews.
    """
    return search_reviews(question, k=k)


def orchestrate(question: str, memory: ConversationMemory = None) -> dict:
    """
    The single public entry point for the chatbot pipeline.
    Classifies the question and runs the corresponding pipelines.
    Always returns a dictionary describing the result.
    """
    contextualized_question = rewrite_question(question, memory)
    print(f"[orchestrator] Original: '{question}' -> Rewritten: '{contextualized_question}'")
    
    route = classify_question(contextualized_question)

    if route == "sql":
        try:
            agent_result = run_sql_agent(contextualized_question, memory=memory)

            if agent_result["status"] == "ok":
                return {
                    "route": "sql",
                    "sql": agent_result["sql"],
                    "columns": agent_result["columns"],
                    "rows": agent_result["rows"],
                }
            elif agent_result["status"] == "refused":
                return {
                    "route": "sql",
                    "refused": True,
                    "reason": agent_result["reason"],
                }
            elif agent_result["status"] == "flagged":
                return {
                    "route": "sql",
                    "flagged": True,
                    "sql": agent_result["sql"],
                    "problems": agent_result["problems"],
                    "suggestions": agent_result["suggestions"],
                }
            else:
                return {
                    "route": "sql",
                    "error": agent_result["error"],
                    "detail": agent_result["detail"],
                }
        except Exception as e:
            print(f"[orchestrator] Unexpected error in sql pipeline: {type(e).__name__}: {e}")
            return {"route": "sql", "error": type(e).__name__, "detail": str(e)}

    elif route == "reviews":
        try:
            documents = run_reviews_pipeline(contextualized_question)
            return {"route": "reviews", "documents": documents}
        except Exception as e:
            return {"route": "reviews", "error": type(e).__name__, "detail": str(e)}

    else:
        result = {"route": "both"}

        try:
            agent_result = run_sql_agent(contextualized_question, memory=memory)
            if agent_result["status"] == "ok":
                result["sql"] = agent_result["sql"]
                result["columns"] = agent_result["columns"]
                result["rows"] = agent_result["rows"]
            elif agent_result["status"] == "refused":
                result["sql_refused"] = agent_result["reason"]
            elif agent_result["status"] == "flagged":
                result["sql_flagged"] = agent_result["problems"]
                result["sql_suggestions"] = agent_result["suggestions"]
            else:
                result["sql_error"] = agent_result.get("detail", "unknown error")
        except Exception as e:
            result["sql_error"] = str(e)

        try:
            documents = run_reviews_pipeline(contextualized_question)
            result["documents"] = documents
        except Exception as e:
            result["reviews_error"] = str(e)

        return result
