# Project Memory Log

Newest entries at the top. A few lines each.

---
## 2026-08-05 — Antigravity
**Phase:** 7 — complete and fully tested
**Result:** Built `src/answer_synth.py` to synthesize the orchestrator's result dict into plain English. 
- Handles all four SQL statuses (ok, refused, flagged, error).
- Handles the `reviews` route via a dedicated summarization LLM call (prompted strictly to extract exactly one Portuguese quote + English translation). 
- Handles the `both` route by stitching the two paragraphs together. Total failure across both pipelines produces a clean unified fallback.
- Added 18 tests (normal + adversarial) proving string formatting, fallback on LLM timeout, gracefully handling malformed input, and the core "never raises" contract. All 18 passing.

**Design decisions deliberately made:**
- **Categorical flagging size cap:** If a bad value is flagged but no fuzzy suggestion exists, the code checks the valid set's size. If <= 10 (`order_status`, `payment_type`), it lists all valid options. If > 10 (`customer_state`, `product_category_name`, etc.), it just stops at "not recognized" to avoid dumping 70 values into a chat sentence.
- **No "Ask me to list values" hint:** Deferred adding a hint like "Ask me to list valid values" for large sets. We haven't verified that the pipeline can reliably answer that follow-up question (Rule 7: Never claim something works without having actually run it).
- **Never raises contract:** The top-level `synthesize_answer()` and the internal `_summarize_documents()` call both have safety-net `try/except` blocks. If the LLM throws a timeout or the dict is completely malformed, it falls back to a plain English error string instead of crashing `chat_cli.py`.

**Worth remembering:**
- The prompt explicitly enforces the quote formatting constraint at the LLM level. If we notice drifting formats later, it's model non-determinism, not missing instructions. 
- `_get_real_values` is imported from `sql_agent.py` to access the DB cache. Safe for now, since it only reads.

---
## 2026-08-05 — Antigravity
**Phase:** 6 — complete and fully tested
**Result:** Built `src/sql_agent.py` (the full SQL pipeline, correctly ordered),
patched `categorical_check.py`'s path bug, slimmed `orchestrator.py` to delegate
to `sql_agent`, and wrote both normal and adversarial test files. 82/82 tests
passing (was 69 before this session — added 13 new tests).

**What was built:**
- `src/sql_agent.py` (NEW): owns the complete pipeline in correct order:
  generate → REFUSE detection → validate_sql() → check_categoricals() →
  run_with_repair(). Four-status return dict: `"ok"` / `"refused"` /
  `"flagged"` / `"error"`. Every status carries a `"sql"` key (except
  `"refused"` which sets `"sql": None`). Module-level `_real_values` cache —
  `load_real_values()`'s five SELECT DISTINCT queries run once per process,
  not once per question.
- `src/categorical_check.py` patched: `load_real_values()`'s default
  `db_path` changed from bare `"data/olist.db"` (fragile, launch-dir-dependent)
  to `__file__`-relative path + `os.path.abspath()` — same pattern as
  execute.py and retrieval.py. Also added `import os`. One-line change,
  zero behavior change for existing callers.
- `src/orchestrator.py` updated: `run_sql_pipeline()` is now a thin shim
  that calls `run_sql_agent()` and translates the four-status dict back to
  tuple-or-raise for any legacy callers. `orchestrate()` now calls
  `run_sql_agent()` directly and surfaces all four statuses as proper dict
  keys (`"flagged": True`, `"refused": True`, etc.) instead of collapsing
  them all into a generic `"error"` key.
- `tests/test_sql_agent.py` (NEW): runs all 18 gold-set cases through the
  real pipeline. Asserts route correctness per case type, never exact SQL.
- `tests/test_sql_agent_adversarial.py` (NEW): cache mutation safety,
  JSON-serialization limitation confirmed empirically, memory parameter
  contract, state isolation across consecutive calls.

**Real accuracy — Phase 6 gold set (real LLM, first run ever):**
10/10 normal questions returned `status="ok"` with real data. 0 errors.
Bad-categorical cases correctly returned `"flagged"`. Unanswerable cases
correctly returned `"refused"`. Should-block cases correctly returned `"error"`.

