# Semantic review: repair-pattern promotion v1

Reviewer: GLM-5.2 (`semantic` profile), per
`BRIEF-repair-promotion-review-semantic.md`.

Inputs judged: `BRIEF-repair-promotion.md` (spec), the implementation
(`library.py`, `solver.py`, `demo.py`; `cases.py`/`dsl.py` read and confirmed
untouched), `REPORT-repair-promotion.md` (implementer's claims),
`docs/entry-001-status.md`, `docs/entry-001-sketch.md`, and the prior review
`REVIEW-metabolism-semantic.md` for the established counting/support
conventions.

Method: read everything first, then reproduced the key numbers before
answering — the demo twice (byte-identical, `sha256`
`2386b94d…79e3ba4`), a persistent-state capture (output again identical),
a generator-level dump of code-upper's revise candidates, and two
counterfactual demo runs built by monkeypatching `solver._revise` from
outside the repo: (b) the pre-round revise (no pattern pass, no absorb) and
(c) the brief's literal global-dedupe reading (one whole-call canonical-JSON
key set, never removed). Probes then covered the pattern-win branch, the
subset relation on all four demo revise configurations, non-separator
literals, mining idempotence/shrink/growth, library round-trip, and the
old-format loads. Scratch work lives under `/tmp/semrp-*`; no repo code was
modified; nothing was committed (the checkout has no `.git`, as both reports
state).

Scale: **Moderate** = a words-vs-mechanism divergence that misleads about
what was built or mismeasures its own evidence if left in place; **Minor** =
precision/latent/documentation issue; **Note** = for the record. No critical
defect: every number in the report reproduces, the round meets its brief,
and the two Moderates below are design-level choices inherited from the
brief (which specified both the pattern key and the trigger/candidate set),
not implementation errors — but they determine what the next round should
build and what the status doc may claim, so they are recorded as findings.

Map to the review brief: Q1 (dedupe tension) → §1, adjudicated first as
instructed; Q2 (part or reordering hint) → §2; Q4 (trigger fidelity) → §3;
Q3 (survivorship) → §4; Q5 (status-doc text) → §8. §5–§6 are residuals
found during adjudication.

Benchmark audit (AGENTS.md): this round makes no benchmark claim — all
figures are on the self-made demo, and both the report and the drop-in text
below preserve the framing 自作デモは反復用の手応れであって主張の証拠ではない.
Nothing for the selection audit to reject.

---

## 1. Q1 — THE DEDUPE TENSION, adjudicated

**(a) What `candidates_tested` counts: test events, not distinct programs —
and it always has.** Three reproductions establish this:

- *Within one revise call, pre-round.* On code-upper's source
  (`replace("-","/")`), the value tier's first candidate (literal `"/"` →
  `"-"`) and the swap tier's 4th structural candidate
  (`["replace","-","/"]` → `["replace","-","-"]`) are the same canonical
  program `{"extractors":[[["replace","-","-"]]],"joiner":""}`. My
  pre-round reconstruction (b) confirms the report: that revise ran
  `value_tested=2, structural_tested=5` — the duplicate program tested
  twice. The report's phrase "the baseline counted the structural duplicate
  too" is verified.
- *Across stages, worse, and pre-existing.* Reconstructed from the exact
  pre-task-8 state: code-upper's 22 events cover only **13 distinct
  programs**. The template stage's 8 instantiations include 6 of the 7
  reuse-stage programs (structurally guaranteed: `_slot_domains` builds each
  slot domain from task separators *plus the support cases' own bindings*,
  so the template stage always re-enumerates covered support cases'
  programs, which the reuse stage then tests again); the name-swap program
  is tested 3× (template + `reuse:name-swap` + `reuse:name-swap-new`);
  `replace("-","-")` is additionally a T2 instantiation (`s1="-"`), so in
  the full enumeration it appears 3× (template + pattern/value + swap).
- *No dedupe anywhere else.* Nothing canonical-JSON-keys candidates across
  tiers, sources, or stages. The pattern-vs-tier absorb added this round is
  the first keying in the codebase.

