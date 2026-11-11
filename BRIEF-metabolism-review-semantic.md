# Review brief (semantic): metabolism round — do the claims, comments, and
# design readings match what was asked and what the code does?

You are the semantic reviewer. Read BRIEF-metabolism.md (the spec and its
stated design decisions), REPORT-metabolism.md (the implementer's
claims), docs/entry-001-representation-cost.md (the position memo this
round implements), and the changed code (solver.py, cases.py, demo.py).
Judge fidelity between words and mechanisms. Do NOT modify code. Write
findings to REVIEW-metabolism-semantic.md, ordered by severity.

Judge at least:
1. The gate comment: does it claim exactly what the mechanism does (no
   more, no less)? Is the Smyth & Keane 1998 citation used accurately
   (adaptation-guided retrieval is about ranking/gating by adaptability;
   here it gates structural effort by executability — is that a fair
   descendant or a stretch)?
2. "Statistics survive deletion": the brief (R5 comment text) motivates
   stats as the distilled record that survives deletion, but the
   implementation deletes the removed case's stats along with the case.
   Divergence from the brief's rationale? Severity, and the minimal
   faithful fix (e.g., aggregate tombstone stats retained on the case
   base). Also: template "support" still lists the removed case, which
   the implementer calls provenance — defensible reading or stale
   pointer? What does the status doc / sketch call support?
3. Size accounting: the demo prints net +962 B while the like-for-like
   delta is +193 B because the all-concrete baseline omits stats and
   admission (fields that exist in both representations). Is the printed
   line now misleading as a headline? Should the baseline construction
   include stats/admission for like-for-like (as history already is)?
   Recommend a reading the status doc can state without caveat-stacking.
4. behavior {"passed", "errors"} as mining data for the deferred
   ranking decision: is exact-match pass count the datum the design
   discussion wanted (adaptability evidence), or does it conflate
   "source already solves it" with "source is close"? What is missing
   for the future ranking choice to be decidable from these records?
5. Admission labels: do "absorbed"/"redundant"/"novel" as implemented
   match the retention discussion (admission at the gate, labels before
   storage)? Any label whose implemented meaning will mislead a future
   reader of the case file?
6. Status doc: docs/entry-001-status.md now needs this milestone.
   Supply drop-in replacement text (Japanese, same style as the current
   document) for: the solve-order/mechanism description if affected,
   the demo metrics paragraph (new totals: 73 candidates, date-separator
   14, total size delta with the honest decomposition), and the
   divergences/next-candidates section — the record/measure/gate/
   retention gaps this round closed, and what remains open (ranking
   decision pending recorded data, MDL gate deferred, repair-pattern
   promotion still unimplemented, failure localization still limited to
   first-failure observation).