**Architecture decision recorded (Option A/B/C):**
Option A (thin wrapper calling `run_sql_pipeline()`, check categoricals after)
was ruled out — categoricals must be checked BEFORE the query runs. The query
would silently return wrong rows for a bad categorical value with no error.
Option C chosen: `sql_agent.py` owns the full pipeline in the right order,
`orchestrator.py` becomes a pure dispatcher.

**Real bug found and fixed (same session, caught by adversarial test):**
`run_sql_agent()`'s "never raises" contract was broken: the outer `try/except`
only wrapped step 6 (execute+repair). Steps 1-5 — including the first
`llm.invoke()` call — were completely unprotected. When Groq's daily token
limit was hit during the full test suite run, `RateLimitError` propagated
straight to the caller instead of being caught and returned as an error dict.
Fix: wrapped the ENTIRE function body in a single outer `try/except Exception`,
keeping the inner try/excepts for ValidationError and ExecutionError as
early-return paths. Confirmed with a mock test: patching `get_llm` to throw
a fake exception now returns `{"status": "error", "error": "FakeLimitError", ...}`
instead of raising. The `test_run_sql_agent_never_raises` test caught this — this
is exactly why the adversarial "never raises" tests exist.

**Worth remembering:**
- `run_sql_pipeline()` in `orchestrator.py` had NO categorical check at all
  — the gap between Phase 5.5b and Phase 6 was real, not a documentation
  omission. `sql_agent.py` is the first place in this codebase where the
  full intended pipeline actually runs end-to-end in the correct order.
- The `_real_values` cache in `sql_agent.py` is a SHARED mutable object.
  Adversarial test confirms: a caller that writes to the returned dict
  mutates the cache for all future calls in the same process. Currently safe
  (only `sql_agent.py` touches it, read-only) — flag this if concurrent
  access or write-access ever comes up.
- `suggestions` dict in a `"flagged"` result uses `(column, value)` tuples
  as keys. `json.dumps()` raises `TypeError` on this. Empirically confirmed
  in `test_sql_agent_adversarial.py`. Must re-key to strings before any
  serialization in Phase 8/9.
- The two DeprecationWarnings in pytest output are from third-party packages
  (`google.genai.types`, `chromadb`), not our code. Not urgent, not ours
  to fix.

**Next up (Phase 7):**
`src/answer_synth.py` — takes the question + `run_sql_agent()`'s result dict
and returns a plain-English sentence. Must handle all four statuses:
  - `"ok"`: narrate the rows in words (not a raw table dump)
  - `"refused"`: explain why the question can't be answered
  - `"flagged"`: tell the user the specific bad value and the suggestion
  - `"error"`: tell the user what failed, without raw error messages

---
## 2026-08-04 — Claude (chat)
**Phase:** 5.5b — complete and fully tested
**Result:** Built, tested, and committed the reviews collection + orchestrator.
- `build_reviews_collection()` batched run completed cleanly: 40,977 real
  review comments embedded in batches of 200, no batch failures. VRAM was
  clear before starting (`ollama ps` confirmed).
- `src/retrieval.py` additions confirmed working: `get_review_embeddings()`
  (qwen3-embedding:0.6b), `load_review_texts()`, `build_reviews_collection()`,
  `search_reviews()`. Added `_MAX_SEARCH_K = 16_383` module constant (see bugs).
- `src/orchestrator.py` (NEW): `classify_question()` — one LLM call, returns
  "sql"/"reviews"/"both". `run_sql_pipeline()` — full SQL path with REFUSE
  detection. `run_reviews_pipeline()` — thin wrapper on `search_reviews()`.
  `orchestrate()` — public entry point, always returns a dict, never raises.
- `src/validator.py` patched: wrapped `sqlglot.parse_one()` in try/except
  so `ParseError` is always re-raised as `ValidationError` (see bugs).
