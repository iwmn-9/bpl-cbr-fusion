# Brief: repair-pattern promotion v1 (entry 001)

## Why

Promotion v1 abstracts solution skeletons (templates). The sketch's core
claim is the other half: winning REPAIRS should also crystallize into
reusable parts ("adaptation outcomes grow the library"). The metabolism
round completed the input side: every case carries history with the
winning edit record ({kind, ...}), and attempts record the failures.
This round adds the pattern store and its consumer. Demo facts the
design rests on (verified by replay): exactly three revise wins exist —
(value, string) ", " -> "; " (source name-swap), (value, string)
"/" -> "." (source date-separator), and one swap replace -> upper
(source date-separator). The two value wins share one abstraction and
reach support 2; the swap stands alone at support 1.

## Requirements

R1. Pattern mining in library.py: `maybe_promote_patterns(case_base,
library)`, called by demo after `maybe_promote`. Scan the cases'
history records; for each case whose history has edits, abstract each
winning edit to a pattern key:
- value edit -> ("value", role)
- swap edit -> ("swap", from_op name, to_op name)
- insert edit -> ("insert", op name)
- remove edit -> ("remove", op name)
Support of a key = the set of distinct task_ids whose winning edits
abstract to it. Keys with support >= MIN_SUPPORT_CASES (the existing
constant; same recurrence threshold as templates) are promoted into
`library.patterns` as:
{"pattern_id": "P<n>", "kind": ..., key fields mirroring the key
(e.g. "role" for value; "from_op"/"to_op" names for swap; "op" for
insert/remove), "support": [task_ids in case-base order]}.
Pattern IDs are monotonic and never reused, persisted exactly the way
template IDs are (a next-number counter in library.json; old files
without it derive it from existing patterns). Mining is idempotent:
re-running updates support lists in place, never duplicates a pattern,
and returns the list of promotion/update event strings the way
maybe_promote reports promotions (demo prints them). Patterns are
never dissolved in this round.

R2. Persistence: Library gains a `patterns` list (default []), saved
and loaded with the rest of library.json. Backward compatible: a
stored file without "patterns" loads with patterns = [] (use the same
dual-shape care as templates). cases.py is unchanged.

R3. Pattern application in solve: inside the revise step, BEFORE the
tier enumeration for a source program, try the promoted patterns that
apply to that source, in pattern order (support size descending, then
pattern_id ascending):
- A ("value", role="string") pattern applies when the source program
  contains at least one string literal and the target examples' output
  separators are non-empty. Its candidates: for each distinct string
  literal L of the source (in the value tier's literal order), for
  each separator S in the target examples' output separators with
  S != L, the program with L replaced program-wide by S (value-tier
  semantics). 
- Swap/insert/remove patterns: define their application analogously
  ONLY if a promoted instance exists in the demo run — none does
  (support 1), so this round implements the value/string application
  and leaves the others as mined-but-not-applied; state that plainly
  in the report rather than building speculative machinery.
Pattern candidates are tested like any revise candidate: they count
toward candidates_tested and the shared REVISE_CANDIDATE_LIMIT budget.
CRITICAL dedupe: a pattern candidate that the tier enumeration would
also generate must be tested once — the tier generators skip programs
already tested in this revise call (track tested programs by their
canonical JSON). With dedupe, a pattern that only reorders existing
candidates changes no counts; baseline demo totals must not move.
If a pattern candidate wins, the winning edit record is the usual
value edit record PLUS "pattern_id": the pattern's id. The revise
attempt record gains "pattern_tested": <count of pattern candidates
tested for this source> (0 when no pattern applied).

R4. Demo wiring: call maybe_promote_patterns after maybe_promote each
task and print its events in the same style as template promotions
(e.g. "pattern: promoted P1 support=2: name-swap-semicolon,
date-separator-dot"). The final library summary prints a patterns
line: "patterns: P1 (value/string) support=2" style — mirror the
existing templates summary formatting. No other demo output changes.

R5. Report: write REPORT-repair-promotion.md (what was built, where,
any divergence and why) including verification: demo 8/8 with paths
unchanged and per-task candidates unchanged (total 73 — dedupe
proof); P1 promoted exactly after the date-separator-dot task with
support {name-swap-semicolon, date-separator-dot}; the swap key NOT
promoted (support 1); code-upper's revise attempt(s) show
pattern_tested >= 1 with total candidates still 22; mining
idempotence (second call adds nothing); library.json round-trip
preserves patterns; an old-format library file (templates only)
still loads.

## Non-goals

- No ranking change (that decision is still data-pending).
- No mining of failed attempts as negative evidence (recorded for a
  later round; say so in the report).
- No MDL/size acceptance gate for patterns; support threshold only,
  same as templates v1.
- No change to templates, admission, maintain, or the gate.
- No new numeric constants without a paper citation or a NOVEL:
  comment.

House rules (AGENTS.md) apply: stdlib only, no redundant explanation,
citations in comments where a choice comes from the literature
(pattern mining from repair histories is the CBR adaptation-learning
line — reuse of adaptation knowledge, cf. Smyth & Keane's
adaptation-guided retrieval already cited in solver.py; keep comments
to what the code cannot say). Do not commit.
