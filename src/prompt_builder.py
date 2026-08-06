"""
prompt_builder.py
------------------
Assembles the full prompt handed to the LLM for SQL generation.
Pulls relevant context (schema, examples) and conversation memory.
"""

from src.semantic_loader import load_examples, load_glossary, load_schema_cards


def _fallback_context() -> tuple[list[str], list[str]]:
    """Build deterministic context when the optional local vector store is absent."""
    schema_snippets = []
    for table_name, table_info in load_schema_cards().items():
        columns = ", ".join(table_info["columns"].keys())
        schema_snippets.append(f"TABLE: {table_name}\n  {table_info['description'].strip()}\n  COLUMNS: {columns}")

    example_snippets = [f"Q: {example['question']}\nSQL: {example['sql']}" for example in load_examples()]
    return schema_snippets, example_snippets

def format_glossary(glossary: dict) -> str:
    """
    Turns the glossary dict into plain text business-term definitions.
    """
    lines = []
    for term_name, term_info in glossary.items():
        lines.append(f"TERM: {term_name}")
        lines.append(f"  Definition: {term_info['definition'].strip()}")
        lines.append(f"  SQL logic: {term_info['sql_logic'].strip()}")
        lines.append("")
    return "\n".join(lines)


def build_prompt(question: str, memory=None) -> str:
    """
    Builds the complete SQL generation prompt containing instructions,
    relevant schema tables, glossary terms, few-shot examples, and recent memory.

    Args:
        question (str): The user's input question.
        memory (ConversationMemory, optional): Multi-turn context.

    Returns:
        str: The full prompt string.
    """
    try:
        from src.retrieval import search_context

        results = search_context(question, k=5)
        schema_snippets = [r.page_content for r in results if r.metadata.get("source") == "schema"]
        example_snippets = [r.page_content for r in results if r.metadata.get("source") == "example"]
    except Exception as error:
        print(f"[prompt_builder] Vector context unavailable; using static context: {type(error).__name__}")
        schema_snippets, example_snippets = _fallback_context()

    glossary = load_glossary()

    instructions = (
        "You are a SQL generator for a read-only SQLite database about "
        "Brazilian e-commerce orders (the Olist dataset). Given a plain-"
        "English question, respond with ONLY a single SELECT SQL query "
        "— no explanation, no markdown formatting, no semicolon-separated "
        "extra statements. If the question genuinely cannot be answered "
        "with this data, respond with exactly: REFUSE: <one clear reason>"
    )

    parts = [instructions, ""]

    parts.append("=== RELEVANT SCHEMA (top matches for this question) ===")
    parts.append("\n\n".join(schema_snippets) if schema_snippets else "(no closely matching table found)")
    parts.append("")

    parts.append("=== GLOSSARY ===")
    parts.append(format_glossary(glossary))

    parts.append("=== SIMILAR EXAMPLES ===")
    parts.append("\n\n".join(example_snippets) if example_snippets else "(no closely matching example found)")
    parts.append("")

    recent_conversation = memory.format_for_prompt() if memory else ""
    if recent_conversation:
        parts.append("=== RECENT CONVERSATION ===")
        parts.append(recent_conversation)

    parts.append("=== QUESTION ===")
    parts.append(question)
    parts.append("SQL:")

    return "\n".join(parts)
