"""
semantic_loader.py
--------------------
Utility functions for loading the semantic layer files.
"""

import yaml
import json
import os

SEMANTIC_DIR = os.path.join(os.path.dirname(__file__), "..", "semantic")

def load_schema_cards():
    """Loads schema_cards.yaml into a Python dict."""
    path = os.path.join(SEMANTIC_DIR, "schema_cards.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_glossary():
    """Loads glossary.yaml into a Python dict."""
    path = os.path.join(SEMANTIC_DIR, "glossary.yaml")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def load_examples():
    """Loads examples.jsonl into a list of dicts."""
    path = os.path.join(SEMANTIC_DIR, "examples.jsonl")
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            examples.append(json.loads(line))
    return examples