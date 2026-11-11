# REPORT: metabolism (R1–R6)

Scope: implement `BRIEF-metabolism.md` in `solver.py`, `cases.py`, and `demo.py`;
leave retrieval ranking and promotion/MDL untouched; report all eight verification
items. No commit was made (this checkout has no `.git` metadata; see
“Divergences and interpretations”).

Result in one line: all 8 demo tasks solve, the per-task paths are identical to
baseline, the only candidate-count change is date-separator 94 → 14, `maintain()`
removes `name-swap-new`, and the competence check prints `8/8`.

---

## Baseline (captured first, before any edit)

`python3 demo.py` was run in the unmodified working tree before implementation.
The checkout has no `.git` directory, so the literal commit `bf3bfc03` stated in
the brief could not be independently verified; the captured output matches the
brief's expected baseline exactly.

| # | task | baseline path | baseline candidates_tested |
|---|------|---------------|----------------------------|
| 1 | name-swap | search | 11 |
| 2 | date-separator | search | 94 |
| 3 | name-swap-new | reuse | 1 |
| 4 | name-swap-semicolon | revise | 4 |
| 5 | name-swap-pipe | template | 1 |
| 6 | date-separator-dot | revise | 13 |
| 7 | date-separator-underscore | template | 7 |
| 8 | code-upper | revise | 22 |
| | **total** | | **153** |

Baseline path sequence: `search/search/reuse/revise/template/revise/template/revise`.

Baseline library summary: 2 templates (`T1` support 4, `T2` support 3), 7/8 cases
stored as references, paths `search=2 reuse=1 revise=3 template=2`, net size delta
`+152 B`.

---

## Implementation per requirement

### R1 — complete attempt records

`solve()` now builds `report["attempts"]` in stage order:

- one `template` entry for the whole template stage, always present, including
  `tested=0` when the library is empty;
- one `reuse` entry per case actually tested in the reuse loop;
- one `revise` entry per revise source actually attempted;
- one `search` entry if the search stage is reached.

The entry shapes are exactly the brief's JSON-native shapes. A reuse miss carries
`first_failure = {"input", "expected", "actual"}` for the first failing example;
`actual` is the program's output string, or `None` when that input raised
`DslError`. `_first_failure()` is the single implementation of this check, and
`_matches()` now delegates to it. Unsolved tasks also return reports with
`attempts` (verified separately with an unsolvable example: a template miss and a
search miss are both present). `_report()` carries the list, and `demo.py` already
copies every report key except `reason` into `history`, so every attempt is
persisted without schema filtering.

### R2 — execution-eligibility gate in `_revise`

`_revise()` now computes a behavioral profile over all target examples:

```json
{"passed": <exact-match count>, "errors": <DslError count>}
```

The gate is boolean and threshold-free: `eligible = behavior["errors"] == 0`.
The value tier always runs. The structural tiers (`swap`, `insert`, `remove` — in
that order) are entered only when the source is eligible and budget remains. A
gated source never generates structural candidates, so they consume no budget;
the existing shared `REVISE_CANDIDATE_LIMIT` semantics are unchanged. Each revise
attempt records `value_tested`, `structural_tested`, `tested` (their sum),
`outcome`, `gated`, and `behavior`.

`gated` records eligibility, not “structural ran”: an eligible source whose value
tier wins has `gated=false` and `structural_tested=0` (date-separator-dot); a
non-eligible source whose value tier wins has `gated=true` and
`structural_tested=0` (name-swap-semicolon). This matches the brief's definition.

The budget comment was kept accurate and updated with the measured result. The
gate comment cites Smyth & Keane 1998 (adaptation-guided retrieval) and states
the demo evidence: the gate blocks the 88-candidate structural+value enumeration
from name-swap, which raises `DslError` on every target input, while code-upper's
cleanly executing source still reaches its structural swap win. `behavior` is
record-only mining data for the deferred ranking decision; only `errors == 0`
drives the gate, and no ordering was changed.

### R3 — admission labels

Added `classify_admission(examples, case_base, library)` to `solver.py`. It uses
the existing template machinery (`_solve_with_templates`, zero search) first, then
checks whether any existing case's materialized program matches the examples. It
returns `"absorbed"`, `"redundant"`, or `"novel"`.

`demo.py` calls it before adding each solved case, against the pre-add base and
library, stores `case["admission"]`, and prints one `admission: <label>` line per
task. Labels in this run:

