# Code review: metabolism round (R1–R6)

Reviewed files: `solver.py`, `cases.py`, `demo.py`; spot-checked `library.py` and `dsl.py` for unintended changes.
Method: read the spec (`BRIEF-metabolism.md`), the implementer's report (`REPORT-metabolism.md`), and the changed code; ran `demo.py` and small probes.
No code was modified; no commit was made.

## Executive summary

The implementation matches the spec in the parts that matter for the demo:
attempt records have the required shapes and sum correctly, the execution-eligibility
gate behaves as designed, admission labels and usage statistics are recorded,
`maintain()` removes the redundant `name-swap-new` case while preserving competence,
output is deterministic, and the explicit non-goals are respected.

There are two material issues to address:

1. **Stale template support lists after maintenance** — a removed case's `task_id`
   remains in `template["support"]`. This is inert for synthesis (slot lookup only
   reads from cases that still exist), but it makes the printed support count wrong.
2. **Deleted redundant-case stats** — the brief frames statistics as the record that
   survives deletion, yet a removed case's counters are discarded with it. The source-side
   counters on surviving cases remain, but no aggregate survives.

Both are flagged in `REPORT-metabolism.md` as deliberate interpretations; this review
concludes the first is a live observability bug and the second is a design gap worth
noting.

---

## 1. Clean items

### 1.1 Attempt records — shapes and counts

`solve()` builds `report["attempts"]` in stage order with the exact JSON-native
shapes required by R1 (`solver.py:44-50`, `solver.py:71-77`, `solver.py:251-260`,
`solver.py:113-118`). A probe of all eight demo tasks confirmed:

| stage    | keys present |
|----------|--------------|
| template | `stage`, `tested`, `outcome`, `template` |
| reuse    | `stage`, `source`, `outcome`, `first_failure` |
| revise   | `stage`, `source`, `tested`, `outcome`, `value_tested`, `structural_tested`, `gated`, `behavior` |
| search   | `stage`, `tested`, `outcome` |

For every revise attempt, `value_tested + structural_tested == tested`.
The implicit "tested" count of 1 per reuse attempt plus the explicit `tested`
fields for template/revise/search sum to the `tested` total returned by `solve()`.

The first failing example is recorded correctly:

- Program that runs but mismatches: `first_failure.actual` is the produced string
  (`solver.py:499`).
- Program that raises `DslError`: `first_failure.actual` is `None`
  (`solver.py:498`).

Unsolved tasks also carry attempts (`solver.py:122-130`); a probe with an
unsolvable example produced a full attempts list ending in a search miss.

### 1.2 Execution-eligibility gate

`_revise()` always runs the value tier (`solver.py:229-237`) and enters the
structural tiers only when the source program has zero `DslError`s on the target
examples and budget remains (`solver.py:239-248`). The gate comment cites
Smyth & Keane 1998 and the measured demo evidence (`solver.py:214-218`).

Probes confirmed:

- `date-separator` revise source `name-swap`: `gated=true`, `structural_tested=0`,
  `behavior.errors=2`.
- `code-upper` revise source `date-separator`: `gated=false`, `structural_tested=5`,
  `behavior.errors=0`.

Because gated sources never generate structural candidates, they consume no
`REVISE_CANDIDATE_LIMIT` budget. Early budget exhaustion inside a source still
breaks out cleanly (`solver.py:230-231`, `solver.py:241-242`). The demo candidate
count for `date-separator` dropped from 94 to 14 as expected.

### 1.3 `classify_admission`

The helper checks templates first (`solver.py:136-138`), then materializes each
case and checks exact match (`solver.py:139-143`). This gives the required
ordering: `absorbed` before `redundant` before `novel`. When `library is None`,
template-referenced cases are skipped (`solver.py:140-141`), matching the reuse
loop's behavior.

Demo admission labels matched the report:
`novel/novel/redundant/novel/absorbed/novel/absorbed/novel`.

### 1.4 Usage statistics

`demo.py:_update_usage_stats()` increments counters once per attempt, keyed by
source case (`demo.py:80-94`). A case that is both reuse-tested and used as a
revise source in the same solve gets both increments correctly.

`cases.py` round-trips `stats` and `admission` exactly like `history`
(`cases.py:53-56`, `cases.py:72-75`). Old files without these keys load and save
unchanged.

### 1.5 `maintain()` core logic

`maintain()` creates a temporary reduced `CaseBase` by identity exclusion
(`solver.py:170-175`), so tentative removal does not mutate the original base
and restoration is implicit. It re-solves every remaining case plus the removed
case (`solver.py:178-180`). Decision strings match R5's format
(`solver.py:159-160`, `solver.py:164-166`). A probe with a synthetic redundant
case whose removal broke another task returned `kept ... (removal breaks ...)`
and left the base unchanged.

### 1.6 Non-goals and dependencies

- `_rank_cases` and token-overlap logic are untouched (`solver.py:468-490`).
- `library.py` and `dsl.py` contain no metabolism-related changes.
- Only stdlib imports are used; no new dependencies.
- No new tuned numeric thresholds were introduced. The gate is boolean
  (`errors == 0`); the zero stats initializers carry a `NOVEL` comment
  (`demo.py:70-77`).

### 1.7 Determinism

Two consecutive `python3 demo.py` runs produced byte-identical stdout
(`sha256sum = 2bff8b0db344ae63f8d1583a1d0140f5f5ee1508593991ff67d7a9ea1bef2d5c`).
New code paths iterate lists (`case_base.all()`, `attempts`) in order; the dict
in `_update_usage_stats` is used only for lookup, not iteration.

