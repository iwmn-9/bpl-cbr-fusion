# Semantic review: metabolism round (R1–R6)

Reviewer: GLM-5.2 (`semantic` profile), per `BRIEF-metabolism-review-semantic.md`.

Inputs judged: `BRIEF-metabolism.md` (spec + design decisions),
`REPORT-metabolism.md` (implementer's claims),
`docs/entry-001-representation-cost.md` (position memo this round implements),
`docs/entry-001-status.md`, `docs/entry-001-sketch.md`, and the changed code
(`solver.py`, `cases.py`, `demo.py`; `library.py`/`dsl.py` read for consumers).

Method: read everything first, then re-ran the demo (output identical to the
report's excerpts; `sha256` `2bff8b0d…bef2d5c` on repeated runs, matching the
report), reproduced the saved-cases JSON with a scratch harness that snapshots
the pre-maintenance file (patching `solver.maintain` and `tempfile` from
outside the repo), recomputed the size decomposition from those files, and
probed the unsolved-report path and `maintain()`'s `kept` branch. Scratch work
ran via stdin heredocs and wrote only under system temp (`/tmp/metab-*`).
No code was modified; nothing was committed (the checkout has no `.git`, as
the report states).

Scale used below: **Moderate** = a words-vs-mechanism divergence that silently
loses data or misleads if left in place; **Minor** = precision/latent issue;
**Note** = for the record. No critical defect: all eight brief invariants were
re-verified and hold (see §8), and the report is candid — its eight declared
divergences are real and honestly stated.

Map to the review brief's questions: Q1 (gate comment + citation) → §4;
Q2 (stats survive deletion; support as provenance) → §1 and §3;
Q3 (size headline) → §2; Q4 (behavior as mining data) → §5;
Q5 (admission labels) → §6; Q6 (status doc) → §9.

---

## 1. [Moderate] "Statistics survive deletion" — R5's stated rationale is not delivered, and the code comment was reworded to stop promising it

**The brief's words.** R5's comment spec: "an ever-growing case base degrades
retrieval, so retention must be earned; **statistics (R4) are the distilled
record that survives deletion**." The context paragraph frames the whole round
as "retention **with statistics distilled before any deletion**." The plain
reading: when a raw case is deleted, its distilled counters outlive it — that
is what makes deletion safe.

**The mechanism.** `maintain()` commits removal via `case_base.remove(case)`,
which drops the case dict whole: `name-swap-new`'s stats
(`rt=3, rw=0, ra=0, rw2=0` — retrieved-and-tested three times, never a reuse
win), its `admission`, and its history/attempts all vanish. Reproduced: the
final `cases.json` contains no `name-swap-new` and no key recording that a
removal ever happened. The decision string exists only in stdout.

**The comment.** `solver.py:148-151` reads: "Usage statistics (R4) are the
distilled usage record **the surviving base keeps** after a raw case is
deleted." The subject shifted from the deleted case's stats to the surviving
cases' stats — which were never at risk. As written the comment is accurate to
the mechanism but no longer states the brief's rationale; a future session
reading only the code sees a weaker design intent than the round was given.

**Judgment.** Real divergence from the brief's stated rationale, correctly
disclosed in the report (divergence 5) but not delivered. Severity: moderate
within this round's purpose. Nothing in the demo breaks, but every future
deletion silently destroys exactly the utility evidence the deferred
retention/ranking decisions need — a case retrieved 3× with 0 wins is the
cleanest "safe to forget" datum that exists, and deletion erases the evidence
that deletion was right. Note the asymmetry the brief intended: the raw
record (history/attempts, 272 B here) *should* die — that is the compression
point of deletion; only the distillate should survive. The implementation
kills both.

**Minimal faithful fix.** A tombstone aggregate on the case base:
`maintain()` appends `{task_id, admission, stats, decision}` (measured ≈199 B
for this deletion; the report's 113 B figure is the stats+admission portion,
which I confirmed) to a `removed` list on `CaseBase`, and `cases.py`
round-trips it. `cases.json` is currently a bare list, so the file becomes
`{"cases": […], "removed": […]}` with `load()` accepting the old bare-list
shape — exactly the dual-shape tolerance `Library.load` already implements
(`library.py:157-162`), so the pattern is native to this codebase. Deletion
still earns its ~350 B of raw-record savings; the distillate persists.

Related: the removal *decisions* are also unpersisted (print-only). The same
tombstone list closes that hole and gives the `kept` branch of §6 a durable
record.

## 2. [Moderate] The printed "+962 B" headline is no longer like-for-like; the baseline should carry `stats`/`admission` exactly as it already carries `history`

**What the number measures now.** The demo's baseline construction
(`demo.py:201-212`) copies each case's `history` verbatim — including
library-derived fields (`source_template`, `bindings`) — but omits `stats` and
`admission`, which every case now carries. Measured decomposition (all four
cells reproduced exactly from the snapshot files):

| state | cases+lib | plain baseline | meta baseline (like-for-like) |
|---|---:|---:|---:|
| pre-maintain | 7271 + 383 | 6620 → **+1034** | 7502 → **+152** |
| final | 6722 + 383 | 6143 → **+962** | 6912 → **+193** |

The printed +962 B = like-for-like deficit (+193) + 769 B of metadata the
baseline omits. It answers neither "what did this round cost" (the metadata
was deliberately added; it is not a representation deficit) nor "what does the
template mechanism cost" (+193 B).

**Is it misleading as a headline? Yes.** The status doc has tracked this
number as the compression signal for the sketch's hypothesis 3 (経験が貯まる
ほど系全体が軽くなる). A reader of the sequence "+152 B → +962 B" concludes the
round made representation ~6× worse. The truth: like-for-like moved +152 →
+193, a +41 B worsening with a specific, honest cause — the deleted redundant
case was a *reference*, so deletion removed 549 B from the real file but 590 B
from the metadata-inclusive baseline (its concrete-program cost had been
externalized to the shared template). Deleting redundant references makes the
raw base lighter while slightly worsening the compression ratio — the utility
problem's two faces, measured for the first time. That is the story the number
should tell, and +962 B tells none of it.