- `scratch_embedding_test.py` deleted (was the last of 3 throwaway files).
- 69/69 tests passing after all fixes. Zero regressions.

**Real bugs found by tests this session (all fixed):**
1. `k > SQLITE_MAX_VARIABLE_NUMBER` crashes Chroma: `_collection.count()` is
   NOT a safe cap — the collection itself (~40,668) exceeds SQLite's ~32,766
   variable limit. Fix: `_MAX_SEARCH_K = 16_383` hard constant, half of
   SQLite's limit, well above any real search use case.
2. `validate_sql()` leaked `sqlglot.errors.ParseError` instead of the
   consistent `ValidationError` that all callers catch. Any non-SQL string
   (including REFUSE responses) silently bypassed all error handling. Fix:
   wrapped `parse_one()` in try/except, re-raise as `ValidationError`.
3. REFUSE responses from LLM were passed straight to `validate_sql()`: the
   prompt tells the LLM to return `REFUSE: <reason>` for unanswerable
   questions — it was doing exactly that, but the code then tried to parse
   it as SQL. Fix: check `raw_sql.upper().startswith("REFUSE:")` in
   `run_sql_pipeline()` before calling the validator.
4. Test assumption wrong — duplicate `page_content` in review results is real
   data: hundreds of customers independently wrote identical short texts like
   "Atraso na entrega". Distinctness contract is `review_id`, not text.

**Worth remembering:**
- `Chroma.from_texts()` → risky for large corpora (one huge request). Use
  `.add_texts()` in loops on an already-created `Chroma(...)` instance.
- Even `k == collection_size` crashes Chroma/SQLite for large collections.
  Always cap with a hard constant below 32,766.
- `validate_sql()` now has a consistent exception interface: always raises
  `ValidationError`, never leaks sqlglot internals.
- `orchestrate()` has three catch layers: `ValidationError`, `ExecutionError`,
  and a broad `except Exception` final safety net that logs + returns a dict
  instead of crashing the caller.

**Next up (Phase 6):**
Per PROJECT.md order. Phase 5.5b is fully committed.

## 2026-08-02 — Claude (chat)
**Phase:** 5.5a — complete (final piece: fuzzy suggestions)
**Result:** Added difflib-based fuzzy suggestions to categorical_check.py.
- New `suggest_similar_value(bad_value, real_set)`: uses
  `difflib.get_close_matches(n=1, cutoff=0.6)` to find the single
  closest real value, or None if nothing is close enough.
- `check_categoricals()` now returns a new `suggestions` dict key
  (column, bad_value) -> suggestion, alongside the ORIGINAL unchanged
  `problems` list -- deliberately additive, not a reshape, so
  run_eval.py and the existing test file didn't need to change.
- Confirmed Rule 9 still holds: `problems` always reports the original
  wrong value, `suggestions` is purely informational, never substituted
  into the actual query.
- tests/test_categorical_check.py: 3 new tests (suggestion offered for
  close typo, no suggestion for unrelated garbage, suggestion never
  leaks into problems) -- 7/7 total passing.
- tests/test_categorical_check_adversarial.py: 3 new adversarial tests
  -- confirmed empty real_set doesn't crash difflib (returns None
  cleanly, genuinely didn't know this beforehand), empty bad_value
  doesn't crash, and calling the function with an already-valid value
  (a contract violation) still behaves sanely.
**Worth remembering:** This closes Phase 5.5a completely -- retrieval.py,
memory.py, prompt_builder.py refactor, and this fuzzy-suggestion piece
are all built, tested, AND adversarially tested now (new standing rule
from Yuraj this session: every block gets a real penetration/adversarial
test after normal tests pass, not just happy-path tests -- this rule
already caught one real bug this session, in memory.py's
get_recent_turns() leaking internal state).
**Next up:** Phase 5.5b -- Reviews Tool (RAG over review text) +
orchestrator.py. First real open question to test empirically, not
assume: whether nomic-embed-text (English-oriented) handles the
~41%-filled, Portuguese-language review_comment_message text well
enough, or whether a multilingual embedding model is genuinely needed.

