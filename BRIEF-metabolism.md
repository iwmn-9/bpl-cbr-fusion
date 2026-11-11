# Brief: complete attempt records, an execution-eligibility gate for structural
# repair, admission labels, usage statistics, and competence-preserving
# case-base maintenance

Context: entry 001 (see docs/entry-001-sketch.md). A design review (recorded in
docs/entry-001-representation-cost.md and the project discussion) concluded
that the system's remaining failures trace back to missing measures and
missing records: histories store only the winning edit, failed attempts and
their costs are discarded, structural repair enumerates blindly, promotion is
the only compression event, and nothing is ever forgotten. This brief builds
the metabolism underneath those questions, in dependency order: complete
records first, then the one gate the records already justify, then retention
with statistics distilled before any deletion.

Design decisions made by the brief author, with the evidence. Do not relitigate
them silently; flag disagreements in the report instead.

1. The structural-repair gate is ELIGIBILITY BY EXECUTION, not a tuned
   threshold and not a partial-progress test. Measured on the current demo
   (replay of all 8 tasks): the one pathological bill, date-separator's 88
   structural+value candidates, comes from a source program (name-swap) that
   raises DslError on every target input. The one structural win, code-upper's
   swap, comes from a source that executes cleanly on all target inputs but
   whose value tier shows NO partial progress (no value candidate passes more
   examples than the source). A partial-progress gate would therefore block
   the demo's only structural win; an execution-eligibility gate blocks
   exactly the waste. Rule: for each revise source, always run the value
   tier; run the structural tiers (swap, insert, remove) only if the source
   program executes without DslError on EVERY target example input.
2. Retrieval ranking is NOT changed in this round. The natural experiment in
   the demo cuts the other way: for name-swap-semicolon, the winning source
   (name-swap) errors on the target inputs, so ranking by output distance
   would demote the winner below a source whose repair bill is 45 wasted
   candidates. Ranking by adaptability is the documented direction
   (adaptation-guided retrieval: Smyth & Keane 1998), but the ranking key
   must be chosen from recorded outcome data, which this round starts
   collecting (per-source behavioral distance and outcomes, below). Deferring
   the ranking change is deliberate; silently changing it anyway is a defect.
3. The MDL acceptance gate for promotion is also deferred (storage-vs-
   computation tradeoff unresolved). Not in scope.

## Requirements

R1. Attempt records. solve() records every stage attempt, in order, into
report["attempts"], a list of JSON-native dicts:
- template: {"stage", "tested", "outcome" ("win"|"miss"), "template"}
  (template id on win, else None). One entry for the whole template stage.
- reuse: one entry per case tested in the reuse loop:
  {"stage", "source", "outcome", "first_failure"} where first_failure is
  None on win, else {"input", "expected", "actual"} for the FIRST failing
  example, with "actual" the program's output string, or None when the
  program raised DslError on that input. This is the raw failure
  observation the diagnosis discussion requires; do not reduce it to a
  boolean.
- revise: one entry per source attempted:
  {"stage", "source", "tested", "outcome", "value_tested",
   "structural_tested", "gated"} where "gated" is True when the structural
  tiers were skipped under the eligibility rule (R2). Counts must sum:
  value_tested + structural_tested == tested for the source.
- search: {"stage", "tested", "outcome"}.
History keeps the attempts (demo already stores report minus "reason";
no schema filtering). Reports for unsolved tasks also carry attempts.

R2. Execution-eligibility gate in _revise: value tier always; structural
tiers only when the source program executes without DslError on every
target example input. The shared REVISE_CANDIDATE_LIMIT budget semantics
are unchanged (gate-skipped candidates are never generated, so they cost
nothing and consume no budget). The existing budget comment stays accurate;
add a comment at the gate citing Smyth & Keane 1998 (adaptation-guided
retrieval) for ranking/gating repair effort by adaptability, and stating
the measured demo evidence (gate blocks the 88-candidate enumeration from
a non-executing source; the code-upper swap source executes cleanly).
Also record in each revise attempt the source program's behavioral
distance to the target: {"behavior": {"passed": int, "errors": int}}
(counts over the target examples) — mining data for the deferred ranking
decision, recorded but NOT used for ordering this round.

