# Review brief: semantic review of the revise implementation

For the reviewing AI session (dsh profile `semantic`, GLM-5.2). You
are reviewing meaning and claims, not hunting code bugs. Do not edit
any file.

## Scope and sources of truth

- docs/entry-001-sketch.md: the hypothesis and architecture (step 3
  is 適用・修正; the case schema is 問題、プログラム、実行結果、修正履歴;
  step 5 promotes recurring REPAIR PATTERNS into library PARTS).
- docs/entry-001-status.md: the recorded divergence as of the last
  milestone (revise step absent; promotion abstracts solution
  skeletons, not repair patterns). This document is now partly stale;
  part of your job is to say exactly which of its statements the new
  code makes false, and to propose replacement wording.
- BRIEF-revise.md and BRIEF-revise-parts.md: what was asked.
- solver.py / cases.py / demo.py: what was built.

## Questions to answer

1. Fidelity: does the implemented revise match the sketch's step 3
   and the briefs? Where the briefs themselves narrowed or shifted
   the sketch (e.g. edit-operations only, no model proposer; tier
   order; budget), name it explicitly — brief-vs-sketch divergence
   is a finding, as it was last round.
2. The history contract: promotion of repair patterns (the next
   step) will consume these edit records. Are they complete and
   replayable enough to abstract patterns from — could you, given
   only the stored histories, reconstruct what changed and detect a
   recurring pattern across cases? What is missing, if anything?
3. Honest costs: date-separator now spends 88 revise tests before
   falling to search (total 94 vs 6 in the very first skeleton).
   Is the design's "cheap repairs first" story still honest? Is the
   reporting (demo, briefs) candid about this tax, and does the
   budget mechanism actually answer it or merely cap it?
4. Demonstration validity: code-upper is claimed to be solvable ONLY
   via a structural swap (search never generates upper; tier 1 keeps
   the op). Verify this claim from the code (search inventory, tier
   definitions). Also judge: do the 8 demo tasks, taken together,
   evidence anything beyond mechanism? State precisely what the demo
   does and does not show.
5. Citations in code comments: Aamodt & Plaza 1994 (CBR cycle),
   Jha et al. 2010 (component-based synthesis), Koza 1992 (GP
   mutation). Judge whether each citation's placement and implied
   claim are accurate in scope. (Verifying the papers themselves is
   Muse's job, not yours; judge the usage, flag overreach.)
6. The remaining divergence: after this change, what still separates
   the system from the sketch's step 5 (repair patterns promoted to
   parts)? Is the path from here to there actually shorter, and does
   anything in the current design obstruct it?

## Report format

Findings numbered, most severe first, each tied to a source (file
and line, or sketch/status section). For question on the status doc,
include concrete replacement wording for the statements that are now
false. Separate "code diverges from brief" from "brief diverges from
sketch" from "claims outrun evidence".