## 2026-08-02 — Claude (chat)
**Phase:** 5.5a — Retrieval, Vector DB, Embeddings & Conversation Memory
**Result:** Built and tested all three pieces of Phase 5.5a.
- `src/retrieval.py`: "context" Chroma collection (24 cards: 9 schema
  tables + 15 examples), local nomic-embed-text embeddings via Ollama.
  `build_context_collection()` builds/rebuilds, `search_context(q, k)`
  does meaning-based retrieval. Confirmed by hand: a question with zero
  matching wording ("no category assigned") correctly surfaced the
  right schema card via meaning, not keywords.
- `src/memory.py`: `ConversationMemory` class, plain Python list capped
  at MAX_TURNS=5, oldest dropped first. `format_for_prompt()` turns the
  buffer into prompt-ready text, empty string if no history yet.
- `src/semantic_loader.py`: NEW file, pulled out of prompt_builder.py.
  Reason: prompt_builder.py needed to import search_context() from
  retrieval.py, but retrieval.py already imported the loader functions
  FROM prompt_builder.py -- a circular import. Both files now import
  shared loaders from semantic_loader.py instead; neither imports from
  the other.
- `src/prompt_builder.py`: refactored. Schema + examples now pulled via
  search_context() (top-5 relevant cards) instead of the full 9-table/
  15-example dump every time. Glossary stays included in full always --
  deliberate: only 5 terms, cheap to include, and glossary rules (like
  the unique_customer overcounting fix) can matter even when a question
  doesn't obviously reference them, so narrowing it risked silently
  dropping a rule that mattered. Added optional `memory=` parameter for
  recent-conversation context.
- New standing instruction from Yuraj: every phase now gets an
  adversarial/penetration test in addition to normal tests, written
  AFTER normal tests pass, genuinely trying to break the code -- not
  a one-off, applies going forward to every block.
**Worth remembering:**
- Real bug caught by the first adversarial test ever written on this
  project: `ConversationMemory.get_recent_turns()` returned the actual
  internal list object, not a copy -- any caller could mutate it
  directly and silently blow past MAX_TURNS, completely bypassing
  add_turn(). Fixed with `.copy()`. Would never have been caught by
  normal happy-path tests, since they only ever called the API "the
  right way."
- Adversarial test also confirmed something the docstring only
  CLAIMED: `build_context_collection()` really is safe to re-run
  (Chroma upserts cleanly on matching IDs, no duplicates) -- verified
  empirically instead of trusted on faith.
- Real, known, DEFERRED limitation found by adversarial testing:
  `build_prompt()` does zero sanitization of the user's question --
  a question containing fake `=== QUESTION ===`/`SQL:` headers lands
  in the prompt completely unguarded (prompt injection). Deliberately
  NOT fixed now -- decided not a blocker since validator.py still
  structurally blocks any real DROP/DELETE regardless of how the LLM
  was tricked into generating it. Worth fixing properly later (maybe
  Phase 9 polish), not forgotten, just not urgent.
- Any file inside src/ that imports another file inside src/ must use
  `from src.filename import ...`, not a bare `from filename import ...`
  -- everything in this project runs from repo root, not from inside
  src/. First hit this with retrieval.py importing prompt_builder.py.
**Next up:** Phase 5.5a's last piece -- enhance categorical_check.py
with difflib-based fuzzy suggestions (flagging only, still never
auto-correcting, per Rule 9). Then Phase 5.5a is fully complete and we
move to Phase 5.5b: Reviews Tool + orchestrator.py.

## 2026-08-02 — Claude (chat)
**Phase:** 5.5 — designed, not yet built
**Result:** Reshaped the RAG/memory/NLP requirement honestly instead of
bolting it on. Found a real second use case already sitting unused in the
dataset: `review_comment_message` (real customer complaints, ~41% filled,
Portuguese) — SQL can't semantically search that, so it justifies a real
second tool, not an artificial excuse for complexity.
- **Architecture decided:** SQL Tool (existing pipeline, untouched) +
  new Reviews Tool (vector search over review text, RAG) + Orchestrator
  (ONE bounded LLM classification call: sql / reviews / both, then
  dispatches to fixed pipelines) + conversation memory (plain Python
  list, last N turns, shared across both tools).
