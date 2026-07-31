# Project Memory Log

Newest entries at the top. A few lines each.

---


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





