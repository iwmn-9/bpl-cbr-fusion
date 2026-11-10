# AGENTS.md — rules for AI sessions working on bpl-cbr-fusion

Reader: the next AI session, not a human reviewer. No human reads this code
in review. Write so a later AI (same setup: DeepSeek V4.1 Flash, reasoning
MAX, via dsh) can pick the work up cold. Human readability is a floor, not
the goal: names and structure should make sense to a person at a glance,
but optimize for the next AI.

## Code rules

- Structure for AI comprehension: flat, explicit data flow. One module = one
  responsibility. Small files, clear names, minimal indirection. No deep
  inheritance, magic dispatch, implicit global state, or clever
  metaprogramming.
- No design that becomes untraceable. If following the code costs more
  context than the task is worth, the design is wrong. Prefer boring,
  explicit code over compact clever code.
- No redundant explanation. No tutorial comments, no restating what the code
  already says, no docstring that repeats the signature. Comment only where
  intent is not obvious from the code: non-obvious invariants, trade-offs,
  external quirks.
- Keep context consumption low: short functions, narrow interfaces, no giant
  files, no duplicated logic that forces the reader to diff copies.

## Model and division of labour

- All implementation work: DeepSeek V4.1 Flash (1017), reasoning MAX,
  unified. Do not switch models per task unless the user says so.
- dsh has no web search. Research and paper hunting are Muse's job; dsh
  implements from the brief Muse supplies. If a task needs a paper, a
  benchmark, or an external fact, ask Muse — do not guess it.
- Benchmarks: compare on established benchmarks used by similar papers, not
  on self-made tests alone. Self-made tasks are for iteration; external
  benchmarks are for claims. Current anchors: SyGuS-Comp PBE-Strings track,
  FlashFill / PROSE tasks (incl. FlashFill++), RobustFill, DreamCoder
  library-learning domains.
- Cross-domain methods: reuse freely. If a technique from another field fits
  (library learning, enumerative synthesis, neural synthesis, CBR
  retrieval), use it and note its source paper in the task notes.

## Numbers and documents

- No magic numbers, as a rule. Every numeric constant that comes from a
  paper or an empirical result carries a comment at its definition site
  citing the source paper. A constant that is this project's own novel
  design choice is the exception: mark it with a `NOVEL:` comment so the
  next AI knows it is a tunable decision of ours, not a derived value.
  Bare unexplained literals in logic are not acceptable either way.
- Human-facing documents (design sketches, paper notes, reading summaries,
  anything written for the user rather than for an AI session) live under
  `docs/`. Code-adjacent notes for AI sessions stay next to the code.

## Project state (as of 2026-11-10)

- Design-sketch stage. The sketch is `docs/entry-001-sketch.md`; it is the
  current source of truth for the hypothesis and architecture.
- Provisional, user may override: prototype language is Python; the first
  experiment domain is string transformation (FlashFill-style), not yet
  decided.

## Scope and safety

- Work only inside this repository's checkout (or the single directory named
  in the task).
- No writes to other repositories without the user's approval.
- No secrets in files or configs. API keys come from the launcher
  environment only.
- GPU work goes through the Colab CLI; end each session when done.
