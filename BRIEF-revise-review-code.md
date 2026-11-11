# Review brief: code review of the revise implementation

For the reviewing AI session (dsh profile `reviewer`, Kimi K2.7 Code).
You are reviewing, not implementing. Do not edit any file. AGENTS.md
rules apply to your reading (notably: no magic numbers without a paper
citation or NOVEL comment; flat explicit flow; code written for
subsequent AIs).

## Scope

The revise step + repair history, implemented per BRIEF-revise.md and
BRIEF-revise-parts.md (read both). Files in scope: solver.py (the
revise stage, solve report, parts inventory, budget), cases.py
(history round-trip), demo.py (wiring, repair lines, baseline). The
last committed state is GitHub commit b8bd532e; everything about
revise/history is new since then. library.py and dsl.py are out of
scope except where the new code calls into them.

## What to hunt for

- Budget accounting: REVISE_CANDIDATE_LIMIT must bound the number of
  repaired programs actually TESTED per solve() call, across sources
  and tiers. Look for off-by-one errors, candidates generated but
  neither tested nor counted, and paths where the stage can exceed
  the limit.
- Counting honesty in general: every program tested by any stage is
  reflected in candidates_tested exactly once; skipped no-op repairs
  are handled consistently between tier 1 and tier 2.
- Edit-record fidelity: for each edit kind, applying the recorded edit
  to the source program must reproduce the returned program exactly.
  Probe this property with your own small scripts (e.g. construct a
  case base, force a swap/insert/remove win, compare).
- Enumeration order and determinism: the briefs pin an order for
  sources, tiers, sites, ops, and values. Check the implementation
  follows it, and that dict/set iteration cannot leak nondeterminism
  into it.
- Edge cases: remove producing an empty chain; a source program with
  repeated identical ops; joiner edits; sources skipped when
  library is None; solve() failure report shape (keys present, path
  None, reason string preserved).
- Round-trips: cases with structural-edit histories through
  cases.py save/load; histories on cases that later become template
  references (does anything drop or corrupt history?).
- Regressions vs the pre-revise behavior: template and reuse results
  for the original tasks must be untouched by the new stages.

## Report format

Findings first, most severe first, each with file:line evidence and,
where you claim a defect, a minimal reproduction or a trace. Then a
short list of what you verified as correct. If a brief requirement
and the code disagree, say which one you are reading. Do not propose
redesigns; correctness against the briefs and AGENTS.md is the bar.