- **Kept deliberately lean:** exactly 3 new files —`retrieval.py` (two
  Chroma collections: context + reviews), `memory.py`, `orchestrator.py`.
  Existing safety-critical files (validator, execute, categorical_check)
  untouched on purpose — they're independently tested, no reason to
  restructure what already works.
- **Tools chosen:** Chroma (local, file-based, no server), Ollama local
  embeddings (`nomic-embed-text` to start — cross-lingual quality on
  Portuguese review text is an open question, not assumed), Python's
  built-in `difflib` for a new fuzzy "did you mean...?" suggestion in
  `categorical_check.py` (still never auto-corrects — Rule 9 intact).
- Wrote a full copy-paste text package for updating PROJECT.md (new
  Section 9b amendment + 9c note on file count, updated Phase 5.5a/5.5b
  roadmap entries, updated Section 9/11), Flowcharts_Mermaid_Source.md
  (5 new/updated Mermaid diagrams), and the Word doc tracker (progress
  table row, new subsections, file structure, guardrails table, phase
  checklist with real sourced video links) — handed over as plain text
  for Yuraj to paste in himself, not applied directly to files.
**Worth remembering:**
- **Orchestrator ≠ LangGraph, confirmed and reasoned through.** What
  actually requires LangGraph is state persisting across steps + cycles
  (a step looking at a previous step's output and deciding what to do
  next). This Orchestrator does one classification call upfront, then a
  plain `if/elif` dispatch — a branch, not a graph. Hard Rule 3 ("no
  LangGraph, no autonomous agents") stays fully intact; if the
  Orchestrator ever needs to look at one tool's result before deciding
  whether to call another, THAT would cross into needing LangGraph and
  would need its own amendment — hasn't happened, shouldn't happen
  without deliberately deciding so.
- Attempted a full docx image-regeneration + XML-surgery pass on the
  Word doc tracker (Graphviz diagrams, unzip/re-zip editing) — burned a
  lot of turns/tokens for something the interface can't actually verify
  visually anyway. **Standing correction, going forward: no image
  rendering, no docx/file surgery unless explicitly asked. Plain
  copy-pasteable text and Mermaid code only** — Yuraj pastes it into
  files himself, much cheaper and he's going through it side-by-side
  anyway.
- Also surfaced a fair critique: this project's modularity (many small
  files) is a deliberate choice tied to Phases 2–4 being safety-critical
  and independently testable, not just "how projects are usually built"
  — worth being able to explain that reasoning if asked in review.
**Next up:** Phase 5.5a — install `langchain-chroma` + `chromadb`, pull
`nomic-embed-text` via Ollama, build `retrieval.py`'s context collection
(examples + schema) first, block by block. Reviews collection and
Orchestrator come in 5.5b, after 5.5a is tested and committed. Confirm
the PROJECT.md/Flowcharts/docx copy-paste updates were actually pasted
in before assuming those docs are current.

## 2026-08-01 — Claude (chat)
**Phase:** 5 — LLM connected via LangChain, provider factory built
**Result:** Built and tested the real LLM layer for the first time in
this project's life.
- `src/llm_client.py`: `get_llm(provider)` factory returning ChatGroq /
  ChatGoogleGenerativeAI / ChatOllama behind one identical interface.
  Unknown provider name → warns and falls back to `DEFAULT_PROVIDER =
  "groq"` rather than crashing (deliberate choice: never crash on a typo).
- `src/prompt_builder.py`: loads schema_cards.yaml, glossary.yaml,
  examples.jsonl and assembles them + the question into one prompt
  string via `build_prompt()`. Hands the LLM everything every time, no
  retrieval/ranking — matches PROJECT.md Section 9's YAGNI call.
- `.env` (gitignored) holds GROQ_API_KEY and GOOGLE_API_KEY via
  python-dotenv.