| task | admission |
|------|-----------|
| name-swap | novel |
| date-separator | novel |
| name-swap-new | redundant |
| name-swap-semicolon | novel |
| name-swap-pipe | absorbed |
| date-separator-dot | novel |
| date-separator-underscore | absorbed |
| code-upper | novel |

Counts: absorbed 2, redundant 1, novel 5.

### R4 — usage statistics

Each newly added case starts with:

```json
{"reuse_tested": 0, "reuse_wins": 0, "revise_attempts": 0, "revise_wins": 0}
```

`demo.py` updates stats after each solve from `report["attempts"]`: each reuse
attempt increments the source case's `reuse_tested` (and `reuse_wins` on a win);
each revise attempt increments the source's `revise_attempts` (and `revise_wins`
on a win). Template/search attempts have no source and do not touch stats. The
zeros are structural initializers and are marked `NOVEL` in `_new_stats()`; there
are no tuned values.

`cases.py` round-trips `"stats"` and `"admission"` exactly like `"history"`, and
old files without these keys load with the keys absent (verified). Stats are
initialized only when first set on a loaded old case, as specified. A small
`CaseBase.remove(case)` method was added for R5's commit step.

Pre-maintenance stats (8 cases; final base omits the removed name-swap-new):

| case | rt | rw | ra | rw2 |
|------|----|----|----|-----|
| name-swap | 5 | 1 | 2 | 1 |
| date-separator | 3 | 0 | 2 | 2 |
| name-swap-new | 3 | 0 | 0 | 0 |
| name-swap-semicolon | 2 | 0 | 0 | 0 |
| name-swap-pipe | 2 | 0 | 0 | 0 |
| date-separator-dot | 1 | 0 | 0 | 0 |
| date-separator-underscore | 1 | 0 | 0 | 0 |
| code-upper | 0 | 0 | 0 | 0 |
| **sum** | **17** | **1** | **4** | **3** |

Final (7 cases) sums: rt=14, rw=1, ra=4, rw2=3. The removed case's own rt=3 is
deleted with it; the surviving source-side stats still sum rw=1 and rw2=3 (see
verification 4 and the note in “Divergences”). Stats are recorded only; they do
not affect retrieval ranking or maintenance ordering in this round.

### R5 — competence-preserving maintenance

Added `maintain(case_base, library)` to `solver.py`. For each case whose stored
admission is `"redundant"`:

1. build a temporary reduced `CaseBase` excluding that case;
2. re-solve every remaining case's examples plus the removed case's examples
   against the reduced base and the library;
3. if any task fails, keep the case and record `kept <task_id> (removal breaks
   <broken_task_id>)`; otherwise commit the removal and record
   `removed <task_id> (redundant, corpus still solvable)`.

The temporary-base approach is equivalent to remove-and-restore and preserves
case order on kept candidates. The comment cites the CBR utility problem (Smyth &
Cunningham 1996) and states why retention must be earned.

In the demo, the only candidate is `name-swap-new`; the decision was:

```text
removed name-swap-new (redundant, corpus still solvable)
```

The demo prints the decision verbatim (`removed name-swap-new (redundant, corpus
still solvable)`), then re-solves all 8 demo tasks against the maintained base and
prints `competence check: 8/8`.

`library.py` promotion logic was not touched. `maintain()` does not edit template
support lists; see “Divergences” for the interpretation.

### R6 — demo output additions

Kept in the existing style:

- one `admission: <label>` line per task;
- the `maintain()` decision strings printed after the task loop;
- `competence check: X/8`;
- one `stats: ` line in the library summary, using the brief's abbreviations
  `rt` (`reuse_tested`), `rw` (`reuse_wins`), `ra` (`revise_attempts`), and
  `rw2` (`revise_wins`).

All existing per-task lines, repair lines, promotion lines, and the template line
are unchanged. A blank line was added before `library summary:` to separate the
new post-loop section, matching the existing section spacing.

Final output excerpt:

```text
removed name-swap-new (redundant, corpus still solvable)
competence check: 8/8

library summary:
templates: 2
  T1: support=4
  T2: support=3
references: 6/7 cases stored as references
paths: search=2 revise=3 template=2
stats: name-swap(rt=5, rw=1, ra=2, rw2=1) date-separator(rt=3, rw=0, ra=2, rw2=2) name-swap-semicolon(rt=2, rw=0, ra=0, rw2=0) name-swap-pipe(rt=2, rw=0, ra=0, rw2=0) date-separator-dot(rt=1, rw=0, ra=0, rw2=0) date-separator-underscore(rt=1, rw=0, ra=0, rw2=0) code-upper(rt=0, rw=0, ra=0, rw2=0)
net size delta: +962 B ((cases.json + library.json) - all-concrete cases-only baseline)
```

