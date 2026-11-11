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
- Benchmarks: established benchmarks with validated effectiveness are the
  default, and claims rest on them, never on self-made tasks. Self-made
  tasks are for iteration only. A custom benchmark is admissible only
  when the claim's novelty is high enough that no established benchmark
  can measure it, and that justification must be written down where the
  benchmark is introduced. Reviewers must audit benchmark choice for
  self-serving selection (tasks or subsets chosen because the method
  wins on them); a failed audit blocks the claim. Current anchors:
  SyGuS-Comp PBE-Strings track, FlashFill / PROSE tasks (incl.
  FlashFill++), RobustFill, DreamCoder library-learning domains.
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

## Project state (as of 2026-11-11)

- The sketch is `docs/entry-001-sketch.md` (source of truth for the
  hypothesis and architecture). Implementation status and the recorded
  divergence from the sketch live in `docs/entry-001-status.md`.
- Implemented and review-settled: string-transformation skeleton
  (dsl / cases / solver / demo), promotion v1 (anti-unification
  templates in library.py), the revise step with repair history
  (tiered value / swap / insert / remove edits in solver.py; cases
  carry history records), and the metabolism round (complete attempt
  records in report["attempts"], an execution-eligibility gate on
  structural repair tiers, admission labels, usage statistics, and
  competence-preserving case-base maintenance with tombstone
  records), and repair-pattern promotion v1 (winning edits mined
  from case histories into library.patterns; value/string patterns
  applied before tier enumeration in revise with scoped dedupe).
  Language is Python; the experiment domain is string
  transformation.
- Review setup: coder = DeepSeek V4.1 Flash (`headless` profile);
  code reviewer = Kimi K2.7 Code (`reviewer` profile); semantic
  reviewer = GLM-5.2 (`semantic` profile). Review briefs include the
  benchmark-selection audit from the Benchmarks rule above.

## Commits and documentation

- dsh sessions never commit or push. Muse (the main agent) owns all
  GitHub operations after the review cycle settles (user decision,
  2026-11-10).
- Documentation (docs/, the project Space) is updated at milestones —
  a settled review cycle, benchmark results, a design decision made or
  reversed — not on every change. Commit messages carry the
  per-change record.

## Scope and safety

- Work only inside this repository's checkout (or the single directory named
  in the task).
- No writes to other repositories without the user's approval.
- No secrets in files or configs. API keys come from the launcher
  environment only.
- GPU work goes through the Colab CLI; end each session when done.