- Real end-to-end test on Groq: correct SQL for a simple question AND
  a harder question with no matching example (correctly pulled
  customer_unique_id from glossary.yaml, not customer_id, proving the
  semantic layer is actually being read, not just pattern-matched).
- Ollama (qwen2.5:7b, local, RTX 4050) also tested, responded correctly.
**Worth remembering:**
- Gemini free tier now requires a linked Google Cloud billing account
  (still free under quota) — a `429 RESOURCE_EXHAUSTED ... limit: 0`
  error is THIS, not real quota exhaustion. Decision: parked Gemini,
  not fixed — Groq + Ollama already proves the factory pattern works.
  Circle back later if a 3rd provider is genuinely needed.
- New standing instruction from Yuraj: don't just avoid hand-writing
  SQL — also skip the teach-it-step-by-step ritual for Python
  plumbing/glue code (factories, file loaders, prompt assembly). Write
  that directly with comments; reserve the slow teaching ritual for
  genuinely new concepts.
- Ollama PATH issue (bare `ollama` not recognized right after install)
  fixed just by closing and reopening PowerShell — same root cause
  shape as the earlier Python PATH bug, same fix, no registry surgery
  needed this time.
**Next up:** Phase 6 — `src/sql_agent.py`, wiring build_prompt() →
get_llm().invoke() → validate_sql() → check_categoricals() →
run_query() with a real repair loop (regenerate_fn now actually calls
the LLM with the error fed back in). Then tests/test_sql_agent.py runs
the Phase 4 gold set through the REAL pipeline for the first time.

## 2026-08-01 — Claude (chat)
**Phase:** 4 — Gold Test Set
**Result:** eval/gold_set.jsonl built — 18 hand-written cases: 8 normal,
2 bad_categorical, 2 should_block, 1 bad_table_name, 1 bad_column_name,
2 unanswerable. eval/run_eval.py built, wired to real validate_sql()
(raises ValidationError) and real run_query() (returns columns, rows
tuple, raises ExecutionError) -- initial draft guessed dict-return
shapes for both and had to be corrected against the real files.
18/18 passed on first full run after the fix.
**Worth remembering:** validator.py's row cap (MAX_ROWS=1000) is
confirmed genuinely active -- case #6 (seller with most orders, no
LIMIT in the query) returned exactly 1000 rows, not the full table,
proving the cap isn't just decoration. Harness now proven correct
BEFORE any LLM is connected -- future low accuracy scores can be
blamed on the model, not a broken test.

## 2026-08-01 — Claude (chat)
**Phase:** 3 — Categorical Check
**Result:** src/categorical_check.py built — loads real distinct values
for 5 categorical columns from olist.db, extracts (column, value) pairs
from EQ and IN nodes via sqlglot, flags any value not in the real set.
Handles reversed EQ ('value' = column) and IN clauses with mixed
good/bad values. Never auto-corrects (Rule 9). tests/test_categorical_check.py
4/4 passing.
**Worth remembering:** IN nodes use plural `expressions` (a list), EQ
uses singular `expression` (one item) -- easy to mix up. IN with a
subquery (not a literal list) is deliberately skipped, not handled yet.

## 2026-08-01 — Claude (chat)
**Phase:** 2 — complete
**Result:** Built and tested both safety-layer files.
- `src/validator.py`: parses SQL with sqlglot into an AST, checks (1) root
  node is `exp.Select` (blocks DELETE/DROP/UPDATE/etc structurally, not by
  text matching), (2) every table found via `find_all(exp.Table)` is in a
  9-table allow-list (set difference check), then attaches a LIMIT 1000 via
  `tree.limit()`. `tests/test_validator.py` — 8/8 passing: valid select,
  DELETE blocked, DROP blocked, disallowed table blocked, valid join,
  CTE join, multi-statement injection blocked, and a self-authored subquery-
  to-banned-table attack (buried inside a WHERE ... IN (...) subquery).