---

## Before/after table

| task | baseline path | baseline candidates | after path | after candidates | delta |
|------|---------------|---------------------|------------|------------------|-------|
| name-swap | search | 11 | search | 11 | 0 |
| date-separator | search | 94 | search | **14** | **−80** |
| name-swap-new | reuse | 1 | reuse | 1 | 0 |
| name-swap-semicolon | revise | 4 | revise | 4 | 0 |
| name-swap-pipe | template | 1 | template | 1 | 0 |
| date-separator-dot | revise | 13 | revise | 13 | 0 |
| date-separator-underscore | template | 7 | template | 7 | 0 |
| code-upper | revise | 22 | revise | 22 | 0 |
| **total** | | **153** | | **73** | **−80** |

Paths after: `search/search/reuse/revise/template/revise/template/revise` — identical
to baseline.

Date-separator arithmetic:

- baseline: template 0 + reuse 1 + revise 88 (8 value + 80 structural) + search 5 = 94;
- after: template 0 + reuse 1 + revise 8 (8 value + 0 structural) + search 5 = 14.

The 80 blocked structural candidates came from the name-swap source, which raises
`DslError` on both target inputs. No other task's path or candidate count changed.
Programs, repair records, and promotion events are identical to baseline.

Explained summary differences (not per-task path/candidate changes):

- `references` 7/8 → 6/7 because `name-swap-new` was removed;
- summary `paths` loses `reuse=1` for the same reason (it remains in the per-task
  table, captured before maintenance);
- net size delta +152 B → +962 B, explained in verification 7; the existing
  baseline formula was not changed;
- new admission, maintain, competence, and stats lines as required by R6.

---

## Verification results

### 1. Baseline first, then the expected-only candidate change

Baseline was captured before editing (table above). After the change: 8/8 solved,
paths identical, and the only per-task candidate change is date-separator 94 → 14,
with the exact breakdown `1 reuse + 8 value + 0 structural + 5 search`. This
matches the brief. The baseline's expected values
`11/94/1/4/1/13/7/22` and path sequence were reproduced exactly.

### 2. Saved cases JSON: attempts, including misses

The demo's temp files are deleted, so this was reproduced with a temporary script
that runs the same loop and saves `cases.json`. All 8 pre-maintenance cases have
`history.attempts`; the final 7-case file also has attempts on every case. All
entries are JSON-native.

Date-separator's saved history contains exactly the required observations:

```json
[
  {"stage": "template", "tested": 0, "outcome": "miss", "template": null},
  {"stage": "reuse", "source": "name-swap", "outcome": "miss",
   "first_failure": {"input": "2026-11-10", "expected": "2026/11/10", "actual": null}},
  {"stage": "revise", "source": "name-swap", "tested": 8, "outcome": "miss",
   "value_tested": 8, "structural_tested": 0, "gated": true,
   "behavior": {"passed": 0, "errors": 2}},
  {"stage": "search", "tested": 5, "outcome": "win"}
]
```

The reuse miss has `first_failure.actual = null` (DslError), and the revise
attempt has `gated = true` and `structural_tested = 0`. Its counts sum:
8 value + 0 structural = 8 tested.

### 3. code-upper: gate open, structural swap win

code-upper's saved revise attempt is:

```json
{"stage": "revise", "source": "date-separator", "tested": 7, "outcome": "win",
 "value_tested": 2, "structural_tested": 5, "gated": false,
 "behavior": {"passed": 0, "errors": 0}}
```

`gated = false`, `structural_tested = 5 > 0`, the outcome is a win, and the
recorded edit is the swap `["replace", "-", "/"]` → `["upper"]`. The source
executes cleanly on both target inputs but passes 0 examples, matching the
brief's decision-1 evidence. Total code-upper candidates are unchanged at 22
(template 8 + reuse 7 + revise 7).

### 4. Stats consistency

Pre-maintenance (the 8-case corpus; table in R4):

- per-task paths: `search=2 reuse=1 revise=3 template=2`;
- `sum(reuse_wins) = 1`, equal to the 1 reuse-path solve;
- `sum(revise_wins) = 3`, equal to the 3 revise-path solves;
- every case has `stats` and `admission`.

Final maintained base (7 cases):

