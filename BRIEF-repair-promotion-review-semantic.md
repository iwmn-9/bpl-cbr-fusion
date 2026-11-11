# Semantic review brief: repair-pattern promotion v1

Review the implementation of BRIEF-repair-promotion.md against
docs/entry-001-sketch.md, docs/entry-001-status.md, and
REPORT-repair-promotion.md. Write findings to
REVIEW-repair-promotion-semantic.md, ordered by severity. Do not
modify code. Do not commit.

Questions:
1. THE DEDUPE TENSION (adjudicate this first). The brief demanded
   both "a pattern candidate the tiers would also generate must be
   tested once (canonical-JSON dedupe)" and "baseline demo totals
   must not move (code-upper stays 22)". In code-upper's revise, the
   pattern candidate program ALSO arises from a structural tier
   generator (a different edit yielding the same program), so the two
   demands conflict: strict dedupe gives 21. The implementer chose a
   scoped dedupe and documented the interpretation in the report.
   Judge: (a) What does candidates_tested actually count in this
   codebase — distinct programs, or generator attempts (the baseline
   counted the structural duplicate too)? (b) Is the implemented
   scope principled under that reading, or a fudge to hit 22?
   (c) Is the report's account of it honest and complete? (d) Is this
   a defect of the brief (both demands unsatisfiable together), of
   the implementation, or of the counting semantics — and what is the
   smallest faithful resolution?
2. Is the promoted P1 a genuine "part" in the sketch's sense — a
   repair pattern with an applicability condition, stored in the
   library and consulted by solve — or is it, in substance, a
   reordering hint for the value tier? State what would distinguish
   the two and which one this is. Note the honest context: on this
   demo its measured effect is zero candidates.
3. Survivorship: mining reads only winning edits. Failed pattern
   applications are recorded (pattern_tested, attempts) but never
   mined, so a pattern's support can only grow. Is that acceptable
   for v1 given patterns cannot be dissolved, or does it need a
   recorded caveat in the status doc?
4. Trigger fidelity: the value/string trigger (source has a string
   literal; target outputs have separators) and its candidate set
   (output separators only) — is that the abstraction the two
   supporting wins actually share, or broader/narrower than the
   evidence? What does the pattern do on sources whose string
   literals are not separators?
5. Status doc: supply drop-in Japanese replacement text for
   docs/entry-001-status.md covering this milestone: a new 実装済み
   bullet for repair-pattern promotion (mining, store, application,
   dedupe semantics as adjudicated in Q1), the 実測 additions
   (P1 promoted with support 2 after date-separator-dot; swap key at
   support 1 unpromoted; demo totals unchanged at 73; size delta now
   +477 B with the pattern store's share identified; pattern effect
   on this demo = zero candidates, stated plainly), and the updated
   差分/次の候補 (repair-pattern promotion is now implemented for the
   value class only; structural patterns mined-but-not-applied;
   negative-evidence mining still open).

Reproduce the key numbers independently (demo run, pattern promotion
point, code-upper pattern_tested and total) before answering.