So the frozen baseline "22" is an event count whose event multiset contains
duplicates; the value↔swap double-test the brief's parenthetical would
suppress is one instance of a pre-existing, structural property of the
metric. (The 73 was measured under this semantics last round; the metabolism
review's 94→14 arithmetic also mixes stages freely.)

**(b) Is the implemented scope principled, or a fudge to hit 22?
Principled — and it is the *unique* semantics satisfying both demands under
the event-count reading.** Two facts:

1. *Pattern ⊆ value tier, always.* Structurally: a pattern candidate is
   `_replace_literal(program, "string", sites(L), S)` for an output
   separator `S`; the value tier's domain `_task_separators` = input ∪
   output separators ⊇ output separators, with identical `_replace_literal`
   semantics and the identical `S != L` skip. Verified empirically: every
   pattern candidate on all four demo revise configurations
   (`in-value-tier=True` everywhere). Therefore "each pattern test absorbs
   one matching tier occurrence" (`solver.py:488-496`) makes the pattern
   pass a pure relabeling-plus-reordering of value-tier test events:
   **count-neutral by construction whenever no pattern candidate wins.**
2. *The alternative is not a no-op.* The brief's parenthetical ("the tier
   generators skip programs already tested in this revise call", keys never
   removed) also suppresses the pre-existing value↔swap double-count — a
   change to the *tiers'* own counting semantics smuggled in under a
   pattern brief. Verified by counterfactual (c): code-upper revise = 6
   (pattern 1 + value 1 + structural 4) → task **21**, total **72** — the
   exact 21 the brief's question cites.

So the implementer's choice is not "tune until 22 falls out"; it is "change
nothing that the 22 was measuring." The one arbitrary element — *which*
occurrence is absorbed (the first in tier order, i.e. the value-tier one) —
is deterministic, natural (the value tier runs first), and documented at
`solver.py:254-257`, `solver.py:489-490`, and report §Dedupe. Coverage of
the dedupe's blind spots, for the record: pattern-vs-pattern duplicates are
skipped (`solver.py:260-262`, currently unreachable — a duplicate would
need two patterns or colliding (literal, separator) pairs); pattern-vs-tier
is the scoped absorb; tier-vs-tier double-tests are *deliberately preserved*
(the baseline's own counts); across sources nothing is deduped (each
`_revise` call has a fresh absorb set — latent only, no demo revise runs a
second source).

Two boundary properties the chosen semantics has, which should be stated
wherever the 22/73 invariant is quoted:

- *A pattern win reduces the count below baseline.* Probed on task-6's
  configuration (source `replace("-","/")`, date-separator-dot examples,
  P1 loaded): the revise wins at pattern candidate #2
  (`tested=2, pattern_tested=2, value_tested=0`, edit carries
  `"pattern_id": "P1"`); the pre-round revise won at value candidate #3
  (`tested=3, value_tested=3`). Fewer tests to the same win — a
  improvement, not a defect — but "baseline totals must not move" is a
  property of this demo (no pattern wins), not an invariant of the
  mechanism.
- *Under budget pressure the pattern changes which programs are tested, not
  just their order* (it front-runs string→output-separator candidates ahead
  of the rest of the value domain). Unreachable at
  `REVISE_CANDIDATE_LIMIT=256` against ≤8 revise candidates here; worth one
  sentence of awareness before that budget is ever tightened.

**(c) Is the report's account honest and complete? Honest — yes: every
factual claim in §Dedupe and divergence 1 reproduced exactly (the two
generation sites, the absorbed occurrence, the surviving swap occurrence,
the 21/72 counterfactual, the 7-candidate equivalence). Complete — two
gaps,** graded Minor and folded into §6: the report's own pattern-win probe
(`tested=2`) is printed without the pre-round contrast (3), so a reader
cannot see that the win branch is exactly where "totals must not move"
breaks; and the general neutrality argument (pattern ⊆ value tier ⇒ no
added tests; counts move only downward, only on wins) is never stated — the
report argues only the code-upper instance. Plus one wording nit: "the same
seven programs are tested as before" is true as a multiset; it is six
distinct programs, one of them tested twice — which is precisely the
double-test under discussion, so the clause "…as a multiset (six distinct
programs)" would pre-empt the misreading. Same nit, one place over, in the
code comment `solver.py:256` ("so it is not tested twice" — within
code-upper it *is* tested twice, pattern + swap; the comment's next clause
discloses this, but a skimmer of the first clause is misled).

