# Logistics & Order Intelligence Chatbot

A plain-English terminal chatbot designed to answer logistical and sales questions against the real Brazilian E-Commerce public dataset (Olist). It turns user questions into SQL, runs them safely against a local database, and synthesizes the data into human-readable answers. 

It features a dual-route architecture: answering structured data questions via SQL generation, and unstructured sentiment questions via semantic search (RAG) against ~41,000 real customer reviews.

## Architecture & Safety
This project deliberately avoids black-box autonomous agents (like LangGraph or LangChain's SQL Agent). Instead, it uses a deterministic pipeline with strict safety guarantees:
1. **Validator Check**: SQL is parsed into an AST via `sqlglot`. Only `SELECT` statements are allowed. Only 9 allow-listed tables can be queried. 
2. **Categorical Check**: Any string literal used in the query is verified against a ground-truth cache of real distinct values. The chatbot flags typos and offers fuzzy suggestions before running the query, preventing silent empty-result bugs.
3. **Read-Only Database**: SQLite is opened with `uri=True` and `mode=ro`, enforcing read-only access at the OS level.
4. **Repair Loop**: Execution errors are fed back to the LLM for a maximum of 2 retry attempts.

## How to Run

1. **Setup the Database**: 
   Download the Kaggle Olist dataset (9 CSV files) to `data/raw/` and run:
   ```bash
   python src/build_db.py
   ```
2. **Setup the Vector Store**: 
   Build the Chroma collections for context and reviews (requires Ollama running locally):
   ```bash
   python src/retrieval.py
   ```
3. **Setup the Environment**:
   Create a `.env` file in the root with your API keys:
   ```
   GROQ_API_KEY=your_key_here
   GOOGLE_API_KEY=your_key_here
   ```
4. **Start the Chatbot**:
   Run the terminal loop. By default, it uses Groq, but you can switch providers at runtime:
   ```bash
   python src/chat_cli.py
   python src/chat_cli.py --provider gemini
   python src/chat_cli.py --provider ollama
   ```

## What's Tested
- The SQL AST validation and read-only execution layers are thoroughly unit tested.
- The categorical value checker has been adversarially tested.
- A "Gold Set" of 18 questions (including bad categoricals, out-of-scope requests, and SQL injections) was hand-authored to empirically prove the end-to-end pipeline routes correctly and never raises an unhandled exception.

## What Isn't Tested
- The web UI (Streamlit/Gradio) is intentionally excluded per the project brief; this is a CLI-first tool.
- The system doesn't auto-correct bad categorical values; it only flags them and asks the user to rephrase (a deliberate choice to avoid guess-fixing).
