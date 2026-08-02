"""
prompt_builder.py
------------------
Assembles the full prompt handed to the LLM for SQL generation.

Phase 5.5a change: instead of dumping the ENTIRE schema and ALL 15
examples into every prompt, this now calls retrieval.py's
search_context() to pull only the top-k most RELEVANT schema tables
and examples for the specific question being asked. Glossary stays
included in full -- only 5 terms, small enough that retrieving a
subset would add complexity for no real savings (YAGNI).

Also new: an optional recent-conversation section, fed by memory.py's
ConversationMemory, so follow-up questions can be understood.
"""

from src.semantic_loader import load_glossary


def format_glossary(glossary: dict) -> str:
    """
    Turns the glossary dict into plain text business-term definitions.
    sql_logic is included so the LLM sees the EXACT expression to use,
    not just the plain-English idea.
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
    The single entry point this file exists for. Takes the user's
    plain-English question and returns one complete prompt string,
    ready to hand straight to an LLM via get_llm().invoke(prompt).

    question: the plain-English question.
    memory: an optional ConversationMemory instance (memory.py). If
        given and it already has turns in it, those recent turns are
        included so the LLM can understand follow-up questions like
        "what about payment type?" If None, or empty, this section is
        skipped entirely -- no pointless empty header in the prompt.
    """
    # Imported here rather than at the top of the file. retrieval.py
    # no longer imports anything from THIS file (it reads from
    # semantic_loader.py instead), so this import is safe at the top
    # too now -- but keeping it local here is a deliberate, harmless
    # habit while this refactor is fresh, to make the dependency
    # direction obvious at a glance without scrolling to the top.
    from src.retrieval import search_context

    # Pull the k=5 most relevant cards for THIS question -- a mix of
    # schema tables and examples, whichever are closest by meaning.
    results = search_context(question, k=5)

    # Split the mixed results back into two groups by their metadata
    # "source" tag, which build_context_collection() set when it
    # built the collection.
    schema_snippets = [r.page_content for r in results if r.metadata.get("source") == "schema"]
    example_snippets = [r.page_content for r in results if r.metadata.get("source") == "example"]

    glossary = load_glossary()

    instructions = (
        "You are a SQL generator for a read-only SQLite database about "
        "Brazilian e-commerce orders (the Olist dataset). Given a plain-"
        "English question, respond with ONLY a single SELECT SQL query "
        "— no explanation, no markdown formatting, no semicolon-separated "
        "extra statements. If the question genuinely cannot be answered "
        "with this data, respond with exactly: REFUSE: <one clear reason>"
    )

    # Building the prompt as a list of lines/blocks, joined at the end,
    # instead of one long f-string -- makes it easy to conditionally
    # skip the recent-conversation section without messy string logic.
    parts = [instructions, ""]

    parts.append("=== RELEVANT SCHEMA (top matches for this question) ===")
    parts.append("\n\n".join(schema_snippets) if schema_snippets else "(no closely matching table found)")
    parts.append("")

    parts.append("=== GLOSSARY ===")
    parts.append(format_glossary(glossary))

    parts.append("=== SIMILAR EXAMPLES ===")
    parts.append("\n\n".join(example_snippets) if example_snippets else "(no closely matching example found)")
    parts.append("")

    # Only add a recent-conversation section if there's actually
    # history to show -- format_for_prompt() returns "" if empty.
    recent_conversation = memory.format_for_prompt() if memory else ""
    if recent_conversation:
        parts.append("=== RECENT CONVERSATION ===")
        parts.append(recent_conversation)

    parts.append("=== QUESTION ===")
    parts.append(question)
    parts.append("SQL:")

    return "\n".join(parts)