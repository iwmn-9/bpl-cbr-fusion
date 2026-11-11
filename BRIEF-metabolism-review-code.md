# Review brief (code): metabolism round — attempt records, eligibility gate,
# admission, stats, maintenance

You are the code reviewer. Read BRIEF-metabolism.md (the spec),
REPORT-metabolism.md (the implementer's claims), and the changed code
(solver.py, cases.py, demo.py; library.py and dsl.py should be unchanged).
Verify the implementation against the spec by reading code and, where a
claim is checkable, by running small probes. Do NOT modify code. Write
findings to REVIEW-metabolism-code.md, ordered by severity, each with
file/line evidence and a concrete failure scenario where applicable.
State explicitly when a checked item is clean.

Check at least:
1. Attempts schema: all four stage entry shapes exactly as specified in
   R1; counts consistency (value_tested + structural_tested == tested per
   revise attempt; stage tested counts sum to solve()'s returned total);
   first_failure is the FIRST failing example with actual=None exactly
   when the program raised DslError on that input (probe a case where the
   program runs but mismatches, and one where it errors).
2. The gate: structural tiers are generated iff the source program runs
   without DslError on EVERY target input; the value tier always runs;
   gate-skipped candidates consume no REVISE_CANDIDATE_LIMIT budget;
   early budget exhaustion mid-source still behaves as before.
3. classify_admission: "absorbed" uses the template machinery with no
   search; "redundant" materializes referenced cases correctly; ordering
   (absorbed checked before redundant); behavior when library is None.
4. Stats: exactly-once updates per solve (a case appearing in multiple
   attempts of one solve; a case that is both reuse-tested and a revise
   source in the same solve); cases.py round-trips stats/admission;
   pre-change files (no new keys) load without error.
5. maintain(): tentative removal truly isolates the candidate (no
   mutation leaks on restore); the re-solve covers every corpus task plus
   the removed one; decision strings match R5's format; a case whose
   removal would break another task's solve is kept (construct or reason
   about such a scenario).
6. Non-goals: _rank_cases and token-overlap logic unchanged; library.py
   byte-identical to before (no git here — judge by content: promotion
   logic untouched); no new dependencies; no new tuned numeric constants.
7. Determinism hazards: set/dict iteration order anywhere in the new
   code paths (attempts, stats printing, maintain order).
8. Known wrinkles to assess, not excuse: (a) the removed case's stats
   are deleted with it — does any code path or invariant break?
   (b) library template "support" still lists the removed case — trace
   every consumer of support (slot domains, promotion, materialize) and
   state whether the stale entry is inert or a live bug.