---

## 2. Issues

### 2.1 Stale template support entries after removal — live observability bug

**Severity: moderate (accounting / reporting).**

`maintain()` removes `name-swap-new` from the case base but does not update the
`support` list of template `T1`. After the demo:

```text
T1.support = ['name-swap', 'name-swap-new', 'name-swap-semicolon', 'name-swap-pipe']
Cases in base = ['name-swap', 'date-separator', 'name-swap-semicolon',
                 'name-swap-pipe', 'date-separator-dot',
                 'date-separator-underscore', 'code-upper']
```

The library summary therefore prints `T1: support=4` even though only three of
those cases still exist.

**Why it is inert for synthesis:**

- `_support_slot_values()` filters support IDs against the current case base
  (`solver.py:455-465`). A removed case's ID contributes no slot values because
  the case is no longer in `case_base.all()`.
- `maybe_promote()` iterates over `case_base.all()`, not over `support`, when
  matching programs (`library.py:205-230`). A stale support ID never enters
  `covered_by_task`, and `_promote()` resets `template["support"]` from the
  matched cases (`library.py:305`).
- `_dissolve()` looks up each support ID in a `cases_by_task` dict built from
  `case_base.all()`; missing IDs are skipped (`library.py:321-329`).
- `materialize()` and `instantiate()` use only the skeleton and bindings, never
  `support`.

**Why it is still a bug:**

The printed support count is incorrect and will mislead any later session or
human reading the summary. If a future feature starts trusting `len(support)` as
a cardinality invariant (e.g. `MIN_SUPPORT_CASES` dissolution logic), the stale
entry could mask that a template no longer has enough actual support. The brief
explicitly asked reviewers to trace consumers and classify the stale entry;
this review classifies it as a live accounting bug, not merely provenance.

**Evidence:** `solver.py:147-167` (no support update), `library.py:305`
(consumer that would overwrite support on re-promotion), demo output line
`  T1: support=4` after `name-swap-new` was removed.

### 2.2 Removed redundant case loses its own stats — design gap

**Severity: low (spec interpretation, not a crash).**

The brief states that usage statistics are "the distilled record that survives
deletion" (R5). The implementation deletes a removed case's `stats` along with
the case. The source-side counters on surviving cases remain (e.g. `name-swap`
keeps its `reuse_wins`), but the removed case's `rt=3` counters are gone.

`REPORT-metabolism.md` records this as a deliberate divergence, noting that no
aggregate store for deleted-case counters was specified. This review agrees with
that reading of the literal spec, but flags it as a design gap: the brief's
framing implies survival, and a future maintenance round that aggregates
utility will need to decide whether to preserve these counters.

**Evidence:** `solver.py:163` (`case_base.remove(case)` removes the whole case),
demo output final stats line omits `name-swap-new`.

### 2.3 `classify_admission(library=None)` can under-report redundancy

**Severity: low / note.**

When `library is None`, `classify_admission()` skips any case that is stored as
a template reference (`solver.py:140-141`). For a base that contains only
referenced cases, an example solvable by those references will be labeled
`novel` instead of `redundant`. This matches the reuse loop's behavior (a
referenced case cannot be materialized without its library), so it is consistent
and not a bug in context. It is worth documenting because the helper's signature
accepts `library=None` and callers might expect semantic redundancy detection.

**Evidence:** `solver.py:133-144`.

### 2.4 Maintenance order can affect which redundant cases survive

**Severity: low / note.**

`maintain()` processes redundant cases in `case_base.all()` order and commits
removals immediately (`solver.py:153-167`). If two redundant cases depend on
each other, the first one checked may be removed because the second is still
present, and the second may then be kept because the first is gone. A single
atomic competence check over the set of all candidates would avoid this
order-dependence. The brief does not specify semantics for multiple redundant
cases, so this is an observation rather than a defect.

**Evidence:** `solver.py:153-167`.

---

## 3. Verification checklist from brief

| # | Item | Result |
|---|------|--------|
| 1 | Baseline reproduced; only `date-separator` changes 94→14; paths identical | Clean |
| 2 | Saved cases JSON contains attempts with misses; `date-separator` reuse miss has `actual=null`; revise attempt has `gated=true`, `structural_tested=0` | Clean |
| 3 | `code-upper` revise has `gated=false`, structural swap win | Clean |
| 4 | Stats consistent; `sum(reuse_wins)=1`, `sum(revise_wins)=3` pre-maintenance; every case has stats/admission | Clean |
| 5 | `maintain()` prints decisions; competence check `8/8` | Clean |
| 6 | Determinism: byte-identical output across runs | Clean |
| 7 | Library size delta reported honestly; history growth reported | Clean |
| 8 | Stdlib only; no new tuned constants | Clean |

The two issues above do not invalidate any of these checklist items, but they
are concrete places where the code and the brief's broader intent diverge.

---

## 4. Recommendations

1. **Update template support lists on removal.** In `maintain()`, after committing
   a removal, remove the case's `task_id` from every `template["support"]` list.
   If a list then drops below `MIN_SUPPORT_CASES`, call the existing dissolution
   path or at least warn. This fixes the stale-count bug and keeps the library
   and case base consistent.
2. **Document the stats-deletion choice explicitly** in `docs/entry-001-status.md`
   or a code comment if the brief's "survives deletion" wording is intentionally
   deferred; otherwise add an aggregate stats store for deleted cases.
3. **Consider batch maintenance** if multiple redundant cases are expected, so
   competence is evaluated over the final reduced base rather than commit-after-commit.
