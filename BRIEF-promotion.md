# Brief: promotion (昇格) — anti-unification into a template library

For the implementing AI session (dsh, DeepSeek V4.1 Flash, reasoning MAX).
Repo rules are in AGENTS.md; they win over this brief on any conflict.
Work only in this directory. Do not touch BRIEF-promotion.md itself.

## Goal

Add step 5 of the sketch's architecture (docs/entry-001-sketch.md):
when solved cases recur with the same program skeleton, abstract the
skeleton into a reusable template (型) in a library, and let the solver
instantiate templates before falling back to exact reuse or search.
Covered cases are stored as template references (compression).

Method: anti-unification (least general generalization, Plotkin 1970) —
the same family of move as DreamCoder's library learning (Ellis et al.
2021), minus the neural parts. Cite both in one short comment where the
algorithm lives.

## Design

### library.py (new module)

- A template is a program in dsl.py's shape whose literal arguments may
  be slots. Represent a slot inside program data as {"slot": <name>}.
  Slots may appear: as an op argument (separator, replace old/new,
  slice bounds) and as the joiner.
- `anti_unify(program_a, program_b)` -> template or None.
  Returns None unless both programs have the same number of extractors,
  equal chain lengths, and equal op names/arities position by position.
  Per argument position: equal literals stay literal; differing literals
  become a slot. Slot identity is consistent: the same (value_a,
  value_b) pair always maps to the same slot name, across the whole
  program (both field ops in a name-swap share one separator slot).
  The joiner is anti-unified the same way.
- `instantiate(template, bindings)` -> concrete program (plain dsl.py
  shape), substituting every slot. `slots_of(template)` -> slot names.
- `class Library`: holds templates [{id, skeleton, support: [task_id]}],
  load/save as JSON next to the case base file. Ids: T1, T2, ... in
  creation order.
- `maybe_promote(case_base, library)` -> list of promotion event strings.
  For the most recently added case (or: check all pairs involving the
  newest case — keep it simple and deterministic), anti-unify its
  program against every earlier case's program and every existing
  template's skeleton (anti-unifying a template with a program
  generalizes the template further; slots already present stay slots).
  A template is created/updated when the anti-unification covers at
  least MIN_SUPPORT_CASES distinct cases. On promotion:
  - register the template with support = covered task_ids;
  - rewrite each covered case to a reference {template_id, bindings}
    (bindings = the case's own slot values);
  - invariant, verify before rewriting: instantiating the template
    with each covered case's bindings reproduces that case's original
    program exactly. If verification fails, do not promote.
- MIN_SUPPORT_CASES = 2, marked NOVEL (smallest count that evidences
  recurrence; tunable).

### cases.py

- A case gains optional fields template_id and bindings. When present,
  "program" may be absent from storage; `all()` still returns cases,
  and materialization happens through a helper in library.py:
  `materialize(case, library)` -> concrete program. Cases without a
  reference behave exactly as today. Keep load/save symmetric.

### solver.py

- solve(examples, case_base, library=None) returns
  (program, path, candidates_tested). Path order:
  1. "template": for each template, enumerate candidate bindings and
     test instantiated programs. Slot domains: string slots take the
     task's observed separators (inputs and outputs, reuse the existing
     separator observation; cap MAX_OBSERVED_SEPARATORS applies) plus
     "" for a joiner slot; integer slots take 0..FIELD_INDEX_LIMIT-1.
     Bindings must be consistent (one value per slot per program).
  2. "reuse": as today, over materialized case programs.
  3. "search": as today.
  candidates_tested counts every program tested against the examples
  across all paths, so path costs are comparable.
- With library=None, behavior must match the current solver except the
  extra return value. Update demo.py accordingly.

### demo.py

- Keep the existing three tasks first, in order (regression anchor).
  Then append, in order:
  - "name-swap-semicolon": ["Tanaka; Taro", "Taro Tanaka"],
    ["Suzuki; Hanako", "Hanako Suzuki"]
  - "name-swap-pipe": ["Kim | Jiwoo", "Jiwoo Kim"],
    ["Lee | Minjun", "Minjun Lee"]
  - "date-separator-dot": ["2026-11-10", "2026.11.10"],
    ["2025-01-05", "2025.01.05"]
  - "date-separator-underscore": ["2026-11-10", "2026_11_10"],
    ["2025-01-05", "2025_01_05"]
- After each solved task: add the case, run maybe_promote, print any
  promotion events. Print candidates_tested per task.
- End: print library summary — template count, each template's support
  size, and compression: cases stored as references / total cases.
- Expected outcome (acceptance): name-swap-pipe solves via "template";
  date-separator-underscore solves via "template"; two templates exist
  at the end; the original three tasks still solve with the same paths
  as before (reuse for name-swap-new).

## Constraints

- Python stdlib only. Keep modules small and flat; library.py owns
  templates, cases.py owns storage, solver.py owns solving.
- No magic numbers: new constants get a paper citation or a NOVEL
  comment at the definition site.
- No redundant comments/docstrings (AGENTS.md).
- `python3 demo.py` must run clean end to end.
