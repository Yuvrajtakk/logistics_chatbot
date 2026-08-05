"""
retrieval.py
------------
Phase 5.5a & 5.5b: Vector search over the semantic layer and customer reviews.
Provides functions to build and search Chroma collections.
"""

import os
import sqlite3
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from src.semantic_loader import load_schema_cards, load_examples

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
EMBEDDING_MODEL = "nomic-embed-text"
REVIEWS_EMBEDDING_MODEL = "qwen3-embedding:0.6b"
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "olist.db")

_MAX_SEARCH_K = 16_383


def get_embeddings():
    """Returns the embedding model used for the context collection."""
    return OllamaEmbeddings(model=EMBEDDING_MODEL)


def get_review_embeddings():
    """Returns the embedding model used for the reviews collection."""
    return OllamaEmbeddings(model=REVIEWS_EMBEDDING_MODEL)


def build_context_collection():
    """
    Builds the 'context' Chroma collection containing schema cards and examples.
    """
    schema_cards = load_schema_cards()
    examples = load_examples()

    texts = []
    metadatas = []
    ids = []

    for table_name, table_info in schema_cards.items():
        lines = [f"TABLE: {table_name}", f"  {table_info['description'].strip()}"]
        for col_name, col_info in table_info["columns"].items():
            lines.append(f"  - {col_name} ({col_info['type']}): {col_info['description'].strip()}")
        card_text = "\n".join(lines)

        texts.append(card_text)
        metadatas.append({"source": "schema", "table": table_name})
        ids.append(f"schema-{table_name}")

    for i, ex in enumerate(examples):
        card_text = f"Q: {ex['question']}\nSQL: {ex['sql']}"

        texts.append(card_text)
        metadatas.append({"source": "example", "question": ex["question"]})
        ids.append(f"example-{i}")

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
    Retrieves the k most relevant context cards for a given question.
    """
    vectorstore = Chroma(
        collection_name="context",
        embedding_function=get_embeddings(),
        persist_directory=CHROMA_DIR,
    )
    return vectorstore.similarity_search(question, k=k)


def load_review_texts():
    """
    Retrieves all non-null customer reviews from the database.
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
    Builds the 'reviews' Chroma collection in batches.
    """
    review_rows = load_review_texts()

    texts = [message for review_id, message in review_rows]
    ids = [f"review-{review_id}" for review_id, message in review_rows]
    metadatas = [{"source": "review", "review_id": review_id} for review_id, message in review_rows]

    total = len(texts)
    print(f"Building 'reviews' collection: {total} real review comments, in batches of {batch_size}...")

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
            print(f"FAILED at batch {start}-{end}: {e}")
            raise
        print(f"  embedded {end}/{total}")

    print(f"Built 'reviews' collection: {total} real review comments embedded.")
    return vectorstore


def search_reviews(question: str, k: int = 5):
    """
    Retrieves the k most relevant customer reviews for a given question.
    """
    vectorstore = Chroma(
        collection_name="reviews",
        embedding_function=get_review_embeddings(),
        persist_directory=CHROMA_DIR,
    )
    k = min(k, _MAX_SEARCH_K)
    return vectorstore.similarity_search(question, k=k)
