"""
orchestrator.py
---------------
Phase 5.5b: The entry point for a single question from the user.
Classifies the question and dispatches to the appropriate deterministic pipeline.
"""

import src.llm_client as llm_client
# Backward‑compatible alias for tests that monkeypatch src.orchestrator.get_llm
get_llm = llm_client.get_llm
from src.retrieval import search_reviews
from src.memory import ConversationMemory
from src.sql_agent import run_sql_agent
import re

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

_GREETING_RE = re.compile(r"^(?:hi|hello|hey|good (?:morning|afternoon|evening))\b", re.IGNORECASE)
_INTRODUCTION_RE = re.compile(r"^(?:my name is|i am|i'm)\s+([A-Za-z][A-Za-z'-]{0,30})\b", re.IGNORECASE)


def _conversation_response(question: str, memory: ConversationMemory = None) -> str | None:
    normalized = question.strip()
    introduction = _INTRODUCTION_RE.match(normalized)
    if introduction:
        name = introduction.group(1)
        if memory:
            memory.user_name = name
        return f"Nice to meet you, {name}. Ask me about Olist orders, payments, deliveries, sellers, or customer reviews."

    if _GREETING_RE.match(normalized):
        name = getattr(memory, "user_name", None) if memory else None
        return f"Hello{', ' + name if name else ''}! I can help with Olist order analytics and customer-review themes."

    lowered = normalized.lower()
    project_help = (
        lowered in {"help", "what can you do?", "what can you do"}
        or "what can this chatbot" in lowered
        or "about this project" in lowered
        or "what data" in lowered
    )
    if project_help:
        return (
            "This chatbot answers questions about historical Olist Brazilian e-commerce data from 2016–2018. "
            "Ask for order, payment, delivery, seller, product, or customer-review insights; it cannot provide live data, "
            "profit margins, or facts outside this dataset."
        )
    return None


def rewrite_question(question: str, memory: ConversationMemory = None, provider: str = None) -> str:
    """
    Rewrites a follow‑up question into a standalone question using the conversation history.
    If the LLM call fails (e.g., rate limit), returns the original question unchanged.
    """
    if not memory:
        return question
    
    history = memory.format_for_prompt()
    if not history:
        return question
    
    llm = llm_client.get_llm(provider)
    prompt = _REWRITE_PROMPT.format(history=history, question=question)
    try:
        rewritten = llm.invoke(prompt).content.strip()
    except Exception as e:
        print(f"[orchestrator] rewrite_question LLM error ({type(e).__name__}): {e}. Using original question.")
        return question
    return rewritten


def classify_question(question: str, provider: str = None) -> str:
    """
    Classifies the user's question into 'sql', 'reviews', or 'both'.
    Falls back to 'sql' on unexpected output or LLM errors (e.g., rate limits).
    """
    # Quick intent gate for sentiment questions
    lowered = question.lower()
    if any(tok in lowered for tok in ["sentiment", "feel", "opinion", "review"]):
        return "reviews"
    llm = llm_client.get_llm(provider)
    prompt = _CLASSIFY_PROMPT.format(question=question)
    try:
        raw = llm.invoke(prompt).content.strip().lower()
    except Exception as e:
        # Log the error and fallback safely
        print(f"[orchestrator] classify_question LLM error ({type(e).__name__}): {e}. Falling back to 'sql'.")
        return "sql"
    if raw in ("sql", "reviews", "both"):
        return raw
    print(f"[orchestrator] Unexpected classification '{raw}' — falling back to 'sql'.")
    return "sql"


def run_reviews_pipeline(question: str, k: int = 5):
    """
    Executes a semantic search over customer reviews.
    """
    return search_reviews(question, k=k)


def orchestrate(question: str, memory: ConversationMemory = None, provider: str = None) -> dict:
    """
    The single public entry point for the chatbot pipeline.
    Classifies the question and runs the corresponding pipelines.
    Always returns a dictionary describing the result.
    """
    conversational_response = _conversation_response(question, memory)
    if conversational_response:
        return {"route": "conversation", "message": conversational_response}

    contextualized_question = rewrite_question(question, memory, provider=provider)
    print(f"[orchestrator] Original: '{question}' -> Rewritten: '{contextualized_question}'")
    
    route = classify_question(contextualized_question, provider=provider)

    if route == "sql":
        try:
            agent_result = run_sql_agent(contextualized_question, memory=memory, provider=provider)

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
            agent_result = run_sql_agent(contextualized_question, memory=memory, provider=provider)
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