- `src/execute.py`: opens SQLite via `file:...?mode=ro` URI (uri=True) —
  a second independent safety layer that's physically incapable of writing,
  not just policy-enforced. `run_query()` wraps sqlite3.Error into a custom
  `ExecutionError`. `run_with_repair()` is a plain Python while-loop, max 2
  retries, calling an injected `regenerate_fn(failed_sql, error_message)` —
  no LLM wired in yet, tested with stand-in functions. `tests/test_execute.py`
  — 5/5 passing, including `test_connection_is_actually_read_only`, which
  proves sqlite3 itself raises `OperationalError` on an attempted INSERT
  through the read-only connection.
**Worth remembering:**
- Real bug caught and fixed: `find_all(exp.Table)` cannot distinguish a real
  table from a CTE alias (`WITH recent_orders AS (...)`) — both look like
  "a table being read from" to sqlglot. Fix: collect CTE names via
  `find_all(exp.CTE)` and subtract them from `tables_used` before checking
  the allow-list. Without this, any query using a CTE would be wrongly
  refused. Worth remembering for any future AST-based table-extraction code.
- Off-by-one logic in the repair loop was deliberately checked by hand:
  `attempt` increments BEFORE the `attempt > MAX_RETRIES` check, giving
  exactly 3 total tries (1 original + 2 retries) for `MAX_RETRIES = 2`. Using
  `>=` instead would silently change the retry count by one — confirmed
  understood, not just copy-pasted.
- Environment detour: a stray `Set-Alias python ...pythoncore-3.14-64...`
  line in the PowerShell profile was overriding the venv's PATH prepend
  every time, even after activation. Fixed by Antigravity (replaced
  Set-Alias with an appended PATH fallback). Confirmed dead — plain
  `python` now correctly resolves to the venv.
- Minor file-location slip: created `test_execute.py` while `cd`'d into
  `src/`, which nested it as `src/tests/test_execute.py` instead of the
  real `tests/` at repo root. Moved and cleaned up. Lesson: always confirm
  `pwd` before creating new files if unsure which folder you're standing in.
- New standing instruction from Yuraj: all code, going forward, should be
  fully comment-loaded by default (line-by-line), no need to ask each time.
**Next up:** Phase 3 — `categorical_check.py`. Ground truth values were
already recorded in Phase 0 (`semantic/categorical_values.md`), including
the `not_defined` 5th payment_type and the 4 missing seller_state values.
Phase 3 needs to: query real distinct values at startup, extract literal
string values compared against categorical columns from validated SQL,
check membership, and flag (never auto-correct) on mismatch.

