# Brief: structural repairs — parts swap / insert / remove

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
AGENTS.md wins on any conflict. Work only in this directory. Do not edit
BRIEF-*.md or docs/.

## Why

Project direction (user, 2026-11-10): BPL x CBR is the axis, but the
glue and internals should be modern, and other theories may be combined
freely. The value-only revise from BRIEF-revise.md is therefore just the
cheapest tier of adaptation, not its ceiling. This brief extends the
revise stage with structural repairs: a program is an assembly of parts
(ops) in slots, and a repair may swap, insert, or remove a part. Every
op in this DSL is string -> string, so any part fits any slot; say so
in a comment at the parts inventory, citing component-based synthesis
(Jha et al. 2010). The structural tiers are mutation-style operators
(cite Koza 1992 in a comment at the tiers).

## Design

### Repair tiers (extend the existing revise stage)

Keep the stage order template -> reuse -> revise -> search, and keep
the existing per-source loop and REVISE_SOURCE_LIMIT. Within each
source case, try tiers in this order; the first repaired program
matching ALL examples wins, as today:

- Tier 1 (exists): value change — one program-wide constant replaced.
- Tier 2 (new): swap — replace ONE op occurrence (one chain, one
  position) with a different op from the parts inventory.
- Tier 3 (new): insert — insert ONE op at one position of one chain
  (positions 0..len(chain)).
- Tier 4 (new): remove — remove ONE op from one chain. The chain may
  become empty (an empty chain is the identity on its input).

Parts inventory: the DSL ops in OP_ARG_ROLES order, EXCLUDING slice
(search never generates slice either; its integer domains are not
example-derived). Argument values for a swapped/inserted op come from
the same domains tier 1 uses: string args = separators observed in the
task's examples (inputs then outputs); int args = range
(FIELD_INDEX_LIMIT); zero-arg ops (upper/lower/strip) take no values.
A swap whose result is identical to the source program is skipped.

Enumeration order is deterministic everywhere: chains in order,
positions in order, ops in inventory order, argument values in domain
order (for two-arg ops, first arg outer loop, second inner).

### Revise budget

Structural enumeration is wide, so the whole revise stage gets one
budget: REVISE_CANDIDATE_LIMIT (NOVEL comment), the maximum number of
repaired programs the revise stage may test per solve() call across
all sources and tiers. Size it well below MAX_CHAIN_PAIRS and state
the sizing rule in the comment (a failed revise must stay cheaper
than the search stage it precedes). 256 is acceptable. When the
budget is exhausted the stage returns and search proceeds; every
test still counts toward candidates_tested.

### History records (extend the v1 format)

Each edit gains a "kind". Tier 1 edits keep their current shape plus
"kind": "value". New kinds, JSON-native throughout:

- swap: {"kind": "swap", "site": [chain_idx, op_idx],
  "from_op": op-as-list, "to_op": op-as-list}
- insert: {"kind": "insert", "site": [chain_idx, position],
  "op": op-as-list}
- remove: {"kind": "remove", "site": [chain_idx, op_idx],
  "op": op-as-list}

demo.py prints one repair line per edit for the new kinds too:
`repair: <source_case> <kind> <site> <op details in data form>`.

### Demo: one new task

Append an 8th task, "code-upper":
examples [["ab-cd", "AB-CD"], ["wx-yz", "WX-YZ"]].
No existing stage can solve it (search never generates upper; tier 1
keeps the replace op), so it exists to exercise tier 2. Expect it to
be solved by revise via swapping a date family's replace op for
upper. Adding it changes the end state: references become 7/8 (the
new case is covered by no template). That is expected, not a
regression.

## Out of scope

- Promotion of repair patterns (next brief) — but the edit records
  above are its input contract; keep them complete and exact.
- Multi-edit repairs (two swaps, swap+value, etc.), chain-level edits
  (adding/removing whole extractor chains), changes to promotion or
  to the template/search stages.

## Acceptance

`python3 demo.py` (run twice; output identical):

- All 8 tasks solve. Paths: search, search, reuse, revise, template,
  revise, template, revise. If they differ, stop and report.
- The two tier-1 revise histories are unchanged in shape and content
  (kind "value", same edits as before this brief).
- code-upper's history records exactly one edit of kind "swap" whose
  to_op is ["upper"].
- End state: T1 support 4, T2 support 3, references 7/8.
  paths line: search=2 reuse=1 revise=3 template=2.
- date-separator falls through revise to search as before; its
  candidates_tested grows (structural tiers spend budget first) but
  the revise stage never exceeds REVISE_CANDIDATE_LIMIT for any task
  (verify by the counts: no task's total implies more than the limit
  spent inside revise).
- Histories with structural edits survive a save/load round-trip.
- New constants carry NOVEL comments; citations (component-based
  synthesis; GP mutation) sit at the inventory / tiers.