**(d) Whose defect, and the smallest faithful resolution? The brief's.**
Its two demands are jointly unsatisfiable as written: the baseline total it
freezes (22) already contains an intra-revise duplicated program, so the
parenthetical whole-call canonical-JSON skip entails 21. The counting
semantics itself (event counting) is the codebase's established,
cross-round-comparable metric; redefining `candidates_tested` as distinct
programs would silently re-baseline every historical number (153→73, the
per-task table, the gate's 94→14) and is not this round's decision to make.
The implementation is the smallest faithful resolution: keep event
counting; scope the dedupe to one absorbed tier occurrence per pattern
test; document the semantics — which the code comments do and the
status-doc text below now does. What the brief should have said:
"the tier generators skip *one occurrence* per pattern-tested program;
`candidates_tested` counts test events, so programs the tiers enumerate
more than once keep their baseline counts." If the project later wants a
distinct-program metric, it should be added as a *secondary* reported
number, not a redefinition (my code-upper measurement gives it: 22 events
= 13 distinct). No code change is required by this adjudication.

## 2. [Moderate] Q2 — the promoted P1 is, in substance, a reordering hint for the value tier, not a "part" in the sketch's sense

**What the sketch means by 部品.** Architecture item 5 (the 肝 of the
sketch): recurring repair patterns are promoted *into library parts*; item
2: when no case is retrieved, solutions are *synthesized from library
parts*. A part is library-stored, consulted when composing or adapting
solutions, and carries learned content.

**What P1 is, mechanically.** Stored: yes (`library.patterns`, persisted,
monotonic IDs — verified). Consulted: yes, but only by revise
(`_pattern_candidates` from `_revise`, `solver.py:258`), never by the
template or search stages. Learned content: a single bit plus a support
list. The key `(kind, role)` (`library.py:8-13`, `325-333`) discards
everything the two supporting wins actually knew — their from→to values
(`", "→"; "`, `"/"→"."`) and which side of the task each literal and
separator came from. The trigger, candidate generator, and ordering are
hardcoded in `_pattern_candidates`, identical for every value/string
pattern that can ever exist — and at most **one** value/string pattern can
ever exist (the key is kind+role, so the store holds one slot per edit
class; `maybe_promote_patterns` never creates a second pattern for a key
already present). The support-size ordering machinery
(`solver.py:461,484-485`) is therefore unreachable in effect, and support
itself has no post-promotion function at all: no dissolution (a promoted
pattern survives support=0 — verified), no candidate generation, no
ordering to break.

**The decisive property: no expressive power beyond the value tier.**
Provably and verified (§1(b).1): every pattern candidate is a value-tier
candidate. The pattern can never propose a program the tiers would not;
it changes the *order* in which a fixed candidate set is tried and relabels
a winner with `pattern_id`. The sketch's promise for this mechanism —
経験が貯まるほど系全体が軽くなる via patterns replacing raw history — is not
yet served: the pattern neither shrinks enumeration (front-running is
count-neutral without a win) nor compresses anything (the +136 B store is
additive).

**Measured effect on this demo: zero, plainly.** No pattern win anywhere;
net added candidates zero (the one application, code-upper's losing
candidate, absorbed a value-tier occurrence); the printed output of a run
with the pattern pass disabled is **byte-identical** to the real run
(verified — counterfactual (b)). Even the end-of-run competence re-solve
never exercises the pattern: by then templates and reuse cover all eight
tasks. P1's only observable trace in the whole run is
`pattern_tested: 1` inside one saved attempt record.

**What would distinguish a genuine part.** Any one of: (i) stored learned
content that generates candidates *outside* the tier domains — e.g.
carrying the observed substitution values (`"; "`, `"."`) as replacements,
which on a task whose separators exclude them would be genuinely new
candidates; (ii) a key fine enough to represent distinct abstractions
(input-side repair vs output-side repair — see §3), i.e. more than one
inhabitable slot; (iii) consultation at composition time (item 2), or (iv)
multi-edit repair patterns the single-edit tiers cannot express. All four
would let the pattern widen the reachable set rather than reorder it.

**Verdict.** This is a reordering hint — a prioritized subset of the value
tier, switched on by a recurrence flag, with a bookkeeping label. The
institutional seed is genuinely present, and it is the first end-to-end
instance of the sketch's item 5 (adaptation outcomes flowing into the
library and being consulted later): mine → store → consult → apply →
`pattern_id` on the edit → re-mine updates support. The claim to police is
wording: "the library now grows parts from repairs" is false in the
composition sense; "the library now records recurring repair classes and
front-runs their candidates inside revise" is accurate. The status text in
§8 says the latter.

