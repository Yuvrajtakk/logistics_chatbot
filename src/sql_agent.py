"""
sql_agent.py
------------
Phase 6: The complete SQL pipeline for a single question.
"""

import os

from src.llm_client import get_llm
from src.prompt_builder import build_prompt
from src.validator import validate_sql, ValidationError
from src.categorical_check import load_real_values, check_categoricals
from src.execute import run_with_repair, ExecutionError
from src.memory import ConversationMemory

_real_values = None

def _get_real_values() -> dict:
    """
    Returns the cached categorical ground-truth values dictionary, loading
    it from the database on the first call.
    """
    global _real_values
    if _real_values is None:
        _real_values = load_real_values()
    return _real_values


def run_sql_agent(question: str, memory: ConversationMemory = None) -> dict:
    """
    Runs the full SQL pipeline for a single question.
    
    Args:
        question (str): The plain-English question.
        memory (ConversationMemory, optional): Multi-turn context memory.
        
    Returns:
        dict: A status dictionary containing the execution result, refusal,
              categorical flag details, or an error.
    """
    try:
        llm = get_llm()
        prompt = build_prompt(question, memory=memory)
        raw_sql = llm.invoke(prompt).content.strip()

        if raw_sql.upper().startswith("REFUSE:"):
            return {
                "status": "refused",
                "sql": None,
                "reason": raw_sql,
            }

        try:
            validated_sql = validate_sql(raw_sql)
        except ValidationError as e:
            return {
                "status": "error",
                "sql": raw_sql,
                "error": "ValidationError",
                "detail": str(e),
            }

        real_values = _get_real_values()
        cat_result = check_categoricals(validated_sql, real_values)

        if not cat_result["ok"]:
            return {
                "status": "flagged",
                "sql": validated_sql,
                "problems": cat_result["problems"],
                "suggestions": cat_result["suggestions"],
            }

        def regenerate_fn(failed_sql: str, error_message: str) -> str:
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
                "sql": validated_sql,
                "columns": columns,
                "rows": rows,
            }
        except (ValidationError, ExecutionError) as e:
            return {
                "status": "error",
                "sql": validated_sql,
                "error": type(e).__name__,
                "detail": str(e),
            }

    except Exception as e:
        print(f"[sql_agent] Unexpected error: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "sql": None,
            "error": type(e).__name__,
            "detail": str(e),
        }
