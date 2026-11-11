# Brief: comment corrections after the revise reviews

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
AGENTS.md wins on any conflict. Work only in this directory. Do not edit
BRIEF-*.md or docs/.

The code review found no defects. The semantic review found that two
comments in solver.py claim more than the system's own demo supports,
and that one convention is undocumented. This brief is COMMENT-ONLY:
no behavior may change, and `python3 demo.py` output must remain
byte-identical to the current run.

## Fix 1 — budget sizing comment (solver.py, at REVISE_CANDIDATE_LIMIT)

Replace the two "Sizing rule" sentences with wording to this effect
(close to verbatim):

"The budget caps revise's worst case far below the search stage's own
worst case (MAX_CHAIN_PAIRS pairs, each with several joiners). It does
not make a failed revise cheap on small tasks: a task with no winning
repair pays the full tier enumeration first (measured: 88 tests on
date-separator, whose search then needs 5)."

Keep the preceding NOVEL sentences about the shared budget as they are.

## Fix 2 — tier-order comment (in _repair_candidates)

The current text says the fixed order is "cheapest first". Replace
that claim with wording to this effect:

"Tiers are ordered by edit size — value, swap, insert, remove — which
orders the edits tried, not their expected cost: a source with no
winning repair pays for all four tiers."

Keep the Koza 1992 mutation citation sentence as it is.

## Fix 3 — edit-record coordinate frame (new comment)

Edit records' sites/site are indices into the SOURCE program (the
program before the edit is applied). This convention is currently
stated nowhere. Add one short comment saying exactly that, placed
directly above `def _repair_candidates`.

## Acceptance

- Only comments changed; `python3 demo.py` output byte-identical.
- grep confirms the phrases "stays cheaper than the search stage" and
  "cheapest first" no longer appear in solver.py.
