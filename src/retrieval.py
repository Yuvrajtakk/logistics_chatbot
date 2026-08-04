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
import sqlite3


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

# Separate model for the "reviews" collection only -- decided in memory.md's
# 2026-08-04 entry after 4 rounds of testing. nomic-embed-text stays for
# "context" (English YAML/JSONL, no cross-lingual problem there).
REVIEWS_EMBEDDING_MODEL = "qwen3-embedding:0.6b"

# Same "step out of src/, into data/" pattern used everywhere else
# (execute.py's DB_PATH, categorical_check.py's default db_path).
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

# Hard cap on k for search_reviews() (and a safe default for search_context()
# too, though context collection is small). Chroma passes k straight through
# to SQLite's query planner as a variable list; SQLite's default maximum is
# 32,766 variables. Even k == collection_size (~41k) crashes. 16,383 is half
# that limit, giving safe headroom regardless of Chroma's per-result
# accounting. No real semantic search use case needs more than this.
_MAX_SEARCH_K = 16_383



def get_embeddings():
    """
    One shared way to get the embedding model, same spirit as
    get_llm() in llm_client.py -- a single place that knows how to
    build it, so nothing else has to know the model name.
    """
    return OllamaEmbeddings(model=EMBEDDING_MODEL)

def get_review_embeddings():
    """
    Same shape as get_embeddings(), pointed at the multilingual model
    instead. Kept as a separate function (not a parameter on
    get_embeddings()) so it's obvious at a glance which model backs
    which collection -- no risk of accidentally mixing them.
    """
    return OllamaEmbeddings(model=REVIEWS_EMBEDDING_MODEL)


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

def load_review_texts():
    """
    Pulls every non-null review_comment_message from the real database
    -- the full ~41k corpus, not a sample (the scratch tests were
    samples on purpose; this is the real build).

    Returns a list of (review_id, message) tuples. review_id becomes
    the Chroma card ID later, so re-running this function overwrites
    the same cards instead of duplicating them -- same safe-to-rerun
    pattern as build_context_collection().
    """
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT review_id, review_comment_message
        FROM olist_order_reviews_dataset
        WHERE review_comment_message IS NOT NULL
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def build_reviews_collection(batch_size: int = 200):
    """
    Same job as before, but embeds in small batches instead of one
    giant 41k-text call. The earlier crash (Ollama connection refused
    mid-request) was almost certainly Ollama's embedding batching
    choking on one huge request, not a real bug in our code or a
    broken model -- single-call tests worked fine.

    batch_size=200: small enough that one failed batch doesn't lose
    much progress, large enough that we're not paying per-call
    overhead 41,000 times. Not scientifically tuned -- a reasonable
    starting point, adjust if it's still unstable.
    """
    review_rows = load_review_texts()

    texts = [message for review_id, message in review_rows]
    ids = [f"review-{review_id}" for review_id, message in review_rows]
    metadatas = [{"source": "review", "review_id": review_id} for review_id, message in review_rows]

    total = len(texts)
    print(f"Building 'reviews' collection: {total} real review comments, in batches of {batch_size}...")

    # Create the (empty) collection once, up front. We build it by
    # repeatedly calling add_texts() on THIS SAME vectorstore object,
    # instead of from_texts() which tries to do everything in one call.
    vectorstore = Chroma(
        collection_name="reviews",
        embedding_function=get_review_embeddings(),
        persist_directory=CHROMA_DIR,
    )

    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        batch_texts = texts[start:end]
        batch_ids = ids[start:end]
        batch_metadatas = metadatas[start:end]

        try:
            vectorstore.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids,
            )
        except Exception as e:
            # If a batch fails, tell us exactly which range failed so
            # we can investigate or resume from there -- not just a
            # dead traceback with no idea how far we got.
            print(f"FAILED at batch {start}-{end}: {e}")
            raise

        print(f"  embedded {end}/{total}")

    print(f"Built 'reviews' collection: {total} real review comments embedded.")
    return vectorstore

def search_reviews(question: str, k: int = 5):
    """
    Given a plain-English question (e.g. "was delivery late?"), returns
    the k most semantically relevant real review comments.

    Same re-open-don't-rebuild pattern as search_context() -- connects
    to the already-built "reviews" collection on disk, doesn't redo
    the 41k-embedding build every call.

    k is capped at _MAX_SEARCH_K before querying. Chroma passes k
    straight through to SQLite as a variable list; when k exceeds
    SQLite's SQLITE_MAX_VARIABLE_NUMBER (default 32,766) the query
    throws InternalError. Even k == collection_size (~41k) crashes,
    so capping against collection_size alone is not enough -- we need
    a hard ceiling below the SQLite limit.
    """
    vectorstore = Chroma(
        collection_name="reviews",
        embedding_function=get_review_embeddings(),
        persist_directory=CHROMA_DIR,
    )

    k = min(k, _MAX_SEARCH_K)
    results = vectorstore.similarity_search(question, k=k)
    return results