## 3. [Moderate] Q4 — the trigger/candidate set is not the abstraction the two supporting wins share: broader than the evidence on one side, narrower on the other, and it regenerates only one of its own two wins

**The evidence.** The two supporting value wins:

- name-swap-semicolon: literal `", "` — the *source's input separator* —
  replaced by `"; "`, the *target's input separator*.
- date-separator-dot: literal `"/"` — the source's replace new-value, an
  *output-side* literal — replaced by `"."`, the target's *output
  separator*.

**What was implemented** (per the brief's own R3, faithfully): trigger =
source has any string literal ∧ target outputs have any separator;
candidates = literals × *output* separators only.

- *Literal side — broader than needed, but the breadth is forced.* Win 2's
  replaced literal is not a separator in the field-splitting sense, so
  conditioning on separator literals would have missed win 2; "any string
  literal" is the weakest condition covering both wins. The cost: the
  trigger is close to vacuous in this DSL — any source containing a
  field/replace op and any target whose outputs contain a non-word run
  qualify, i.e. nearly every revise call (probed: a `replace("Mr","")`
  source against outputs containing `", "` fires the pattern and proposes
  `"Mr"→", "` and `""→", "` — semantically unmotivated candidates,
  front-run *ahead* of the value tier's plausible repairs; count-neutral
  today, but prioritized noise, and budget-starving under a tight cap).
- *Replacement side — narrower than the evidence.* Output separators only.
  Probed on task-4's configuration (source name-swap, examples
  name-swap-semicolon): the pattern's sole candidate is `", "→" "` (the
  output separator), which loses; the actual winner `", "→"; "` (an input
  separator) is **not in the pattern's candidate set**. The two wins
  support two distinct finer abstractions — input-side repair (source
  input literal ← target input separator) and output-side repair (source
  output literal ← target output separator) — and the implemented blend
  (any literal ← output separator) regenerates only the date-separator-dot
  one.

So the brief's premise "The two value wins share one abstraction" is true
only at the *mined key* level (both are (value, string) edits); at the
*application* level it is false, and the support metric inherits the
confusion: **P1's support 2 is evidence that the (value, string) edit class
recurred twice, not that this pattern's trigger and candidates won twice**
— one of the two supporting wins is outside the pattern's own reach (this
is the ratchet mechanism of §4, stated concretely). This is a defect of
the brief's design (R3 specified both the key and the trigger/candidate
set), not of the implementation; the report documents the supports without
surfacing the mismatch (§6). The smallest evidence-faithful v2 candidate
set is literals × (input ∪ output) separators — which is exactly the value
tier's domain, i.e. the honest v1 statement is the one §2 makes: the
pattern adds prioritization, not coverage, and its support measures its
class, not itself.

## 4. [Minor] Q3 — survivorship: win-only, class-granularity ratchet; acceptable for v1, but the caveat must be recorded (supplied in §8), and one asymmetry with templates noted