R3. Admission labels. Add solver-level helper
classify_admission(examples, case_base, library) -> "absorbed" |
"redundant" | "novel": "absorbed" when a library template solves the
examples (test via the existing template machinery, zero search), else
"redundant" when some existing case's materialized program matches the
examples, else "novel". demo.py calls it BEFORE adding each solved case
(against the pre-add base and library) and stores the result as
case["admission"]. Admission is a label this round; R5 consumes it.

R4. Usage statistics. Each case gains "stats":
{"reuse_tested": int, "reuse_wins": int, "revise_attempts": int,
"revise_wins": int}, all starting at 0. demo.py updates stats after each
solve from report["attempts"]: for each reuse attempt, the source case's
reuse_tested += 1 (and reuse_wins += 1 on win); for each revise attempt,
revise_attempts += 1 (and revise_wins += 1 on win). cases.py round-trips
"stats" and "admission" exactly like "history". Old files without the new
keys load fine (keys absent, stats treated as absent until set).

R5. Competence-preserving maintenance. Add maintain(case_base, library)
to solver.py: for each case whose admission is "redundant", tentatively
remove it and re-solve EVERY remaining case's examples plus the removed
case's examples against the reduced base and library; commit the removal
only if every task still solves (any path). Otherwise restore the case.
Return a list of decision strings, one per candidate, e.g.
"removed <task_id> (redundant, corpus still solvable)" or
"kept <task_id> (removal breaks <task_id>)". Comment citing the CBR
utility problem (Smyth & Cunningham 1996): an ever-growing case base
degrades retrieval, so retention must be earned; statistics (R4) are the
distilled record that survives deletion. demo.py calls maintain() after
the task loop, prints each decision, then re-solves all 8 demo tasks
against the maintained base as a competence check and prints
"competence check: X/8".

R6. demo.py output additions, kept minimal and in the existing style:
per task, one line "admission: <label>"; after the loop, the maintain()
decisions and the competence-check line; in the library summary section,
one line "stats: " followed by per-case compact stats
"<task_id>(rt=<reuse_tested>, rw=<reuse_wins>, ra=<revise_attempts>,
rw2=<revise_wins>)" — pick readable abbreviations and use them
consistently. Everything else about demo output stays as it is.

## Non-goals (explicit)

- No change to retrieval ranking order (decision 2 above).
- No MDL gate on promotion; no change to library.py promotion logic.
- No multi-edit repairs; no new DSL ops; no benchmark code.
- No deletion of "absorbed" or "novel" cases in maintain() this round.

## Invariants and verification (report all of these)

1. Baseline first: run demo.py at HEAD (commit bf3bfc03) and capture the
   per-task path/candidates table (expected: paths
   search/search/reuse/revise/template/revise/template/revise; candidates
   11/94/1/4/1/13/7/22). After the change: 8/8 solved, paths IDENTICAL,
   and the ONLY candidate change is date-separator 94 -> 14
   (1 reuse + 8 value + 0 structural + 5 search). Any other difference
   must be explained in the report, not silently accepted.
2. saved cases JSON (demo's temp files are discarded; reproduce by a
   small run or a test snippet) shows attempts for every case, including
   miss entries: date-separator's case must show a reuse miss with a
   first_failure whose "actual" is None (DslError), and a revise attempt
   with gated == True and structural_tested == 0.
3. code-upper's case shows a revise attempt with gated == False and a
   swap win (structural_tested > 0).
4. Stats consistency: sum of revise_wins over cases == number of
   revise-path solves (3); sum of reuse_wins == reuse-path solves (1);
   every case has stats and admission after the demo.
5. maintain() decisions printed; competence check prints 8/8. Report
   which cases were removal candidates and the decisions verbatim.
6. Determinism: demo.py output byte-identical across two runs (modulo
   nothing). Use a hash to show it.
7. Library size accounting: report the new net size delta; histories
   grow because attempts are retained — state the delta and the
   per-case history growth honestly. No target value; concealment is
   the defect.
8. Stdlib only; no new numeric constants except structural ones, which
   must carry NOVEL comments; zero new tuned thresholds (the gate is
   boolean by construction).

Write the report as REPORT-metabolism.md in the repo root: what was
implemented per requirement, the before/after table, the verification
results above, and any place where the code and this brief diverge.
