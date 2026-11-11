# Fix brief: metabolism round — review fixes

Reviews: REVIEW-metabolism-code.md (no defects in the core mechanisms) and
REVIEW-metabolism-semantic.md (3 moderate, 4 minor). Implement the fixes
below exactly. Everything not mentioned stays as it is. Write a short
addendum to REPORT-metabolism.md ("Fix round" section) describing each
change and the re-verified numbers. Do not commit.

F1. Tombstone statistics (semantic finding 1). When maintain() removes a
case, its distilled record must survive: append
{"task_id", "admission", "stats", "decision": "removed"} to a case-base
level list of removed records. CaseBase owns it: a `removed` list
attribute (default []), and cases.py persists it. File format: keep
backward compatibility the way Library.load does — a stored top-level
list means the old format (removed = []); the new format is
{"removed": [...], "cases": [...]}. Old files must load and re-save
without losing data. Restore the honest comment at maintain(): statistics
are distilled into tombstones before the body is deleted, so the record
of what was removed and how it performed survives. demo.py prints one
additional line after the maintain decisions:
"removed records: <n>" (the tombstone count). No other demo output
changes from this fix.

F2. Like-for-like size baseline (semantic finding 2). demo.py's
all-concrete baseline must carry the same per-case metadata as the
current representation: copy "stats" and "admission" into baseline cases
exactly as "history" is already copied. The printed net size delta
becomes the honest single number (expected +193 B; verify and report
the actual). Add a code comment at the baseline construction: the
baseline carries history/stats/admission verbatim so the delta measures
representation only.

F3. Prune stale support (semantic finding 3, code finding 1). In
maintain(), when a removal is committed, remove the case's task_id from
every template's "support" list in the library. Do NOT dissolve
templates in maintain() and do not touch support for kept cases. The
demo's printed T1 support becomes 3 (was 4); report the change.

F4. Gate comment precision (semantic finding 4). Replace the gate
comment's overclaim with the accurate statement: the gate restricts
STRUCTURAL repair effort by executability (the source must run on every
target input); the value tier is never gated (a non-executing source
can still win there — name-swap-semicolon, gated=true with a value-tier
win, is the in-demo proof); it blocks 80 of the 88 candidates in the
measured case. Keep the Smyth & Keane 1998 citation but mark the
descent: their retrieval ranks by adaptability; this gate is the same
principle at a coarser, one-bit decision point (executable or not),
applied to repair effort instead of ranking. Use the semantic review's
suggested replacement text (§4 of REVIEW-metabolism-semantic.md) if it
matches this specification.

F5. Report erratum (semantic finding 7). In REPORT-metabolism.md
verification 7, correct the mispaired figure: the drop "6620 -> 6143"
is 477 B, not 590 B (590 B belongs to the metadata-inclusive baseline).
Fix in place and note the correction in the Fix round addendum.

Acknowledged non-fixes (do not change code; the addendum states they
are recorded as known behavior): code finding 3 (classify_admission
with library=None under-reports redundancy for reference-only bases),
code finding 4 (maintain() decisions are order-dependent across
multiple redundant cases), semantic finding 5 (behavior {passed,
errors} is insufficient for the deferred ranking decision — its four
missing pieces are design input for that future round), semantic
finding 6 (admission labels are insertion-time events).

Re-verify after fixes and report in the addendum: demo 8/8, paths
unchanged, per-task candidates unchanged (total 73), competence check
8/8, maintain decision unchanged (name-swap-new removed), printed net
size delta (expected +193 B), T1 support printed as 3, tombstone
present in a saved cases file with the removed case's stats intact,
old-format cases file still loads, demo output byte-identical across
two runs (new hash).