**Should the baseline include stats/admission? Yes.** The precedent is
in-file: `history` is copied verbatim with all its library-derived content.
The baseline is a storage-format thought experiment (concrete programs instead
of template references), not a re-derivation, so carrying the same recorded
per-case fields is the consistent convention. Two lines in the baseline loop
restore like-for-like, after which the printed line is again a single honest
number and the formula's label stays truthful. (The implementer reported both
numbers correctly in verification 7 — the defect is only what the demo prints
as its one headline and what a status doc would naturally quote.)

**Recommended reading for the status doc** (used in §9): state one number —
like-for-like **+193 B** — defined once, with the +41 B move and its cause as
a fact, and the attempts growth as a separate fact (it cancels in the
comparison). Treat the demo's printed +962 B as a known-biased formula until
the baseline is fixed; do not publish both with stacked caveats.

## 3. [Moderate] Template `support` after maintain() is a stale pointer, not provenance — the codebase's own consumers read it as live state

**What "support" is in this codebase.** After `maintain()` removes
`name-swap-new`, `T1.support` still lists it (reproduced:
`['name-swap', 'name-swap-new', 'name-swap-semicolon', 'name-swap-pipe']`),
and the demo prints `T1: support=4` over 3 real cases. The report (divergence 3)
calls the support list "provenance". The status doc reports support counts as
the templates' recurrence strength (「テンプレート2件（support 4 と 3）」);
`library.py:5` defines `MIN_SUPPORT_CASES` as "smallest count evidencing
recurrence"; the sketch describes the promotion relationship in the other
direction (cases become references to types) and does not name support at all.

**Consumers, traced:**

- `_support_slot_values` (`solver.py:455-465`) — dangling-tolerant (looks IDs
  up in the current base). This is the only consumer the implementer cited.
- `_dissolve` trigger (`library.py:316-317`): `len(old["support"]) <
  MIN_SUPPORT_CASES` — **not** dangling-tolerant. A dead ID inflates the
  count and can keep a template alive that no longer has the recurrence
  evidence the threshold exists to check.
- `_promote` (`library.py:300-305`) — actively *prunes* support IDs and
  rewrites the list from currently covered cases. `library.py` itself treats
  support as live, maintained state; `maintain()` leaving it stale breaks an
  invariant the rest of the codebase upholds.
- The printed count and the status doc's recurrence reporting — read a dead
  ID as recurrence evidence.

