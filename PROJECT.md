# Logistics & Order Intelligence Chatbot — Project Brief and Build Roadmap

This entire file is the context. There is no separate "prompt section" — if you
(a human or an AI coding assistant) are reading this, you now have everything
needed to work on this project correctly. Read this whole file before writing
or changing anything.

Building approach: brick by brick. AI helps explain and review. Yuvraj writes
and understands every file, function, and class himself. No handing over a
finished repo.

---

## 1. What this is

A chatbot that answers plain-English questions about real order, payment, and
delivery data by turning the question into SQL, running it safely, and
answering in words. Read-only. Never writes to the database.

**Dataset: real, not synthetic.** Using the Olist Brazilian E-Commerce public
dataset (Kaggle) — genuine anonymized order data from a real marketplace,
~100,000 orders, 2016–2018, 9 relational tables.

**Honest framing, worth stating plainly:** this is domestic Brazilian
e-commerce data, not literally cross-border export data. There is no free
dataset that gives real per-order international export/multi-currency data at
company level — real companies don't publish that; what's publicly available
is only country-level aggregate trade statistics, which is useless for a
project like this. So the honest framing is: a real sales & logistics
analytics chatbot, asking export-style questions (regional breakdowns,
delivery delays, payment behavior) against real data — not pretending it's
literally cross-border trade.

---

## 2. The dataset — Olist Brazilian E-Commerce

**Source:** https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
(9 CSV files)

**Known real tables (from public documentation — confirm exact column names
yourself once downloaded, in Brick/Phase 0; correct this list if anything
differs):**

| Table | What it holds |
|---|---|
| `olist_customers_dataset` | customer_id, customer_unique_id, zip prefix, city, state |
| `olist_orders_dataset` | order_id, customer_id, order_status, purchase/approved/delivered timestamps, estimated delivery date |
| `olist_order_items_dataset` | order_id, product_id, seller_id, price, freight_value |
| `olist_order_payments_dataset` | order_id, payment_type, payment_installments, payment_value |
| `olist_order_reviews_dataset` | review_id, order_id, review_score, comments, timestamps |
| `olist_products_dataset` | product_id, category, dimensions, weight |
| `olist_sellers_dataset` | seller_id, zip prefix, city, state |
| `olist_geolocation_dataset` | zip prefix, lat, lng, city, state |
| `product_category_name_translation` | category name → English translation |