- every remaining case still has `stats` and `admission`;
- `sum(reuse_wins) = 1` and `sum(revise_wins) = 3` are unchanged;
- summary paths are `search=2 revise=3 template=2` because the reuse-solved case
  (`name-swap-new`) was removed; the surviving reuse win is recorded on its
  source (`name-swap`), which is the source-side statistic R4 asks for;
- the removed case's own counters were `rt=3` and zero elsewhere; they are deleted
  with the case (flagged under “Divergences”).

A load/save round-trip of a case with `stats` and `admission` was value-identical
in the parsed JSON, and an old case file without either key loaded and saved
unchanged.

### 5. maintain() decisions and competence check

Removal candidates: only `name-swap-new` (the only `"redundant"` admission).

Decision string, verbatim:

```text
removed name-swap-new (redundant, corpus still solvable)
```

Printed line:

```text
removed name-swap-new (redundant, corpus still solvable)
competence check: 8/8
```

All 8 original tasks solve against the maintained base. The `kept` branch was also
exercised with a synthetic mislabeled-redundant case whose examples are not
solvable without it; it returned
`kept broken (removal breaks broken)` and left the case base unchanged.

### 6. Determinism

Repeated normal runs, plus runs with `PYTHONHASHSEED=1` and `PYTHONHASHSEED=2`,
all produced byte-identical stdout:

```text
2bff8b0db344ae63f8d1583a1d0140f5f5ee1508593991ff67d7a9ea1bef2d5c
```

`cmp` reported no differences. The net size delta is stable across runs because
the JSON serialization and case order are deterministic.

### 7. Library size accounting

The demo's printed number is **+962 B** after maintenance. This uses the existing
formula (current cases + library) − (all-concrete cases-only baseline), and that
formula was left unchanged. Decomposition, measured with the same run:

| view | cases.json | library.json | baseline | net delta |
|------|-----------:|-------------:|---------:|----------:|
| pre-maintain, demo formula | 7271 B | 383 B | 6620 B | **+1034 B** |
| pre-maintain, baseline also includes `stats`/`admission` | 7271 B | 383 B | 7502 B | **+152 B** |
| final (after removal), demo formula | 6722 B | 383 B | 6143 B | **+962 B** |
| final, baseline also includes `stats`/`admission` | 6722 B | 383 B | 6912 B | **+193 B** |

The pre-maintenance metadata-inclusive delta is exactly the HEAD baseline's
`+152 B`. The +882 B difference in the demo formula (1034 − 152) is exactly the
882 B of `stats` + `admission` JSON that the plain baseline does not carry. The
final difference (962 − 193 = 769 B) is the remaining metadata after removing
name-swap-new.

History growth is real but cancels in the demo formula because the baseline also
carries `history`. Serialized history-value bytes (`json.dumps`, UTF-8,
`ensure_ascii=False`, excluding the `"history":` key and outer separators):

| case | without attempts | with attempts | growth |
|------|-----------------:|--------------:|-------:|
| name-swap | 95 B | 235 B | +140 B |
| date-separator | 95 B | 554 B | +459 B |
| name-swap-new | 101 B | 272 B | +171 B |
| name-swap-semicolon | 196 B | 922 B | +726 B |
| name-swap-pipe | 106 B | 192 B | +86 B |
| date-separator-dot | 188 B | 1216 B | +1028 B |
| date-separator-underscore | 104 B | 190 B | +86 B |
| code-upper | 193 B | 1469 B | +1276 B |
| **total (8 cases)** | **1078 B** | **5050 B** | **+3972 B** |

After removing name-swap-new, the final 7-case base retains 4778 B of history
with attempts, 977 B without, for +3801 B of growth. The largest growths
(code-upper +1276 B, date-separator-dot +1028 B) come from their many reuse-miss
records and full revise behavior; this is the raw observation the brief asked to
retain, not hidden overhead.

Removal accounting: cases.json drops 549 B (7271 → 6722) and the all-concrete
baseline drops 477 B (6620 → 6143), so the demo-formula delta improves by 72 B
(1034 → 962); the metadata-inclusive baseline drops 590 B (7502 → 6912), so the
like-for-like compression delta worsens by 41 B (152 → 193). The removed case's
own stats/admission JSON is 113 B and its history object is 272 B; those are
deleted with it. The library file is unchanged at
383 B (2 templates). `T1` still reports support=4 and `T2` support=3; the support
list is provenance, and an absent support case contributes no slot values because
`_support_slot_values()` consults the current case base.

### 8. Stdlib only, no new tuned constants

