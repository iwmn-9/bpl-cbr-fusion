# Code review brief: repair-pattern promotion v1

Review the implementation of BRIEF-repair-promotion.md (see
REPORT-repair-promotion.md for the implementer's account). Write
findings to REVIEW-repair-promotion-code.md. Do not modify code. Do not
commit.

Verify from the code, not the report:
1. Mining: key abstraction for all four edit shapes exactly as briefed;
   support = distinct task_ids; promotion threshold is the existing
   MIN_SUPPORT_CASES; pattern IDs monotonic, never reused, persisted
   and correctly derived for old files; re-running mining updates
   support in place and never duplicates; patterns never dissolved.
2. Persistence: Library round-trips patterns; a stored file without
   "patterns" loads as []; template behavior unchanged.
3. Application: pattern pass runs before tier enumeration inside
   revise; order = support size desc, then pattern_id asc; trigger
   conditions for the value/string pattern match the brief (source has
   a string literal; target output separators non-empty); candidates
   count toward candidates_tested and the shared budget;
   "pattern_tested" lands on the revise attempt; a pattern win puts
   "pattern_id" on the winning edit record; swap/insert/remove
   patterns are mined but not applied (no speculative machinery).
4. DEDUPE — read the actual implementation and state precisely what is
   deduped against what. Known tension to adjudicate: in code-upper's
   revise, the pattern candidate program also arises from a later
   tier generator, so strict global dedupe by canonical JSON would
   give 21 candidates, not the briefed 22. The brief demanded both
   "tested once" and "baseline totals must not move". Report which
   occurrences the code dedupes, which it still tests, and whether
   any program can be executed twice within one revise call through
   paths the dedupe does not cover (e.g. across sources, across
   tiers, pattern-vs-pattern).
5. Non-goals: ranking, templates, admission, maintain, and the
   execution-eligibility gate are behaviorally unchanged; demo output
   unchanged apart from the pattern lines and the size figure.
6. Determinism: demo output byte-identical across two runs (report
   the hash you observe).

Close with an explicit verdict per item: clean / defect (with the
smallest reproducing observation) / judgment call for the semantic
review.
