# Brief: revise step + repair history

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
AGENTS.md wins on any conflict. Work only in this directory. Do not edit
BRIEF-*.md or docs/.

## Why

The design sketch (`docs/entry-001-sketch.md`) defines the case base as
（問題、プログラム、実行結果、修正履歴） and step 3 as 適用・修正
(apply, then locally repair what fails). The current system has neither:
a retrieved program is replayed exactly or discarded, and cases store no
history. This brief adds the revise step and the history record. It does
NOT add promotion of repair patterns; that is the next brief, and the
history format below is the contract it will consume.

## Design

### 1. Revise step in solver.py

Insert a revise stage between exact reuse and search, so the order is:
template -> reuse -> revise -> search. Tasks that template or reuse
already solve must behave exactly as before.

Repairs are value-level only. A repair never adds, removes, or reorders
ops or extractor chains; it changes literal argument values of an
existing program (the revise step of the CBR cycle: Aamodt & Plaza
1994 — cite in a comment where the stage is introduced).

- Sources: the same ranked, materializable cases the reuse loop walks
  (including the library=None skip for template-referencing cases),
  capped at REVISE_SOURCE_LIMIT sources (NOVEL constant with comment;
  3 is fine).
- One repair = pick one distinct (role, value) pair among the source
  program's literal arguments — roles from OP_ARG_ROLES in library.py
  ("string" / "int"), plus the joiner as role "joiner" — and replace
  EVERY occurrence of that value in arguments of that role with one new
  value. (One edit = one program-wide constant changed. This mirrors
  the slot-identity rule in anti-unification: the same literal is the
  same constant everywhere. The joiner counts as its own single site.)
- Candidate new values, in deterministic order:
  - role "string": separators observed in the task's examples, inputs
    first then outputs, as `_slot_domains` already collects them.
  - role "int": range(FIELD_INDEX_LIMIT).
  - role "joiner": observed output separators, then "" if absent.
  Skip the no-op replacement (new value == old value).
- Enumeration order: sources in rank order; within a source, distinct
  (role, value) pairs in program order (extractor chains in order, ops
  in order, args in order, joiner last); values in domain order. First
  repaired program matching ALL examples wins.
- Every repaired program tested counts toward the returned
  candidates_tested total, exactly like the other stages.

### 2. Solve report and case history

`solve` returns (program, report, tested). report is a dict with keys:

- "path": "template" | "reuse" | "revise" | "search" on success, None
  on failure.
- "reason": the current failure message string on failure, else None.
- "source_case": task_id of the case a reuse/revise solution came
  from, else None.
- "source_template": template id for the template path, else None.
- "bindings": the bindings dict used on the template path, else None.
- "edits": list of repairs applied; empty unless path == "revise".
  Each edit: {"role": role, "from": old value, "to": new value,
  "sites": [[extractor_idx, op_idx, arg_idx], ...]} with ["joiner"]
  as the site for a joiner edit. JSON-native types only.

cases.py: an optional "history" key on a case round-trips through
load/save unchanged (same pattern as template_id/bindings). A history
is exactly the report dict above, minus "reason". Old case files
without "history" load as before.

### 3. Demo wiring

demo.py uses the new solve signature. On success it stores the case
with its "history" attached, prints the path as today, and for the
revise path additionally prints one line:
`repair: <source_case> <role> <from!r> -> <to!r>` (one line per edit;
there is at most one in this version).

The all-concrete baseline in the summary must carry the same history
fields as the current cases (like-for-like: the size delta measures
program representation, not the presence of history). The net size
delta is whatever the files measure; do not target a number.

Add one summary line: `paths: ` followed by per-path counts over the
stored histories, e.g. `paths: search=2 reuse=1 revise=2 template=2`.

maybe_promote and library.py are unchanged: revised cases are ordinary
concrete programs and take part in promotion as before.

## Out of scope

- Promotion of repair patterns (next brief).
- Multi-repair search (two or more constants changed), structural
  edits, and any use of a model as repair proposer (the sketch lists
  it as an option; this version is edit operations only, so runs stay
  deterministic).
- Any change to the template stage or to promotion semantics.

## Acceptance

`python3 demo.py`:

- All 7 tasks solve. Expected paths: search, search, reuse, revise
  (name-swap-semicolon), template (name-swap-pipe), revise
  (date-separator-dot), template (date-separator-underscore). If the
  actual paths differ, stop and report rather than tuning the demo.
- The revise solutions cost fewer candidates_tested than the search
  stage needed for the same tasks before this change (14 and 15).
- End state unchanged in shape: templates T1 (support 4) and T2
  (support 3); references 7/7.
- Every stored case carries a history; the two revise histories record
  exactly the separator edits (", " -> "; " across both field sites;
  "/" -> "." at the replace site).
- Histories survive a save/load round-trip; a case file without
  "history" still loads.
- No new magic numbers beyond REVISE_SOURCE_LIMIT (NOVEL comment);
  the Aamodt & Plaza citation sits at the revise stage.
