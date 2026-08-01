# yaml reads .yaml files into Python dicts — same library check_yaml.py
# already uses, nothing new here.
import yaml

# json reads .jsonl files one line at a time (each line is its own
# independent JSON object) — same pattern as check_jsonl.py.
import json

# os.path lets this file find semantic/ correctly regardless of which
# folder you're standing in when you run it — same trick used in
# execute.py for finding olist.db.
import os

# Build a path to the semantic/ folder that works no matter where this
# script is run from: go up one level from src/, then into semantic/.
SEMANTIC_DIR = os.path.join(os.path.dirname(__file__), "..", "semantic")


def load_schema_cards():
    """Loads schema_cards.yaml into a Python dict: {table_name: {...}}"""
    path = os.path.join(SEMANTIC_DIR, "schema_cards.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_glossary():
    """Loads glossary.yaml into a Python dict: {term_name: {...}}"""
    path = os.path.join(SEMANTIC_DIR, "glossary.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_examples():
    """
    Loads examples.jsonl into a list of dicts:
    [{"question": ..., "sql": ...}, {"question": ..., "sql": ...}, ...]
    One json.loads() call per line, same as check_jsonl.py already does.
    """
    path = os.path.join(SEMANTIC_DIR, "examples.jsonl")
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            examples.append(json.loads(line))
    return examples

def format_schema_cards(schema_cards: dict) -> str:
    """
    Turns the schema_cards dict into plain text describing every table
    and column — this is the "seating chart" from the lunch-box analogy.
    """
    lines = []
    for table_name, table_info in schema_cards.items():
        lines.append(f"TABLE: {table_name}")
        lines.append(f"  {table_info['description'].strip()}")
        for col_name, col_info in table_info["columns"].items():
            lines.append(f"  - {col_name} ({col_info['type']}): {col_info['description'].strip()}")
        lines.append("")  # blank line between tables, easier to read
    return "\n".join(lines)


def format_glossary(glossary: dict) -> str:
    """
    Turns the glossary dict into plain text business-term definitions —
    the "classroom rules" piece. sql_logic is included so the LLM sees
    the EXACT expression to use, not just the plain-English idea.
    """
    lines = []
    for term_name, term_info in glossary.items():
        lines.append(f"TERM: {term_name}")
        lines.append(f"  Definition: {term_info['definition'].strip()}")
        lines.append(f"  SQL logic: {term_info['sql_logic'].strip()}")
        lines.append("")
    return "\n".join(lines)


def format_examples(examples: list) -> str:
    """
    Turns the examples list into plain text Q -> SQL pairs — the
    "worked problems on the board" piece. Refusal examples (sql starts
    with "REFUSE:") are included as-is, teaching the LLM by example
    that refusing is sometimes the CORRECT answer, not a failure.
    """
    lines = []
    for ex in examples:
        lines.append(f"Q: {ex['question']}")
        lines.append(f"SQL: {ex['sql']}")
        lines.append("")
    return "\n".join(lines)

def build_prompt(question: str) -> str:
    """
    The single entry point this whole file exists for. Takes the
    user's plain-English question, returns one complete prompt string
    ready to hand straight to an LLM via get_llm().invoke(prompt).
    """
    schema_cards = load_schema_cards()
    glossary = load_glossary()
    examples = load_examples()

    # A short, direct instruction block up front — LLMs follow
    # explicit rules stated plainly far more reliably than rules left
    # implied by the examples alone.
    instructions = (
        "You are a SQL generator for a read-only SQLite database about "
        "Brazilian e-commerce orders (the Olist dataset). Given a plain-"
        "English question, respond with ONLY a single SELECT SQL query "
        "— no explanation, no markdown formatting, no semicolon-separated "
        "extra statements. If the question genuinely cannot be answered "
        "with this data, respond with exactly: REFUSE: <one clear reason>"
    )

    # f-string assembly: every piece gets its own labeled section, in
    # the same order every time, so the LLM always sees the same shape
    # of prompt regardless of which question comes in.
    prompt = (
        f"{instructions}\n\n"
        f"=== SCHEMA ===\n{format_schema_cards(schema_cards)}\n"
        f"=== GLOSSARY ===\n{format_glossary(glossary)}\n"
        f"=== EXAMPLES ===\n{format_examples(examples)}\n"
        f"=== QUESTION ===\n{question}\n"
        f"SQL:"
    )

    return prompt