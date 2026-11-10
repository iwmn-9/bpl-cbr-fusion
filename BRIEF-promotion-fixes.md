# Brief: fix round for the promotion step (code review + semantic review)

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
Repo rules are in AGENTS.md; they win on any conflict. Work only in this
directory. Do not edit BRIEF-*.md or docs/. Two reviews produced the
findings below; fix all of them. `python3 demo.py` must still run clean
and hit the acceptance outcomes at the end of this brief.

## Code-review findings (correctness)

1. solver.py: `solve(..., library=None)` crashes on promoted cases —
   the reuse path calls `materialize(case, None)` and raises. When the
   library is None, cases carrying a `template_id` must be skipped in
   reuse, restoring the pre-promotion solver's behavior (plus the extra
   return value).
2. library.py `maybe_promote`: it returns after the first
   promotion/update. Remove the early returns: try every existing
   template, then every earlier case, accumulate all promotion events,
   and return the full list.
3. library.py `_promote`: when a case is rewritten to reference a
   different template, its task_id stays in the old template's support
   list, corrupting the summary. On rewrite, remove the task_id from
   the previous template's support. If that drops the old template
   below MIN_SUPPORT_CASES, dissolve it: restore its remaining cases
   to concrete programs (via instantiate with their bindings), remove
   the template, and emit a "dissolved" event string.
4. library.py `_anti_unify_value`: when both values are slots with
   different names, the right slot's identity is silently dropped.
   Treat the (left_name, right_name) pair like any other differing
   pair: map it to one fresh slot through the same consistent-pair
   mechanism (key the pair map on slot names in that case). The
   instantiate-reproduces-operands invariant must hold for
   template-vs-template anti-unification too.
5. Duplicated slot traversal: `slots_of` (library.py) and
   `_slot_positions` (solver.py) walk the template structure twice.
   Put one shared walker in library.py and use it from both modules.

## Semantic-review findings (meaning)

6. Zero-slot promotion is deduplication, not type formation.
   `maybe_promote` must skip anti-unification results with zero slots:
   a promotion requires at least one slot. (Verified by the reviewer:
   on the demo corpus the end state is identical — T1 is born at
   name-swap-semicolon instead, already slotted, covering name-swap,
   name-swap-new, and name-swap-semicolon.)
7. Honest size reporting in demo.py. The current "compression: 7/7"
   line conflates a reference ratio with byte savings; measured net
   effect is about +152 B (library overhead exceeds case savings).
   Change the summary to print both: "references: X/Y cases stored as
   references" and the net size delta in bytes — (cases.json +
   library.json) versus the all-concrete baseline (every case
   materialized, serialized as a cases-only file). No claim wording
   beyond the numbers.
8. Citation comment in library.py overstates. Reword so it says, in
   substance: anti-unification / least general generalization
   restricted to structurally identical skeletons (Plotkin 1970); the
   promotion loop is the same family of move as DreamCoder's library
   learning (Ellis et al. 2021), minus the neural parts and minus its
   MDL acceptance test. Keep it to a couple of lines.
9. Slot domains in solver.py: a string slot's domain is currently only
   the task's observed separators, so a slot born from a non-separator
   literal can never be filled. Extend the domain with every value
   that slot takes in the bindings of the template's support cases
   (read from the case base). Integer slots and the joiner "" rule
   stay as they are.

## Acceptance (demo.py, after fixes)

- Paths unchanged: search / search / reuse / search / template /
  search / template.
- No promotion event after name-swap-new. T1 created at
  name-swap-semicolon with support 3, updated to 4 at name-swap-pipe.
  T2 created at date-separator-dot with support 2, updated to 3 at
  date-separator-underscore.
- Final summary: templates 2 (support 4 and 3), references 7/7, plus
  the honest net-size line.
- A case base full of references passed to solve() with library=None
  no longer raises.
