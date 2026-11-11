# Fix brief: repair-pattern promotion v1 — review fixes

Reviews: REVIEW-repair-promotion-code.md (all items clean; dedupe =
judgment call) and REVIEW-repair-promotion-semantic.md (Q1 adjudicated
for the implementation; 2 moderate, 3 minor). Implement the fixes
below. Everything not mentioned stays as it is. Append a "Fix round"
addendum to REPORT-repair-promotion.md with the changes and
re-verified numbers. Do not commit.

F1. Candidate-set fidelity (semantic finding Q4). The pattern's
replacement values are currently the target examples' OUTPUT
separators only, which cannot regenerate one of P1's own two
supporting wins (name-swap-semicolon replaced the source's input
separator ", " with the target's INPUT separator "; "). Change the
value/string pattern's candidate values to the target examples'
input-union-output separators — the same separator domain the value
tier uses (_task_separators). Literals stay "every distinct string
literal of the source". Update the pattern comment to state the
candidate set plainly (pattern candidates remain a subset of the
value tier's string-role candidates, so the dedupe accounting is
unchanged). Verify in the addendum: with P1 preloaded, the
semicolon configuration (source name-swap, name-swap-semicolon
examples) now has ", " -> "; " among the pattern candidates;
code-upper's pattern_tested stays 1 and the demo totals stay
11/14/1/4/1/13/7/22 = 73 with paths unchanged.

F2. Pattern support pruning (semantic finding Q3 asymmetry).
maintain() prunes removed task_ids from template support but not
from pattern support. Mirror it: on a committed removal, also
remove the task_id from every pattern's "support" list. No
dissolution. Demo behavior in this run is unchanged (the removed
case is in no pattern's support); verify that.

F3. Citation correction (semantic finding 5). The mining comment in
library.py attributes adaptation-knowledge reuse to Smyth & Keane
1998 (adaptation-guided retrieval), which is about retrieval
ranking. The on-point reference for learning adaptation rules from
a case base is: Hanney & Keane 1996, "Learning Adaptation Rules
from a Case-Base", EWCBR-96, LNCS 1168, pp. 179-192 (verified by
Muse against dblp and the EWCBR proceedings record). Rewrite the
comment to cite Hanney & Keane 1996 for the pattern-mining
mechanism, keeping any Smyth & Keane mention only where
adaptability-guided effort is actually meant, with the descent
marked. Do not touch the solver.py gate comment (already settled
last round).

F4. Report completeness (semantic findings Q1 residuals and §6).
The addendum records: (i) pattern neutrality is conditional — the
pattern pass is count-neutral only when no pattern candidate wins
and the budget does not bind; a pattern win REDUCES the count
(verified probe: 2 vs the baseline's 3 for the same configuration);
(ii) the neutrality argument in general form (pattern candidates
are a subset of the value tier's, per F1 still true after the
widening); (iii) the mined-but-not-applied set is everything except
(value, string), including possible future (value, int) and
(value, joiner) keys; (iv) F1-F3 above and their verification.

Acknowledged non-fixes (record in the addendum as known v1 limits,
no code change): the pattern key discards the learned content
(observed from/to values, input-side vs output-side), so (value,
string) is one slot forever and support counts the edit class, not
the pattern's own wins (semantic Q2/Q4); win-only mining with no
dissolution is a ratchet whose failure side is recorded
(pattern_tested) but unmined (semantic Q3). These are the next
round's design inputs, listed in the status doc.

Re-verify after fixes and report in the addendum: demo 8/8, paths
unchanged, per-task candidates unchanged (total 73), P1 promotion
point and support unchanged, code-upper pattern_tested = 1, maintain
decision and competence 8/8 unchanged, demo output byte-identical
across two runs (new hash), library round-trip with patterns
intact, semicolon-configuration probe from F1.