**Judgment.** The "provenance" defense holds for exactly one of the
consumers. Within this project support is the recurrence metric (the
promotion/dissolution currency), so the stale entry is a stale pointer with a
latent correctness effect (dissolution threshold) and a present accounting
effect (printed and doc-reported counts). The code review (§2.1 there)
reached the same conclusion; this review adds the dissolution consumer as a
present-tense reader, not just a future risk.

**Minimal fix.** `maintain()` prunes each removed `task_id` from every
`template["support"]` (here 4→3 ≥ `MIN_SUPPORT_CASES`, so no dissolution is
triggered and the dissolution-policy question can stay deferred, as the
report argues). The library file must then be re-saved after maintenance.

## 4. [Minor] The gate comment claims slightly more than the mechanism; the Smyth & Keane 1998 citation is a fair descendant but the comment does not mark the descent

The comment (`solver.py:214-218`): "Adaptation-guided retrieval (Smyth & Keane
1998): gate repair effort by whether the source adapts at all…"

**(a) "gate repair effort"** — the gate gates only the *structural* tiers;
the value tier always runs. The file says so itself ten lines later
(`solver.py:228`: "Value repairs are always tried, even for a non-executing
source"), so the two comments contradict each other under the gate comment's
own gloss.

**(b) "by whether the source adapts at all"** — the criterion is
executability (`behavior["errors"] == 0`), not adaptability, and in this
codebase "adapt" already means repair (`solver.py:88-89` cites Aamodt &
Plaza for exactly that sense). The demo's own records falsify the gloss:
`name-swap-semicolon`'s revise attempt is `gated=true` **and** `outcome=win`
(`value_tested=1`) — a source the comment would call unable to adapt at all,
adapting via the value tier and winning. The accurate phrase is "gate
structural repair effort by whether the source executes on every target
input."

**(c) "blocks … the 88-candidate structural+value enumeration"** — it blocks
the 80 structural candidates of that enumeration; the 8 value candidates
still run (the report's own arithmetic says 88 = 8 + 80 → 8 + 0). Compressed,
not false, but this comment is the one place the precision is the point.

**The citation.** Smyth & Keane 1998 (adaptation-guided retrieval) is about
*ranking retrieved cases* by adaptability — an adaptation-knowledge-guided
similarity measure, graded, applied at retrieval. Here the decision point is
different (which repair tiers to enumerate for an already-retrieved source)
and the signal is degenerate (one executability bit), while retrieval ranking
is deliberately unchanged. As a *descendant* it is fair and the lineage is
genuine — "adaptability, not surface similarity, should govern effort and
order" is exactly the principle the gate instantiates, and the brief's
decision 2 frames it the same way (ranking deferred, gate now). What the
comment lacks is the descent marker: as written it reads as if the paper
prescribes this mechanism. Since the brief mandated both the citation and the
framing, the residual imprecision is inherited, not invented — but the
semantic review's job is to say that a future session reading only this
comment would misreconstruct both the mechanism and the cited work.

**Suggested replacement** (for the next coder; not applied here):

```python
    # Adaptation-guided retrieval (Smyth & Keane 1998) ranks cases by
    # adaptability; this gate applies that principle one step later and one
    # bit coarser: structural tiers run only if the source executes (no
    # DslError) on every target input. Retrieval ranking is unchanged this
    # round. Measured on the demo: name-swap raises DslError on every
    # date-separator input, so the gate cuts that revise from 88 candidates
    # to its 8 value-tier ones; code-upper's cleanly executing source still
    # reaches its structural swap win.
```

The adjacent budget comment (`solver.py:16-25`) was checked and stays
accurate; `gated`-records-eligibility (report divergence 7) matches the
brief's definition ("skipped under the eligibility rule") in all four
branches, including budget-exhaustion and value-win skips.

## 5. [Minor] `behavior {"passed", "errors"}`: sufficient as the gate's input, insufficient as the ranking decision's evidence — and the corpus proves it

The design discussion (memo: 類似度を「直して使えたか」から学ぶ; brief decision 2)
wants *adaptability evidence* per source. What was recorded, measured over the
whole run: **4 behavior records, 2 distinct sources** (`name-swap`,
`date-separator`), and **`passed` is 0 in every record** — the mining key
never varies in this corpus. Meanwhile 17 reuse attempts carry
`first_failure` (raw `input/expected/actual`, with `actual` present for
executed-but-wrong sources — e.g. code-upper's three date-family sources
produced `ab/cd`, `ab.cd`, `ab_cd` against `AB-CD`) but no behavior counts.

**The conflation the brief asks about is real.** `passed` counts per-example
*exact* matches. For a revise source, `passed == len(examples)` is impossible
(a full-pass source wins at reuse), so it measures partial exact coverage —
which is neither "already solves it" nor "is close": a source outputting
`2026/11/1o` (one character off) scores the same `passed=0` as one outputting
`TARO TANAKA`. Exactness cannot rank near-miss against far-miss, i.e. it
cannot order by repair cost, which is what an adaptability key must do.
`errors` is the genuinely load-bearing half: it drives the gate and marks
structurally-blocked sources.

**What is missing for the ranking choice to be decidable from records:**

1. **Graded wrongness.** Per-example actual outputs, or an aggregate distance
   actual-vs-expected. The raw material already exists — `first_failure`
   stores `actual` — but only for the *first* failing example and only in
   reuse attempts, unlinked to the revise attempt's behavior.
2. **Coverage of all retrieved candidates.** Behavior is recorded only for
   attempted revise sources (≤ `REVISE_SOURCE_LIMIT=3`, and only on
   revise-path tasks). The cases the current token ranking *demoted* —
   exactly the comparison an alternative key must win — have no behavior
   data. Recording behavior in the reuse loop is nearly free: the program
   already executes there.
3. **The counterfactual.** The gate guarantees non-executing sources never
   get structural attempts, so no passive record can say whether structural
   repair would have rescued one. This closes only by offline replay of the
   saved corpus under alternative rankings — which the complete attempt
   records plus persisted cases now make possible. That replay capability,
   not direct mining of `{passed, errors}`, is this round's real contribution
   to the deferred decision.
4. **Aggregates over time** exist (R4 stats) but inherit the selection bias
   of (2); a gated source's `revise_wins` can only reflect value-tier wins.

**Verdict.** No defect against the brief — R2 asked to record, not to decide,
and "recorded but NOT used for ordering" is exactly what the code does. The
claim to police is any future statement that the ranking decision is now
"data-supported"; today it is data-*started* (4 rows, one non-constant
field). The status-doc text in §9 says so.

## 6. [Minor] Admission labels: mechanism faithful to the retention discussion; two traps for a future reader of the case file

The implemented semantics match the brief exactly: labels are computed before
storage against the pre-add base/library (absorbed = template enumeration
solves it, zero search; redundant = an existing case's materialized program
solves it; novel = neither), and `maintain()` consumes exactly the
"redundant" label. Order of checks gives absorbed-before-redundant
correctly; the `library is None` skip mirrors the reuse loop (the code
review's §2.3 note — consistent, worth one comment, not a defect).

**Trap 1 — events that read as states.** The label is an insertion-time
event and is never updated. After the run, `name-swap` is
`admission="novel"` yet stored as a `T1` reference; `absorbed` implies a
reference but the converse fails (4 of 6 references are labeled `novel`).
A reader of `cases.json` who interprets absorbed/novel as *current* status
is wrong in the common direction.

**Trap 2 — a kept "redundant" case recommends its own deletion.** Probed: a
case labeled redundant whose removal breaks the corpus is kept
(`kept weird (removal breaks weird)`) and still carries
`admission="redundant"` afterward, while the keep decision exists only in the
returned/printed string. The case file then asserts deletability of a
load-bearing case. It does not bite in this run (the one redundant case was
removed), but the branch exists and was exercised.

**Minimal fixes.** One comment at `classify_admission` stating the time
semantics ("insertion-time event; not updated by later promotion or
maintenance"), or relabel kept cases (e.g. `"redundant-kept"`); the tombstone
ledger of §1 would additionally persist the decisions.

## 7. [Minor] One mispaired figure in REPORT-metabolism.md's verification 7

"the all-concrete baseline drops 590 B (6620 → 6143)" — 6620 → 6143 is a drop
of **477 B**; **590 B** is the drop of the *metadata-inclusive* baseline
(7502 → 6912), which is the number the adjacent like-for-like argument
(+41 B worsening = 590 − 549) actually needs. Both conclusions in that
paragraph are correct (demo-formula improves 72 B = 549 − 477; like-for-like
worsens 41 B = 590 − 549); only the sentence pairs the wrong baseline with
590. Everything else in the report's decomposition table reproduces exactly.
Flagged for the record; fix the sentence when the report is next touched.

## 8. Independent verification record

Everything below was re-run for this review and matches `REPORT-metabolism.md`:

- Demo output byte-identical to the report's excerpts; two `sha256sum` runs
  both `2bff8b0db344ae63f8d1583a1d0140f5f5ee1508593991ff67d7a9ea1bef2d5c`.
- Paths identical to baseline
  (`search/search/reuse/revise/template/revise/template/revise`); only
  candidate change date-separator 94 → 14 (1 reuse + 8 value + 0 structural +
  5 search); total 153 → 73. The 80 blocked structural candidates recomputed
  structurally from the generators (swap 26 + insert 52 + remove 2 for the
  name-swap source on date-separator) — the brief's decision-1 evidence is
  arithmetically sound.
- Saved pre-maintenance JSON: date-separator's attempts verbatim as quoted
  (reuse miss with `first_failure.actual = null`; revise `gated=true`,
  `structural_tested=0`, `behavior {passed:0, errors:2}`); code-upper's
  revise `gated=false`, `value_tested=2`, `structural_tested=5`, win;
  date-separator-dot `gated=false`, `structural_tested=0` (value win);
  name-swap-semicolon `gated=true` with a value-tier win (§4's counterexample).
- Stats: pre-maintenance sums (rt, rw, ra, rw2) = (17, 1, 4, 3) with rw=1 =
  reuse solves and rw2=3 = revise solves; final sums (14, 1, 4, 3); every
  case carries `stats` and `admission`; per-case values match the report's
  table exactly.
- `maintain()`: decision string verbatim, competence check 8/8, kept-branch
  probed and correct, base unchanged on keep.
- Sizes: all four cells of the decomposition table (1034/152/962/193) and
  the demo's own baseline file (6143 B) reproduced exactly; history
  totals 4778/977/+3801 B (final) match; `stats`+`admission` of the removed
  case measured 113 B (report's figure confirmed).
- Unsolved tasks carry full attempts (probed: template/reuse/revise/search
  misses all present, revise `gated=true` on a non-executing source).
- Stdlib only; no new tuned constants; the gate is boolean; ranking and
  promotion logic untouched.

No further false claims were found in the report. Its divergences 1–8 are
candid and are confirmed by this review (1: no `.git`, nothing committed;
2: `passed+errors ≤ len(examples)`; 3: see §3; 4: temporary-base equivalence;
5: see §1; 6: see §2; 7: eligibility semantics; 8: labels printed for solved
tasks only).

## 9. Status-doc drop-in text (Q6)

For `docs/entry-001-status.md`, same style as the current document. The 時点
date in the title should advance to the milestone date. The レビュー体制
bullet should additionally record this round's code+semantic review outcome
once the cycle settles (left to the committer; not drafted here). The
benchmark framing (自作デモは反復用の手応えであって主張の証拠ではない) is
preserved — this round makes no benchmark claim, so the AGENTS.md
benchmark-selection audit has nothing to reject.

The solve order itself (テンプレート→再利用→修正→探索, in the 昇格 v1 bullet) is
unchanged by this round, so that sentence stands as written; what the round
changes is the revise mechanism (gate + attempt records) and adds a whole
metabolism subsystem the document does not yet describe.

**(a) 実装済み — replace the revise bullet, and append the metabolism bullet:**

```markdown
- 修正（revise）ステップ＋実行適格ゲート＋完全試行記録：再利用に失敗した候補（類似度ランキング上位3件）に単一編集を適用する。ティア順は 値置換→部品交換（swap）→部品挿入（insert）→部品削除（remove）で、いずれも1編集・決定的順序。値置換は常に試行し、構造ティアはソースプログラムが対象例の全入力で DslError なしに実行できるときのみ（実行適格ゲート。ブールで閾値なし。adaptation-guided retrieval（Smyth & Keane 1998）の「適応可能性が労力と順序を導く」原則を、ランキングではなく修正ティアの選択に1ビット信号で適用した変種。検索ランキング自体は意図的に不変）。ゲート済み候補は生成されず予算も食わない。solve 1回あたりの修正候補の試行は予算 `REVISE_CANDIDATE_LIMIT`=256 で頭打ち（ソース間で共有）。solve は各段階の試行を `report["attempts"]` に全件記録する（テンプレート1件、再利用は事例ごとに最初の失敗例 {input, expected, actual}（DslError 時は actual=null）、修正はソースごとに value_tested／structural_tested／gated／behavior={passed, errors}、探索1件。未解決でも残る）。demo は reason を除いて history に保存し、`cases.py` で往返する。採用された編集は {kind, …} として事例の history に保存される（再生可能性はレビューで双方向に検証済み）。
- 代謝（admission・統計・保持）：解けた事例は格納前に `classify_admission` で absorbed（既存テンプレートの列挙で解ける）／redundant（既存事例の具体化プログラムで解ける）／novel（いずれでもない）のラベルを付ける。ラベルは格納時点のイベント記録で、以後の昇格・削除では更新されない。各事例は使用統計 stats（reuse_tested／reuse_wins／revise_attempts／revise_wins）を持ち、demo が solve ごとに attempts から加算する。`maintain()` は redundant 事例の削除を候補に、削除後に残り全事例＋削除対象の例題が再解決できる場合のみ確定する（CBR の utility problem、Smyth & Cunningham 1996）。
```

**(b) 実測 — full section replacement:**

```markdown
## 実測（自作デモ上。反復用の手応れであって、主張の証拠ではない）

- 8タスク全解決、経路列は前回と同一（search/search/reuse/revise/template/revise/template/revise）。候補総数は **153 → 73**、唯一の変化は date-separator が **94件 → 14件**（再利用1＋修正8＝値置換8・構造0＋探索5）。全例で DslError を出す name-swap 由来の構造列挙80件がゲートでブロックされ、code-upper の構造勝ち（swap、gated=false、structural_tested=5）はゲートを通る側で生き残った。実行はするが直せる修正が存在しないソースの列挙代（値置換全件＋探索）は依然として固定費。
- 保守：name-swap-new が redundant として削除（removed … corpus still solvable）、全8タスク再解決で competence check **8/8**。テンプレート2件（T1 support=4 には削除済みの name-swap-new が残存し実効3、T2 support=3）。事例は削除後 **6/7 が参照**（code-upper のみ具体プログラム）。経路内訳は削除前 search=2 reuse=1 revise=3 template=2、削除後 search=2 revise=3 template=2（reuse で解いていた事例そのものが消えたため）。統計総計は rt=14, rw=1, ra=4, rw2=3（rw=再利用勝ち1、rw2=修正勝ち3 と一致）。
- サイズ収支は like-for-like で **+193 B** の赤字（事例＋ライブラリの合計 − 同じ事例を同じメタデータ付きの具体プログラムで持つ基線。前回 +152 B と同じ定義で stats／admission を基線側にも載せた値）。前回からの悪化 **+41 B** は、削除された name-swap-new が**参照**事例だったため：現側は 549 B 減、基線側は 590 B 減。冗長な参照事例の削除は生の事例ベースを軽くする一方で圧縮収支をわずかに悪化させる——utility problem の両顔が初めて実測に出た。なお demo の印刷行（+962 B）は基線が stats／admission を載せない旧式のままなので当面は参考値（基線への同フィールド追加が次回の修正候補）。
- 履歴は attempts 全件保存で膨らんだ：削除後7事例で履歴合計 **約4.8 KB**、うち attempts 分が **+3.8 KB**（attempts を除く履歴は約1.0 KB のまま）。「履歴は無料」ではないは以前より強く成立。失敗側の生記録は今回の目的そのもので、圧縮対象としては次段階の修正パターン昇格の入力になる。
```

**(c) スケッチとの差分 — full section replacement:**

```markdown
## スケッチとの差分（重要・未解消）

- **失敗箇所の診断は依然なし（固定費は一部のみ緩和）。** ゲートの判断材料は「ソースが対象で実行できるか」だけで、失敗位置の同定ではない。記録される失敗観測も最初の失敗例1件（reuse の first_failure）と全例の passed／errors 計数までで、例を跨いだ失敗の分布や出力間の距離は残らない。非実行ソースの構造列挙という固定費はゲートで消えた（94件→14件）が、実行はするが修理不能なソースの列挙代（値置換全件＋探索）は全額のまま。
- **試行の完全記録は成立したが、削除と一緒に消える。** attempts により全段階・全ソースの成否（miss 含む・未解決も）が記録に残り、「適応の成否」の否側が初めて蓄積を始めた（スケッチの事例スキーマの「実行結果」相当は最初の失敗例1件分の actual）。ただし maintain() で事例を削除するとその stats も attempts も消え、「統計は削除を生き残る蒸留記録」（R5 の設計意図）は未実装。削除判断の文字列も印刷のみで cases.json には残らない。最小修正は削除事例の {task_id, admission, stats} をトゥームストーン集計として事例ベース側に残すこと。
- **検索ランキングは意図的に不変・決定はデータ待ち。** adaptation-guided retrieval（Smyth & Keane 1998）に沿ったランキング変更は先送り（ブリーフの決定2）。今回記録した behavior={passed, errors} はゲートの入力には十分だが、ランキングの証拠には不十分：passed は「既に完全一致する例の数」で近さを測らず（実行はするが全例不一致のソース同士を区別できず、今回の記録では passed は全行 0）、behavior は試行された修正ソース（実質2事例）にしか付かず、現ランキングが弾いた候補にはデータが無い。ゲート済みソースの構造修理の成否は受動記録では原理的に観測不能。決定には (i) 全再利用候補への behavior 記録（再利用ループで既に実行しているのでほぼ無料）、(ii) 距離付きの失敗観測（全例の actual）、(iii) 保存済み事例ベースを使ったオフラインでのランキング比較再生、が欲しい。
- **保持まわりの未整備。** maintain() は support リストを更新しない（T1 support=4 に削除済みの name-swap-new が残存。support は library.py 内では生きた値——再昇格時に刈り取られ、溶解判定 len(support) < MIN_SUPPORT_CASES の分母——なので残存 ID は再発件数の過大申告になる）。admission ラベルは格納時点のイベントで以後更新されない（novel と付いた事例が現在は参照、という読み違えを招く。kept 判定を受けた redundant 事例はラベルだけ見ると削除可能に見える）。
- **昇格が扱うのは依然として「解の骨格」で、「修正パターン」の昇格は未実装。** 型はプログラム全体で部品として合成はできず、solve の順序もスケッチの「事例優先」と逆の「型優先」のまま。ただし履歴に失敗側が載ったことで、適用条件の材料は揃いつつある。
```

**(d) 次の候補 — full section replacement:**

```markdown
## 次の候補

1. **修正パターンの昇格**（入力は今回整った）：(a) 履歴を消費する昇格経路（現行 maybe_promote はプログラムしか消費しない）、(b) ライブラリにおける修正パターンの表現（現行テンプレートは全体プログラムで部品ではない）、(c) パターンの適用条件（value 系は自然なトリガーを持つが、構造系は behavior／gated 記録が事前分布の材料になった）。旧 (d) 失敗・逸脱の記録は今回で達成・削除。
2. **検索ランキングの決定**（保留中の決定）：記録からの鍵選定。今回の記録だけでは決定不能（上記差分の通り）で、全候補 behavior・距離付き失敗観測の追加記録と、オフライン再生による比較が先決。
3. **保持の最小修正**：削除時トゥームストーン統計（R5 の設計意図の回収）、support リストの掃除（maintain での刈り取り）、kept 判定の永続化（必要なら）。
4. **実績ベンチへの接続**：SyGuS-Comp PBE-Strings 等。主張は既存ベンチの上でのみ行い、自作タスクは反復用に留める（AGENTS.md のベンチ規則、選定監査つき）。デモが示せるのは機構と到達可能性の存在証明までで、学習曲線・一般化・圧縮のいずれの主張にもベンチ接続が前提になる。
5. **昇格基準への MDL 受入テストの検討**（引き続き先送り）：DreamCoder の基準（記述長が減る場合のみ採用）を、support 件数だけの現行基準と置き換えるか併用するか。like-for-like +193 B が動機。
```

---

Reviewer's process note: no code was modified and nothing was committed; the
only file written in this checkout is `REVIEW-metabolism-semantic.md`. The
scratch harness and its snapshots live under `/tmp/metab-*` and are outside
the repository.
