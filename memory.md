# Project Memory Log

Newest entries at the top. A few lines each.

---

## 2026-07-30 — Claude (chat)
**Phase:** Setup
**Result:** Empty folder skeleton created, git initialized, project brief and flowcharts placed in repo root.
**Worth remembering:** Following the same brick-by-brick, build-understand-test-commit ritual used for the YOLO traffic project. Phase 0 is next: download the real Olist dataset, build olist.db, inspect every real column and value by hand before writing any code that depends on them.

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