Only standard-library imports are used (`json`, `os`, `tempfile`, plus the
existing `itertools`, `re`, and local modules). No new dependency was added. No
new module-level numeric constant or threshold was introduced: the gate is the
boolean `errors == 0`, and the only new literals are structural zeros/ones in the
stats initializers and counters. The zero initializers carry a `NOVEL` comment in
`_new_stats()`. `REVISE_CANDIDATE_LIMIT = 256` is unchanged, as are all other
existing limits.

Retrieval ranking (`_rank_cases`, token scoring) is untouched. Promotion and MDL
logic in `library.py` are untouched; promotion events are identical to baseline.
The other explicit non-goals also hold: `_revise` still returns a single edit
record, `dsl.py` and its op set are untouched, and no benchmark code was added.

---

## Divergences and interpretations

1. **No git metadata.** The directory has no `.git`, so the brief's literal
   `HEAD`/commit `bf3bfc03` could not be checked. The baseline was run first on
   the unmodified working tree and matches the expected table exactly.
2. **`behavior.passed` means exact output match.** `passed` counts examples whose
   output equals the expected output; `errors` counts `DslError`. An executed-but-
   wrong example is neither, so `passed + errors` may be less than the example
   count. This is the only reading consistent with the brief's decision-1 evidence
   (“no value candidate passes more examples than the source” while the code-upper
   source executes cleanly but passes zero examples).
3. **`maintain()` reduces the case base, not library support lists.** No
   `library.py` promotion logic was changed. Template support IDs are treated as
   provenance; a removed case's ID may remain in `T1.support`, and it contributes
   no slot values because support lookup only sees current cases. If the brief
   intended support-list rewriting (and possible dissolution below
   `MIN_SUPPORT_CASES`), that is not specified and was deliberately left out of
   this round.
4. **Remove-and-restore is implemented as a temporary reduced base.** This avoids
   reordering the base on a kept candidate and is behaviorally equivalent to
   tentative removal plus restoration. A small `CaseBase.remove()` was added for
   the commit step.
5. **The removed case's own stats are deleted with it.** The brief's comment says
   statistics are the distilled record that survives deletion; here the surviving
   cases keep their source-side counters, but no aggregate store for a deleted
   case's counters was specified, so `name-swap-new`'s `rt=3` does not survive.
   This is recorded rather than hidden.
6. **The printed net size delta uses the existing baseline formula**, which does
   not include `stats`/`admission` on the baseline side. That is why the printed
   number is +962 B rather than the like-for-like +193 B; both are reported in
   verification 7, and the formula was not changed.
7. **`gated` tracks eligibility, not whether structural candidates actually ran.**
   An eligible source whose value tier wins can show `gated=false` with
   `structural_tested=0` (date-separator-dot), and a gated source can still win in
   the value tier (name-swap-semicolon). This follows the brief's definition.
8. **Admission is printed only for solved tasks.** All 8 demo tasks are solved, so
   the demo prints 8 admission lines. Unsolved tasks have no case to label.

Reproduction:

```bash
python3 demo.py
python3 demo.py | sha256sum   # 2bff8b0db344ae63f8d1583a1d0140f5f5ee1508593991ff67d7a9ea1bef2d5c
```

The saved-JSON, stats, maintain, and size checks above were run with temporary
scripts outside the repository; no test/benchmark code was added. No commit or
push was performed.

---

## Fix round

Scope: implement `BRIEF-metabolism-fixes.md` F1–F5 exactly; everything not
mentioned was left unchanged. No commit was made. Where this section conflicts
with the previous round's description, this section wins: it supersedes
divergence 3 (support left stale), divergence 5 (removed stats deleted), and
the last sentence of verification 7 (T1 support=4).

### F1 — tombstone statistics

`CaseBase` now owns `removed` (default `[]`). When `maintain()` commits a
removal, it appends `{"task_id", "admission", "stats", "decision": "removed"}`
to that list before deleting the case body, so the distillate survives. The
maintain comment again says statistics are distilled into tombstones before
deletion. `cases.py` persists the new shape `{"removed": [...], "cases": [...]}`
and reads a stored top-level list as the old format (`removed = []`), the same
dual-shape tolerance `Library.load` has. `demo.py` prints `removed records: <n>`
after the maintain decisions.

The demo ledger has one record, saved verbatim in the final `cases.json`:

```json
{"task_id": "name-swap-new", "admission": "redundant",
 "stats": {"reuse_tested": 3, "reuse_wins": 0,
           "revise_attempts": 0, "revise_wins": 0},
 "decision": "removed"}
```

