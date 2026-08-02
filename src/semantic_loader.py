"""
semantic_loader.py
--------------------
The three functions that read the raw semantic layer files
(schema_cards.yaml, glossary.yaml, examples.jsonl) off disk.

Why this file exists on its own, instead of living inside
prompt_builder.py where it started: BOTH prompt_builder.py and
retrieval.py need to read these same files. If prompt_builder.py kept
the loaders and retrieval.py imported them from there, then
prompt_builder.py needing search_context() back FROM retrieval.py
would create a circular import -- two files each needing something
from the other, at the same time, which Python cannot resolve.
Pulling the shared reading logic out here means neither file needs
anything from the other anymore.
"""

import yaml
import json
import os

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
    """Loads examples.jsonl into a list of {"question":..., "sql":...} dicts."""
    path = os.path.join(SEMANTIC_DIR, "examples.jsonl")
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            examples.append(json.loads(line))
    return examples