Verified facts: mining reads only `history["edits"]` — winning edits
(`library.py:341-347`); failed pattern applications persist only as
`pattern_tested` counts in attempt records (saved values `[0,0,0,1]` —
which candidate failed is recoverable only by deterministic replay, which
the generators' determinism permits); support counts distinct task_ids per
key, so every future value/string revise win — *including wins this
pattern's candidates could never produce* (§3) — increments P1's support;
patterns are never dissolved (support=0 survives, verified); support drops
only when a supporting case leaves the base.

**The ratchet.** Because the key is the edit class, support grows with the
class's success, not the pattern's; combined with no dissolution, an
ineffective pattern is permanent and its recorded strength only rises.
That is acceptable for v1 — the brief explicitly deferred negative-evidence
mining (non-goal 2) and the report says so, and the failure counts *are*
being recorded for that later round — but it is exactly the kind of fact
the status doc exists to record. The drop-in 差分 text below states it
(support は「その編集クラスが勝った」ことであって「このパターンが効いた」ことではない).

**The asymmetry.** `maintain()` prunes removed task_ids from *template*
support (`solver.py:173-181`, the metabolism round's fix) but not from
*pattern* support. Self-healing exists — the next
`maybe_promote_patterns` recomputes support from live histories (verified:
dropping a supporter yields `updated P1 support=1`, later `support=0`) —
but nothing re-mines after `maintain()`, so the saved `library.json`
between maintain and the next run's first mining call can carry a dead
task_id in a pattern's support (and `_pattern_order` would sort on it).
Not triggered in this demo: the only removed case, name-swap-new, has no
edits and is not in P1's support (verified from the saved file). Smallest
fix, next round: prune pattern support in `maintain()` symmetrically with
templates. One more completeness note for the report: it names
swap/insert/remove as mined-but-not-applied, but value/int and
value/joiner patterns — possible future keys — would equally be
mined-but-not-applied; the unapplied set is "everything except
(value, string)".

## 5. [Minor] The new citation comment attributes the mechanism to the wrong paper in the line it invokes

`library.py:337-339`: "Adaptation knowledge is itself reusable case
knowledge (Smyth & Keane 1998, adaptation-guided retrieval): recurring
winning edits become patterns…". Smyth & Keane 1998 argues that *retrieval
ranking* should be guided by adaptability. The claim that adaptation
outcomes accrue into reusable learned rules — mining adaptation rules from
a case-base, which is exactly this round's mechanism — is the
adaptation-rule-learning line of Hanney & Keane (mid-1990s). The comment
inherits the brief's framing (the brief pointed at the citation "already
cited in solver.py"), so the imprecision is inherited, not invented; but as
written, a future session reading only the comment would misattribute the
mechanism to a paper about retrieval ranking — the same residual the
metabolism review flagged for the gate comment (its §4), and the fix is the
same: a descent marker ("the adaptation-knowledge-reuse line, cf. …") or
the on-point citation. The exact Hanney & Keane reference should be
confirmed through Muse before it is written into the code (no web access in
this review environment; per AGENTS.md the reviewer does not guess external
facts). The adjacent absorb-semantics comments (`solver.py:254-257`,
`489-490`) are accurate as written, subject to the one-clause nit in §1(c).

## 6. [Minor] Report completeness residuals (beyond §1(c))

1. **The support/application mismatch is invisible in the report.** §2
   documents P1's supports and the final edit-key tallies correctly, but
   never checks the applied candidate set against its own supporting wins;
   a reader concludes the pattern covers both. It covers one (§3). One
   sentence in the report's R3 section would close this.
2. **The win-branch count change is shown but not contrasted.** The §3
   probe (`tested=2, pattern_tested=2`) is printed without the pre-round
   equivalent (`tested=3, value_tested=3` — my probe), so the one boundary
   where "totals must not move" fails is left for the reader to derive.
3. **Wording nits in the double-testing region** (§1(c)): "the same seven
   programs" (multiset; six distinct) and `solver.py:256`'s "so it is not
   tested twice" (within code-upper it is — pattern + swap — as the
   comment's next clause discloses).
4. **Mined-but-not-applied set** under-names its own scope (§4): swap/
   insert/remove plus value/int and value/joiner.

Everything else in the report reproduced exactly — see §7.

## 7. Independent verification record

All re-run for this review; all match `REPORT-repair-promotion.md`:

- Demo: 8/8; paths `search/search/reuse/revise/template/revise/template/
  revise`; per-task candidates `11/14/1/4/1/13/7/22`, total **73**;
  two runs byte-identical, `sha256 2386b94d331851bf0efa15a36f5efe7ba0
  d8b764d3c043ee073bad3f979e3ba4` (the report claims determinism without
  stating a hash; this is mine). Promotion lines: T1/T2 as reported;
  `pattern: promoted P1 support=2: name-swap-semicolon, date-separator-dot`
  printed exactly once, immediately after the date-separator-dot block
  (T2's promotion line) — the promotion point is exact: the first
  value/string edit arrives at task 4 (support 1), the second at task 6
  (support 2 → promoted). No pattern events on any other task. Swap key:
  exactly one swap edit exists (code-upper's), support 1, never promoted;
  no insert/remove keys (3 winning edits total in all histories: 2 ×
  value/string, 1 × swap).
- code-upper revise attempt, saved verbatim:
  `{"tested": 7, "outcome": "win", "pattern_tested": 1, "value_tested": 1,
  "structural_tested": 5, "gated": false, "behavior": {"passed": 0,
  "errors": 0}}`; task total 22 = 8 template + 7 reuse + 7 revise (T1
  domain 4 + T2 domain 4 = 8 template tests, reconstructed from the exact
  pre-task-8 state). Winning edit is the ordinary swap record without
  `pattern_id`. Other three revise attempts all `pattern_tested=0`.
- Counterfactual (b) — pre-round revise (pattern pass disabled, mining
  intact): printed output **byte-identical** to the real run; code-upper
  revise `value_tested=2, structural_tested=5`; same winners, same edits,
  P1 still promoted with identical support. The pattern application is
  observationally invisible on this demo except in the saved attempt
  records.
- Counterfactual (c) — whole-call canonical-JSON dedupe (the brief's
  parenthetical): code-upper revise 6 (pattern 1 + value 1 + structural
  4), task **21**, total **72**; the run differs from the real one in
  exactly one line. The two brief demands are demonstrably jointly
  unsatisfiable.
- Generator-level: value↔swap canonical-JSON collision on code-upper's
  source = 1 program (`replace("-","-")`), value edit `"/"→"-"` vs swap
  edit `["replace","-","/"]→["replace","-","-"]`; structural order
  field-0/1/2, `replace("-","-")` (#4), `upper` (#5, winner). Full-solve
  event map: 22 events = **13 distinct programs**; duplicate families
  listed in §1(a).
- Pattern ⊆ value tier: verified on all four demo revise configurations
  (tasks 2, 4, 6, 8 sources/examples; `in-value-tier=True` for every
  pattern candidate), plus the structural argument in §1(b).
- Pattern-win branch (P1 loaded, task-6 configuration):
  `{"tested": 2, "pattern_tested": 2, "value_tested": 0}` with
  `"pattern_id": "P1"` on the winning edit — the report's probe
  reproduced; pre-round equivalent `tested=3, value_tested=3`.
- name-swap-semicolon counterfactual (Q4): pattern's only candidate on
  that configuration is `", "→" "` (loses); the winner `", "→"; "` is
  outside the candidate set. Non-separator-literal probe:
  `replace("Mr","")` source fires the pattern with `"Mr"→", "` and
  `""→", "`.
- Mining: second call on the final state returns `[]`, state deep-equal;
  support growth emits only `updated P1 support=3: …`; support drop to 1
  and to 0 updates in place (`updated P1 support=0`), pattern never
  dissolved; support lists in case-base order.
- Persistence: round-trip preserves patterns and `next_pattern=2`;
  dict-without-patterns loads `patterns=[]`, `next_pattern=1`; bare-list
  template file likewise; patterns-without-counter derives
  `next_pattern=5` from a stored `P4`; stale counter (`next_pattern=1`
  with `P4` present) also yields 5. `cases.py`/`dsl.py` unchanged; no new
  numeric constants (the absorb set, ordering key, and key fields
  introduce no literals; `MIN_SUPPORT_CASES` reused with its NOVEL
  comment).
- Sizes: `library.json` 503 B; pre-round reconstruction 367 B; pattern
  store **136 B**; `cases.json` 6996 B vs baseline 7022 B; net **+477 B**;
  pre-round net on the same cases **+341 B** — the report's +341→+477
  decomposition exact. Stats totals unchanged (rt=14, rw=1, ra=4, rw2=3);
  competence 8/8; references 6/7; T1/T2 support=3 each after maintain's
  pruning; history ≈4.9 KB total, ≈3.8 KB of it attempts.

## 8. Status-doc drop-in text (Q5)

For `docs/entry-001-status.md`, same style as the current document. The
時点 date advances to this milestone's date; the レビュー体制 bullet should
record this round's code+semantic review outcome once the cycle settles
(left to the committer, as last round). The 自作デモ framing is preserved —
this round makes no benchmark claim.

**(a) 実装済み — append one bullet after the 代謝 bullet:**

```markdown
- 修正パターンの昇格 v1（`library.py`・`solver.py`・`demo.py`；`cases.py`・`dsl.py` は不変）：事例履歴のうち勝った編集（history の edits）だけを編集種別ごとのキー（value→役割、swap→演算子名の対、insert/remove→演算子名）に抽象し、support（そのキーに抽象される勝ち編集を持つ distinct な task_id）が `MIN_SUPPORT_CASES` に達したものを `library.patterns` へ昇格する（`maybe_promote_patterns` を demo が `maybe_promote` の直後に呼ぶ。P番号はテンプレートと同じ単調カウンタで永続化・再利用なし。再マイニングは support の in-place 更新のみで溶解なし、support 空でも残る）。適用は value/string 系のみ（構造系 swap/insert/remove、および value/int・value/joiner は採掘のみ・適用なし）：revise のティア列挙の前に、ソースが string リテラルを持ち対象例の出力セパレータが空でないとき、リテラル×出力セパレータの値置換候補を support 降順→ID昇順で試行する（予算はティアと共有。勝てば編集記録に `pattern_id` が付き、試行記録には `pattern_tested` が載る）。候補生成は value ティアと同一 semantics（出力セパレータは value ドメインの部分集合）なので、パターン候補は常に value ティア候補の部分集合になる。dedupe は canonical JSON で「パターン候補1件の試行につき、同プログラムのティア出現1件を吸収する」scoped 仕様：`candidates_tested` はテスト事象数であって distinct プログラム数ではなく（基線から テンプレート↔再利用・value↔swap の重複計上を含む。code-upper の22件は distinct 13プログラム）、この読みの下でパターンパスは計上を増やさず、パターン候補が勝つ場合にのみ計上を減らし得る。呼び出し全体での厳密な global dedupe は基線自身の重複計上まで抑制して 22→21 と動いてしまうため、ブリーフの両要求を同時に満たす最小解としてこの scope を採用した（意味論レビューで検証・確定済み）。
```

**(b) 実測 — full section replacement:**

```markdown
## 実測（自作デモ上。反復用の手応れであって、主張の証拠ではない）

- 8タスク全解決。経路列・候補総数とも前回と完全同一（search/search/reuse/revise/template/revise/template/revise、総数 **73**、per-task 11/14/1/4/1/13/7/22）。修正パターンの導入は計上を一切動かさなかった。内訳：code-upper の revise は pattern_tested=1＋value_tested=1＋structural_tested=5（導入前は value 2＋構造 5。パターン候補が value ティア側の同プログラム出現を1件吸収し、swap ティア側の出現は基線どおり残るため、試行7件のマルチセットは同一）。他の3つの revise 試行（date-separator・name-swap-semicolon・date-separator-dot、いずれも P1 昇格前）は pattern_tested=0。パターンパスを無効化した再現実行は印刷出力が完全一致した。
- パターン昇格：P1（value/string）が date-separator-dot の直後に support=2（name-swap-semicolon、date-separator-dot）で昇格（T2 の昇格と同じタイミング）。swap キー（replace→upper）は support=1 で未昇格、insert/remove キーは存在しない。
- パターンのこのデモにおける正味の効果は **ゼロ**（追加候補ゼロ・勝ちゼロ）。唯一の応用は code-upper の負け候補1件で、value ティアが同じプログラムを試す予定だった1件を吸収しただけ。保守は前回と同じ結果（name-swap-new が redundant として削除、competence check **8/8**、テンプレート2件 T1/T2 とも support=3、**6/7 が参照**、統計総計 rt=14, rw=1, ra=4, rw2=3）で、パターンの導入はこれらにも影響なし（P1 の support に削除事例は含まれない）。
- サイズ収支は印刷値で **+477 B**（うちパターンストアの永続化が **+136 B**、残り +341 B は前回と同じ内訳）。support 件数だけの受入基準では、パターン格納は圧縮収支を確実に悪化させる側に働く。
- 履歴は attempts 全件保存のまま：削除後7事例で履歴合計 **約4.9 KB**、うち attempts 分が **約3.8 KB**（revise 記録に加わった pattern_tested 計数を含む）。失敗側の記録は次段階の負証拠マイニングの入力になる（どの候補が負けたかは決定的再実行で復元可能）。
```

**(c) スケッチとの差分 — full section replacement (bullets 1–3 carried
forward, bullet 4 replaced; the additions to 1 and 3 are marked by context,
not brackets, in the final text below):**

```markdown
## スケッチとの差分（重要・未解消）

- **失敗箇所の診断は依然なし（固定費は一部のみ緩和）。** ゲートの判断材料は「ソースが対象で実行できるか」だけで、失敗位置の同定ではない。記録される失敗観測も最初の失敗例1件（reuse の first_failure）と全例の passed／errors 計数、そして今回加わった pattern_tested 計数までで、例を跨いだ失敗の分布や出力間の距離は残らない。非実行ソースの構造列挙という固定費はゲートで消えたが、実行はするが修理不能なソースの列挙代（値置換全件＋探索）は全額のまま。
- **検索ランキングは意図的に不変・決定はデータ待ち。** adaptation-guided retrieval に沿ったランキング変更は先送りした（ブリーフの決定）。今回記録した behavior={passed, errors} はゲートの入力には十分だがランキングの証拠には不十分：passed は「既に完全一致する例の数」で近さを測らず（今回の記録では passed は全行 0）、behavior は試行された修正ソースにしか付かず、現ランキングが弾いた候補にはデータが無い。決定には (i) 全再利用候補への behavior 記録、(ii) 距離付きの失敗観測（全例の actual）、(iii) 保存済み事例ベースを使ったオフラインでのランキング比較再生、が先決。
- **保持まわりの残件はラベルの意味論とパターン support の保守。** admission ラベルは格納時点のイベント記録で、以後の昇格・削除では更新されない（novel と付いた事例が現在は参照、という読み違えを招く。kept 判定を受けた redundant 事例はラベルだけ見ると削除可能に見える）。トゥームストーン統計とテンプレート support の掃除は解消済みだが、maintain はパターンの support は刈り取らない（次のマイニングで自己修復するものの、maintain 直後の保存ファイルには死んだIDが残り得る）。
- **修正パターンの昇格は実装されたが、value/string のみ・かつスケッチの意味での「部品」ではない。** 適用があるのは value/string クラスのみ（構造系は採掘のみで適用なし。value/int・value/joiner も昇格されても適用されない）。パターン候補は常に value ティア候補の部分集合（同一の置換 semantics、出力セパレータは value ドメインの部分集合）なので、探索範囲を広げず順序だけを変える——実質は value ティアへの優先順位ヒント。キー（種別＋役割）は学習内容をほとんど捨てる（支援した2勝の from→to の値も、リテラルが入力側・出力側のどちらかも残らない）ため value/string は永遠に1枠で、適用条件と候補生成はコードに固定。証拠との対応も部分的で、2つの支援勝ちのうち出力側の置換（date-separator-dot）のみ再生し、入力側の置換（name-swap-semicolon、", "→"; "）は候補集合の外。support は「その編集クラスが勝った」ことを数えるのであって「このパターンが効いた」ことではなく、パターン自身の効果と無関係に増え得る（勝ちのみ採掘・溶解なしのラチェット。失敗適用は pattern_tested 計数として記録されるが未マイニング）。テンプレートがプログラム全体で部品として合成できないのと同様、パターンも合成には参照されず（revise のみ）、solve の順序も「型優先」のまま。部品に近づくには、学習内容を伴う表現（観測された置換値の保持、入力側／出力側の区別）、キーの細分化、合成時の参照、複数編集パターンのいずれかが必要。
```

**(d) 次の候補 — full section replacement:**

```markdown
## 次の候補

1. **修正パターンの表現と適用の拡張**（今回の直接の続き）：(a) 学習内容を伴うキーへ（観測された置換値、入力側／出力側の区別。現行キーは value/string 1枠で、2つの支援勝ちが実際に支えている2つの異なる抽象——入力側修理と出力側修理——を表現できない）、(b) 構造系パターンの適用条件（behavior／gated 記録が事前分布の材料）、(c) 負証拠のマイニング（pattern_tested 計数は記録済み、候補特定は決定的再実行で復元可能）、(d) value/int・value/joiner の適用可否の決定、(e) パターン support の保守（maintain での刈り取り、テンプレートと対称に。溶解規則の検討はその後）。
2. **検索ランキングの決定**（保留中の決定）：記録からの鍵選定。今回の記録だけでは決定不能（差分の通り）で、全候補 behavior・距離付き失敗観測の追加記録と、オフライン再生による比較が先決。
3. **実績ベンチへの接続**：SyGuS-Comp PBE-Strings 等。主張は既存ベンチの上でのみ行い、自作タスクは反復用に留める（AGENTS.md のベンチ規則、選定監査つき）。デモが示せるのは機構と到達可能性の存在証明までで、学習曲線・一般化・圧縮のいずれの主張にもベンチ接続が前提になる。今回の「パターンの正味効果ゼロ」という実測は、機構の存在証明としては通るが、効果の主張はベンチ上でやり直す必要があることを明示する。
4. **昇格基準への MDL 受入テストの検討**（引き続き先送り）：DreamCoder の基準（記述長が減る場合のみ採用）を、support 件数だけの現行基準と置き換えるか併用するか。テンプレートに加えパターンストア +136 B が動機に追加された。
```

---

Reviewer's process note: no code was modified and nothing was committed; the
only file written in this checkout is `REVIEW-repair-promotion-semantic.md`.
The scratch harness, counterfactual runs, and state snapshots live under
`/tmp/semrp-*` and are outside the repository.