**Known real categorical values, worth knowing before you start (still verify
yourself against the real CSVs in Phase 0 — don't take this as gospel):**
`order_status` includes `delivered`, `shipped`, `canceled` (single L, American
spelling — worth remembering exactly because assuming "cancelled" would be
precisely the bug `categorical_check.py` exists to catch), `unavailable`,
`invoiced`, `processing`, `created`, `approved`. `payment_type` includes
`credit_card`, `boleto`, `voucher`, `debit_card`.

**Real questions this dataset can actually answer** (use these as inspiration
for gold-set questions in Phase 4):
- Which product categories have the highest late-delivery rate?
- Which states have the longest average delivery time?
- Does delivery time correlate with review score?
- Which sellers have the most orders, and what's their average review score?
- What's the average freight value by product category?
- Which payment type is most common, and does it vary by region?

---

## 3. What already exists from earlier work, and what carries over

An earlier pass built and tested a pipeline against a fake synthetic database
(in an AI sandbox, before this project switched to real data). Here's what's
still usable:

| File | Status |
|---|---|
| `validator.py` (SQLGlot structure check, table allow-list, row cap) | **Logic carries over.** It doesn't care what data it's pointed at, only that queries are SELECT-only and touch allow-listed tables. Re-read it yourself, update the allow-list to the real Olist table names, don't just copy it blindly without understanding it again. |
| `execute.py` (read-only connection, repair loop mechanics) | **Logic carries over.** Same reasoning — re-read it, re-point the file path at the real database. |
| `generate_data.py` (synthetic data generator) | **Dead. Not needed.** |
| `schema_cards.yaml`, `glossary.yaml`, `examples.jsonl` | **Rebuild from scratch** against the real schema — the old ones describe tables that no longer exist. |
| `gold_set.jsonl`, `run_eval.py` | **Rebuild the test cases** against real, verified answers. The harness script's *shape* (run question → compare to expected result) is reusable. |

No LLM was ever actually connected in the earlier work — that part was fully
simulated with hand-written SQL standing in for LLM output. There is no prior
LLM integration to preserve or discard; Phase 5 below is genuinely the first
real attempt at that.

---

## 4. Hard rules (do not violate these regardless of what seems convenient)

1. Database connection is always opened **read-only**. No exceptions, not
   even "just for testing."
2. Every SQL query generated by the LLM must pass through `validator.py` and
   `categorical_check.py` before it's allowed to run. Never bypass this.
3. **LangChain is the chosen orchestration tool** — but specifically for
   prompt templates, few-shot example assembly, and the LLM call wrapper.
   Do **not** add LangGraph, autonomous multi-tool agents, or LangChain's
   own built-in SQL-agent toolkit (`create_sql_agent` / the agent-executor
   pattern) on top of it. An autonomous agent decides for itself when and how
   to query the database — that would bypass the custom
   validate → check → execute → repair chain, which is the actual safety
   mechanism here and needs to stay simple enough to audit line by line.
4. No new major dependency (vector DB, Postgres, Docker, etc.) without a
   specific reason tied to something that's actually broken at the current
   scale — see Section 9.
5. CLI interface first. No web UI unless Ankit sir specifically asks for one.
6. Build one brick/phase at a time. "Done" means built, understood, **and**
   tested — not just run once by hand.
7. Never claim something works without having actually run it. If something
   is untested, say so plainly.
8. Every real value used in a query (a status, a category, a payment type)
   must be checked against what actually exists in that column before
   trusting the query's result — see Phase 3. A wrong spelling of a real
   value throws no error, it just quietly returns the wrong rows or 0 rows.
   This is the single most important lesson carried over from the earlier
   synthetic-data work, and it must not be skipped this time.
9. `categorical_check.py` **flags and asks — it never auto-corrects.**
   Silently "fixing" a wrong value (e.g. rewriting `'cancelled'` to
   `'canceled'` on the model's behalf) would quietly recreate the exact
   silent-wrong-answer bug this check exists to prevent. Wrong values get
   surfaced, never guessed around.
10. Every AI session on this project reads `memory.md` first and appends an
    entry before finishing (Section 10).
11. **The LLM provider is chosen at runtime, not hard-coded.** `llm_client.py`
    exposes a single factory function (`get_llm(provider)`) that returns a
    LangChain chat model — `ChatGroq`, `ChatGoogleGenerativeAI`, or
    `ChatOllama` — depending on which provider was picked. `sql_agent.py` and
    `answer_synth.py` only ever call the object `get_llm()` returns; they must
    never import a specific provider class directly. That's what makes
    switching providers a zero-change-to-the-rest-of-the-pipeline operation.

---

## 5. Architecture

```
User question (plain English)
        ↓
Relevant schema cards + glossary + few-shot examples retrieved
        ↓
LangChain prompt template + LLM (provider picked at runtime: Groq, Gemini, or local Ollama — via llm_client.py's factory) generates SQL
        ↓
validator.py: SELECT-only? allow-listed tables only? (sqlglot AST check)
        ↓
categorical_check.py: do the literal values in the query actually exist?
        ↓
execute.py: run the query against the read-only database
        ↓
  (if it errors) → feed the error back, retry, max 2 attempts
        ↓
answer_synth.py: LLM turns the raw result rows into a plain-English answer
        ↓
Answer shown to the user
```

---

## 6. File and folder structure

```
logistics_chatbot/
├── data/
│   ├── raw/                        # the 9 Olist CSVs, downloaded from Kaggle
│   └── olist.db                    # built from the CSVs yourself, Phase 0
├── semantic/
│   ├── schema_cards.yaml           # rebuilt against the real schema
│   ├── glossary.yaml               # rebuilt
│   └── examples.jsonl              # rebuilt
├── src/
│   ├── build_db.py                 # loads the 9 CSVs into olist.db
│   ├── validator.py                # carried over, allow-list updated
│   ├── execute.py                  # carried over, path updated
│   ├── categorical_check.py        # checks literal values against real distinct values
│   ├── llm_client.py               # get_llm(provider) factory — Groq / Gemini / Ollama, picked at runtime
│   ├── sql_agent.py                # question → prompt → LLM → validate → check → execute → repair
│   ├── answer_synth.py             # result rows → plain-English answer
│   └── chat_cli.py                 # terminal chat loop
├── tests/
│   ├── test_validator.py
│   ├── test_categorical_check.py
│   └── test_sql_agent.py
├── eval/
│   ├── gold_set.jsonl              # real, verified questions + answers
│   └── run_eval.py                 # harness, reused shape, new data
├── memory.md
├── requirements.txt
└── README.md
```

---

## 7. Build order — one phase at a time

Each phase: **build it**, **understand it** (why, in plain language), **test
it** before moving on. YouTube topics are listed inline exactly where a new
concept first shows up — search that phrase, watch with the specific angle
noted, then come back and build.

### Phase 0 — Get the real data and build the database yourself
- [ ] Download "Brazilian E-Commerce Public Dataset by Olist" from Kaggle (9 CSVs) into `data/raw/`
- [ ] Load each CSV in pandas, run `.info()` and `.head()` on all 9 — confirm real column names against Section 2's table, fix any mismatches you find
- [ ] Write `build_db.py`: loads all 9 CSVs into one `olist.db` SQLite file, one table per CSV
- [ ] For `order_status`, `payment_type`, `customer_state`, `seller_state`, `product_category_name`: run `SELECT DISTINCT` yourself and write down the real values. **This is the ground truth `categorical_check.py` uses later** — see it with your own eyes now, don't rely on Section 2's list.
- 📺 **"pandas read_csv tutorial"** — loading and inspecting CSVs
- 📺 **"sqlite3 python create table from csv"** — getting the CSVs into one database file
- 📺 *(if SQL itself is rusty)* **"SQL SELECT WHERE GROUP BY JOIN tutorial"**

**Test:** write and run 5 plain SQL queries yourself, by hand, no AI involved,
against your new `olist.db`. If you can't do this confidently, stay here —
everything later depends on you actually knowing this data.

### Phase 1 — Semantic layer, written against the real schema
- [ ] Write `schema_cards.yaml` by hand: what each table is, what each column means, which tables safely join to which
- [ ] Write `glossary.yaml`: define your own business terms against this real data — e.g. "late delivery" = `order_delivered_customer_date > order_estimated_delivery_date` (decide and write down your own definitions)
- [ ] Write 10-15 few-shot `examples.jsonl` entries by hand, real column names, including 2 refusal examples (questions the data genuinely can't answer)
- 📺 **"YAML tutorial for beginners"**
- 📺 **"JSON Lines JSONL format explained"**

**Test:** run every one of your own example SQL queries against the real
database yourself and confirm the result makes sense before trusting it as a
"known good" example.

### Phase 2 — Re-point the safety layer at real data
- [ ] Bring in `validator.py`, update the table allow-list to the 9 real Olist table names — re-read the whole file, confirm you understand every check it performs
- [ ] Bring in `execute.py`, point it at `olist.db`
- [ ] Write `tests/test_validator.py`: DELETE, DROP, multi-statement injection, disallowed table, a valid multi-table join with a CTE, plus 2 attack cases you think of yourself
- 📺 **"python unittest or pytest basics"**
- 📺 **"abstract syntax tree parsing basics"** — what "reading the structure of code" means, since that's what sqlglot does instead of matching text
- 📺 **"SQL injection explained"** — what the allow-list is actually defending against

### Phase 3 — Categorical value check, against real messy data
- [ ] `categorical_check.py`: at startup, query the real distinct values you wrote down in Phase 0
- [ ] Given a generated query, pull out literal string values compared against those columns, check membership against the real list
- [ ] Unknown value → flag low-confidence, **never auto-correct** (Rule 9)
- [ ] `tests/test_categorical_check.py`: deliberately test a wrong spelling (e.g. `'cancelled'` vs the real `'canceled'`) and confirm it gets flagged, not silently accepted
- 📺 **"python sets and membership testing"** — genuinely the entire theory needed here

### Phase 4 — Gold test set, built and proven BEFORE any LLM is involved
- [ ] Hand-write 15-20 test questions against the real schema: normal questions, a wrong-table-name bug, a wrong-column-name bug, a DELETE attempt, an out-of-scope table attempt, an unanswerable question, at least 2 wrong-categorical-value cases
- [ ] Write `run_eval.py`, run it with hand-authored SQL standing in for the LLM — this proves the *harness itself* works before any model is involved, so a later low accuracy score can be traced to the model, not a broken test

**Test:** every hand-authored case should behave exactly as you intend. If the
harness has bugs, you want to find them now, not after adding an LLM into the mix.

### Phase 5 — Connect a real LLM through LangChain, provider-selectable at runtime
- [ ] Get a free API key for Groq **and** Gemini (both — the point of this phase is that either can be picked at runtime)
- [ ] Install Ollama locally, pull one small model (e.g. `qwen2.5:7b` or `phi4-mini`) for the local option
- [ ] Write `llm_client.py`: a single `get_llm(provider: str)` factory function that returns `ChatGroq`, `ChatGoogleGenerativeAI`, or `ChatOllama` depending on `provider` — text in, text out, identical interface regardless of which one is returned
- [ ] Add a `--provider` CLI flag (or a config value) so the provider is chosen when the chatbot starts, not hard-coded
- [ ] Build a LangChain `PromptTemplate`/`FewShotPromptTemplate` assembling: instructions + relevant schema cards + relevant glossary terms + 2-3 similar few-shot examples + the actual question — this stays identical regardless of provider
- [ ] Manually test: run the same question through all 3 providers via the `--provider` flag, confirm each one writes at least structurally sane SQL, and confirm `sql_agent.py` needed zero changes to do this
- 📺 **"LangChain Explained in 10 Minutes"** — quick overview of LangChain components and provider abstraction/LCEL; watch this first, it directly explains the pattern this phase depends on
- 📺 **"LangChain Full Crash Course"** — chains, prompt templates, model wrappers
- 📺 **"Ollama Masterclass 2026"** — **only**: Open vs Proprietary LLMs, Ollama CLI, Python API, LangChain integration. Skip: Tool Calling, Ollama Cloud, Desktop App, Advanced Agents
- 📺 **"Prompt Engineering Guide"** — few-shot and chain-of-thought sections, for building the `FewShotPromptTemplate`

### Phase 6 — Wire the full agent
- [ ] `sql_agent.py`: question → prompt template → LLM → `validator.py` → `categorical_check.py` → `execute.py` → repair (a plain Python `while` loop wrapping the LangChain call, max 2 retries — no LangGraph needed for this)
- [ ] `tests/test_sql_agent.py`: run Phase 4's gold set through the *real* pipeline this time
- [ ] Record real accuracy — how many of the 15-20 actually come back correct with a real model involved

### Phase 7 — Answer synthesis
- [ ] `answer_synth.py`: LangChain call taking the question + result rows, returning a plain sentence, not a raw table dump
- [ ] Decide and implement: what it says on an empty result, what it says when `categorical_check.py` flagged low-confidence, what it says when retries are exhausted

### Phase 8 — Interface
- [ ] `chat_cli.py`: terminal loop — type a question, get an answer, repeat
- 📺 **"python command line chat loop tutorial"**
- [ ] Streamlit/Gradio UI — only if Ankit sir specifically asks for a visual demo, same `sql_agent.py` underneath either way
- 📺 **"streamlit chatbot tutorial"** — only watch this if you actually reach this step

### Phase 9 — Full pass and handoff
- [ ] Run the complete gold set end-to-end with the real LLM, log accuracy and response time
- [ ] Write `requirements.txt` and a short, honest `README.md` (what it is, how to run it, what's tested, what isn't)
- [ ] Clean up leftover debug prints
- [ ] Demo to Ankit sir live: one normal question, one deliberately broken question, one wrong-categorical-value question, to show the safety layer working, not just the happy path

---

## 8. Good to know, not blocking anything

📺 **"LangChain vs LangGraph explained"** — so you can explain why you used one and not the other, if asked in review.
📺 **"retrieval augmented generation vs fine-tuning explained"** — so you can explain why this hands the model relevant text at question-time instead of retraining a model.
📺 **"SQLite vs Postgres for small projects"** — so you can explain why SQLite was the right call here, not just "because it was easy."

---

## 9. What NOT to add (checked deliberately, not by default)

- No vector database / embedding search — 9 tables and ~15 examples fit
  directly in a prompt. Add this only if the semantic layer genuinely stops
  fitting in context, not preemptively.
- No LangGraph or autonomous multi-tool agents on top of LangChain — the
  repair loop is a bounded 2-try `while` loop, that's the whole "graph" this
  project needs.
- No web UI until Ankit sir asks.
- No Postgres/Docker — a SQLite file plus local Python is the right scale.
- No fuzzy auto-correction in `categorical_check.py` — flag and ask, never
  silently guess-fix a value. Auto-correcting would quietly recreate the exact
  bug this check exists to prevent.
- Don't import `ChatGroq`/`ChatGoogleGenerativeAI`/`ChatOllama` anywhere
  outside `llm_client.py`. The whole point of the factory is that
  `sql_agent.py` and `answer_synth.py` never know which provider they're
  talking to — hard-coding a provider anywhere else defeats it.
- Don't build a fancy plugin/registry system for providers — a factory
  function with an if/elif over 3 known provider names is enough at this
  scale. Add a 4th provider the same way if one ever comes up.

---

## 10. `memory.md` — running log across every AI tool used

Every time any AI tool (this conversation, Claude Code, Cursor, Codex,
Antigravity, anything) is used on this project, add a short dated entry.
Newest entries at the top. A few lines each — what was worked on, what
happened, anything worth remembering (dead ends, gotchas). Read this file
before starting any new session; append an entry before finishing one.

```
# Project Memory Log

Newest entries at the top. A few lines each.

---

## [DATE] — [Tool used]
**Phase:** which one
**Result:** what got built/fixed
**Worth remembering:** anything a future session should know before continuing
```

---

## 11. What is genuinely still undecided

- **Which provider performs best for this task** (Groq vs Gemini vs local
  Ollama) — the architecture supports all three interchangeably (Rule 11,
  Section 5), but which one is fastest/most accurate here is still an open
  empirical question, to be answered in Phase 5/6, not assumed.
- **Whether a web interface is needed at all** — default is no, CLI only,
  unless Ankit sir specifically asks.
- **Exact real column/value names** — confirm in Phase 0, don't trust
  Section 2 blindly.

Nothing else in this document should be treated as flexible without a good
reason — it reflects deliberate choices, not defaults left unquestioned.