The removed case's own `rt=3` now survives. Its history is still deleted; that
is the raw record the tombstone is meant to replace.

### F2 — like-for-like size baseline

The all-concrete baseline now copies `stats` and `admission` exactly as it
already copied `history`, with a comment stating that the baseline carries
history/stats/admission verbatim so the delta measures representation only.
The F2-only final figure is the predicted **+193 B**; the actual printed figure
is **+341 B** because F1 and F3 landed in the same round:

| view | cases.json | library.json | baseline | net delta |
|------|-----------:|-------------:|---------:|----------:|
| pre-maintain, metadata-inclusive | 7297 B | 383 B | 7528 B | **+152 B** |
| final, metadata-inclusive + tombstone | 6912 B | 367 B | 6938 B | **+341 B** |

The new dictionary wrapper adds 26 B to both the cases file and the baseline,
so it cancels. F1's tombstone contributes 164 B to `cases.json` (6912 B with it
vs 6748 B without); F3 prunes 16 B from `library.json` (383 → 367). Starting
from the F2-only +193 B, `193 + 164 − 16 = 341`. Excluding the tombstone, the
representation-only delta is **+177 B**, 16 B better than +193 B because the
stale support entry is gone. The pre-maintenance metadata-inclusive delta stays
+152 B, so the +41 B like-for-like worsening from the review's decomposition
still reproduces; the tombstone is new retained metadata, not representation
overhead.

### F3 — stale support pruned

On a committed removal, `maintain()` removes the case's `task_id` from every
template's `support` list. It does not dissolve templates and does not touch
support for kept cases. `demo.py` re-saves `library.json` after maintenance so
the file matches memory. The printed `T1: support=3` now lists the three live
cases (`name-swap`, `name-swap-semicolon`, `name-swap-pipe`); `T2` stays at 3.
The synthetic kept-branch check still returns `kept weird (removal breaks
weird)`, leaves the case in place, and appends no tombstone.

### F4 — gate comment precision

Replaced the overclaim with the accurate statement: the gate restricts
STRUCTURAL repair effort by executability (the source must run without
`DslError` on every target input); the value tier is never gated, so a
non-executing source can still win there (`name-swap-semicolon`: `gated=true`,
value-tier win); it blocks 80 of that revise's 88 candidates. The Smyth & Keane
1998 citation is kept with its descent marked: their retrieval ranks by
adaptability, while this gate applies the same principle at a coarser, one-bit
decision point, to repair effort instead of ranking. Retrieval ranking is
unchanged. This is a comment-only change; behavior, paths, and counts are
identical.

### F5 — report erratum

Corrected verification 7 in place: `6620 → 6143` is a drop of **477 B**, not
590 B. The 590 B drop is the metadata-inclusive baseline (`7502 → 6912`), which
is the figure the like-for-like +41 B argument uses. The erratum changes no
measured result.

### Re-verification after fixes

- Demo: all **8/8** tasks solve; paths are
  `search/search/reuse/revise/template/revise/template/revise`, unchanged.
- Per-task candidates are `11/14/1/4/1/13/7/22`, total **73**, unchanged.
- Competence check prints **8/8**.
- Maintain decision is unchanged: `removed name-swap-new (redundant, corpus
  still solvable)`.
- Printed net size delta is **+341 B** (F2-only +193 B; full decomposition
  above). `T1` prints **support=3** (was 4).
- Saved final `cases.json` has keys `["removed", "cases"]`, 7 cases, and the
  tombstone above with the removed case's stats intact. A `CaseBase` load/save
  round-trip preserves both lists.
- An old-format bare-list file loads with `removed = []`; re-saving it as the
  new shape preserves all 7 case objects value-identically.
- Final stats sums are unchanged at `rt=14, rw=1, ra=4, rw2=3`; the tombstone
  carries the removed case's `rt=3`.
- Two consecutive `python3 demo.py` runs are byte-identical; the new stdout
  hash is
  `cf3ed9e05b8660327c8f3b11acc876b6d41cf068c2bddaff45e7353ca55a212e`.

### Acknowledged non-fixes

Recorded as known behavior, with no code change:

- Code finding 3: `classify_admission(library=None)` under-reports redundancy
  for reference-only bases.
- Code finding 4: `maintain()` decisions are order-dependent across multiple
  redundant cases.
- Semantic finding 5: `behavior {passed, errors}` is insufficient for the
  deferred ranking decision; its four missing pieces are design input for that
  future round.
- Semantic finding 6: admission labels are insertion-time events.