## 2026-07-31 — Antigravity
**Phase:** 2 (PATH/venv fix, unblocking prior session)
**Result:** Found and fixed the real cause of the python/venv PATH bug.
PowerShell profile (Microsoft.PowerShell_profile.ps1) had a hardcoded
`Set-Alias python 'C:\...\pythoncore-3.14-64\python.exe'` from an earlier
edit — PowerShell aliases override PATH, so this silently beat the venv's
PATH prepend every single time, even right after activation, even in a
fresh window. Replaced the alias with appending the system Python dir to
PATH instead (so it's only a fallback, not an override). Verified: plain
`python` now correctly resolves to venv's python.exe after activation.
scratch_ast.py re-run successfully, confirms sqlglot AST output as before.
**Worth remembering:** If `python` ever misbehaves again on this machine,
check `$PROFILE` for stray Set-Alias lines before anything else — this
was the actual root cause both times, not app execution aliases.

## 2026-07-31 — Claude (chat)
**Phase:** 2 (blocked before real progress)
**Result:** Started Phase 2 (validator.py). Confirmed sqlglot installed
correctly and parses SQL into an AST as expected (tested manually via
`.\venv\Scripts\python.exe src\scratch_ast.py` — printed a clean Select
node tree with expressions/from_/where). No validator.py logic written yet.
**Worth remembering:** Hit a Windows PATH/venv bug that ate the whole
session — plain `python` intermittently resolves to system Python 3.14
(`C:\Users\Lenovo\AppData\Local\Python\pythoncore-3.14-64\python.exe`)
instead of the venv's python, even right after `.\venv\Scripts\Activate.ps1`
and even in a brand-new PowerShell window. Calling the venv's python.exe
by full path (`.\venv\Scripts\python.exe`) always works correctly — the
venv itself is fine, this is purely a PATH resolution issue. Checked
"Manage app execution aliases" — python.exe/python3.exe already toggled
Off, so that's not the cause. Suspect the newer "Python install manager"
(py.exe/pymanager.exe) intercepting the bare `python` command instead.
Not resolved — handing off to Antigravity to fix directly on the machine
rather than burn more chat turns guessing blind. Next session: fix PATH
issue first, then resume Phase 2 from scratch (validator.py not started).

## 2026-07-31 — Claude (chat)
**Phase:** Phase 1 — complete
**Result:** Built all 3 semantic layer files against the real schema:
- schema_cards.yaml — all 9 tables documented (columns, types,
  descriptions, joins, known gotchas like NULL lifecycle stages and
  tables needing aggregation before joining).
- glossary.yaml — 5 business terms defined: late_delivery (NULL
  delivery date counts as late, by decision), unique_customer (must
  use customer_unique_id, not customer_id, to avoid overcounting
  repeat buyers), top_seller (defaults to revenue by product price,
  alternates noted), average_delivery_time (uses julianday(), not
  DATEDIFF — SQLite has no DATEDIFF), unanswerable_question (4
  categories of genuine out-of-scope questions).
- examples.jsonl — 15 hand-written examples: 11 normal questions with
  real SQL against real column names, 4 refusal examples covering
  export/country data, specific product/brand names, employees/
  warehouse ops, and real-time/current data — each with its own
  distinct, non-copy-pasted reason for refusal.
**Worth remembering:**
- SQLite has no DATEDIFF — use julianday(a) - julianday(b) for date
  differences, caught this twice (average_delivery_time glossary term,
  then again in an examples.jsonl query).
- YAML auto-converts bare words on/off/yes/no/true/false to booleans —
  quote them as "on" if you need the literal word as a key (bit us in
  schema_cards.yaml's joins section).
- Python REPL needs a blank line to close an indented `with`/`for`
  block before you can type the next command — tripped us up twice.
  Prefer saving multi-line code as a .py script and running it instead
  of pasting into the raw REPL.
- Copy-pasting the same justification across different refusal
  examples is a subtle but real bug — each refusal needs its own
  actual reason, not a reused one that happens to also be true.
- Phase 0's categorical ground truth already caught 2 real surprises
  worth remembering: payment_type has a 5th real value (not_defined,
  not in PROJECT.md's guess), and seller_state is missing AL, AP, RR,
  TO compared to customer_state (no sellers in those states).

## 2026-07-31 — Claude (chat)
**Phase:** Phase 0 — complete
**Result:** Ran SELECT DISTINCT on all 5 categorical columns (real ground
truth recorded in semantic/categorical_values.md — found payment_type has
a 5th real value, `not_defined`, not in PROJECT.md's guessed list; also
found seller_state is missing AL, AP, RR, TO compared to customer_state —
no sellers based there). Built build_db.py, loads all 9 CSVs into
olist.db via a loop. Verified row counts match Phase 0 .info() exactly.
Ran and verified 5 hand-written SQL queries against real data (delivered
orders, top states by customer count, avg payment value, distinct seller
count, most common payment type) — all results sane and cross-checked
against earlier findings.
**Worth remembering:** conn.execute() returns a cursor, not the connection
itself — fetchall() goes on the returned object, not on conn directly.
Also: always close and reopen the connection between a write phase and a
read phase, don't just keep reusing one connection carelessly.

## 2026-07-30 — Claude (chat)
**Phase:** Setup
**Result:** Empty folder skeleton created, git initialized, project brief and flowcharts placed in repo root.
**Worth remembering:** Following the same brick-by-brick, build-understand-test-commit ritual used for the YOLO traffic project. Phase 0 is next: download the real Olist dataset, build olist.db, inspect every real column and value by hand before writing any code that depends on them.





