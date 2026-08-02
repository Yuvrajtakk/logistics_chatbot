"""
retrieval.py
------------
Phase 5.5a: vector search over the semantic layer, so prompt_builder.py
can hand the LLM only the RELEVANT schema tables and examples for a
given question, instead of the entire manifest every single time.

Two Chroma collections live in data/chroma_db/ (gitignored, rebuilt
from source files any time -- it's a cache, not a source of truth):
    "context" -- built in this phase (5.5a): schema tables + examples
    "reviews" -- built later (5.5b): customer review text

This file owns the "context" collection only. The "reviews" collection
gets its own build function in Phase 5.5b, once we've tested whether
nomic-embed-text handles Portuguese well enough (open question, see
PROJECT.md).
"""

import os

# Chroma's LangChain wrapper -- the actual vector database.
from langchain_chroma import Chroma

# Same package that already gives us ChatOllama in llm_client.py --
# OllamaEmbeddings is the embedding-model equivalent: text in,
# vector out, talking to the same local Ollama service.
from langchain_ollama import OllamaEmbeddings

# Reuse the loader functions already written and tested in
# prompt_builder.py -- no need to re-read the YAML/JSONL files a
# second way. This file only reshapes their output into individual
# Chroma "cards" instead of one giant formatted string.
from src.semantic_loader import load_schema_cards, load_examples

# Where the Chroma database file lives on disk. Same "step out of src/,
# into a sibling folder" pattern already used for SEMANTIC_DIR in
# prompt_builder.py and DB_PATH in execute.py.
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")

# Must match exactly what you pulled: `ollama pull nomic-embed-text`.
EMBEDDING_MODEL = "nomic-embed-text"


def get_embeddings():
    """
    One shared way to get the embedding model, same spirit as
    get_llm() in llm_client.py -- a single place that knows how to
    build it, so nothing else has to know the model name.
    """
    return OllamaEmbeddings(model=EMBEDDING_MODEL)


def build_context_collection():
    """
    Reads schema_cards.yaml and examples.jsonl, turns each table and
    each example into its own separate "card" (a LangChain Document-
    like dict: text + metadata), embeds all of them, and stores them
    in a Chroma collection called "context" on disk at CHROMA_DIR.

    Safe to re-run any time the semantic layer changes -- Chroma's
    from_texts() with the same collection name will add to what's
    already there, so we explicitly wipe and rebuild for a clean,
    predictable result instead of silently accumulating duplicates.
    """
    schema_cards = load_schema_cards()
    examples = load_examples()

    # texts: the actual strings that get embedded (turned into vectors).
    # metadatas: extra info stored ALONGSIDE each vector, not embedded
    #   itself -- lets us later know "this result came from a schema
    #   table" vs "this result came from an example", and which one.
    # ids: a unique string per card, so re-running this function
    #   overwrites the same cards instead of duplicating them.
    texts = []
    metadatas = []
    ids = []

    # ---- One card per schema table ----
    for table_name, table_info in schema_cards.items():
        # Build the same per-table text block format_schema_cards()
        # already produces for one table, just for this table alone.
        lines = [f"TABLE: {table_name}", f"  {table_info['description'].strip()}"]
        for col_name, col_info in table_info["columns"].items():
            lines.append(f"  - {col_name} ({col_info['type']}): {col_info['description'].strip()}")
        card_text = "\n".join(lines)

        texts.append(card_text)
        metadatas.append({"source": "schema", "table": table_name})
        ids.append(f"schema-{table_name}")

    # ---- One card per example question+SQL pair ----
    for i, ex in enumerate(examples):
        card_text = f"Q: {ex['question']}\nSQL: {ex['sql']}"

        texts.append(card_text)
        metadatas.append({"source": "example", "question": ex["question"]})
        ids.append(f"example-{i}")

    # Build (or overwrite) the "context" collection from scratch.
    # Chroma.from_texts() handles embedding every text in `texts`
    # itself -- we never call the embedding model by hand.
    vectorstore = Chroma.from_texts(
        texts=texts,
        embedding=get_embeddings(),
        metadatas=metadatas,
        ids=ids,
        collection_name="context",
        persist_directory=CHROMA_DIR,
    )

    print(f"Built 'context' collection: {len(schema_cards)} schema cards + {len(examples)} examples = {len(texts)} total cards.")
    return vectorstore

def search_context(question: str, k: int = 3):
    """
    Given a plain-English question, returns the k most relevant cards
    from the "context" collection -- a mix of schema tables and
    examples, whichever are closest in MEANING to the question.

    This is what prompt_builder.py will call later, instead of
    dumping the entire schema + all 15 examples into every prompt.

    Returns a list of LangChain Document objects. Each one has:
        .page_content -- the actual card text (what we embedded)
        .metadata     -- the extra info we stored alongside it
                          (source: "schema" or "example", etc.)
    """
    # Re-open the SAME on-disk collection we already built --
    # we are NOT rebuilding it here, just connecting to what's there.
    vectorstore = Chroma(
        collection_name="context",
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )

    # similarity_search embeds the question the same way every card
    # was embedded, then returns the k closest cards by vector distance.
    results = vectorstore.similarity_search(question, k=k)
    return results