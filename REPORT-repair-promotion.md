# REPORT: repair-pattern promotion v1 (entry 001)

Scope: implement `BRIEF-repair-promotion.md` (R1–R5) in `library.py`,
`solver.py`, and `demo.py`; `cases.py` is untouched. No commit was made (this
checkout has no `.git` metadata).

Result in one line: demo 8/8, paths and per-task candidate counts identical
(`11/14/1/4/1/13/7/22`, total **73**), `P1` promoted exactly after
`date-separator-dot` with support `{name-swap-semicolon, date-separator-dot}`,
the swap key stays at support 1 and is not promoted, and `code-upper`'s revise
attempt shows `pattern_tested=1` with task total still 22.

---

## Baseline (captured before editing)

`python3 demo.py` was run in the unmodified tree first. Paths were
`search/search/reuse/revise/template/revise/template/revise`; the summary was
2 templates (`T1` support 3, `T2` support 3), 6/7 referenced cases, no patterns,
and net size delta `+341 B`.

| # | task | path | candidates_tested |
|---|------|------|-------------------|
| 1 | name-swap | search | 11 |
| 2 | date-separator | search | 14 |
| 3 | name-swap-new | reuse | 1 |
| 4 | name-swap-semicolon | revise | 4 |
| 5 | name-swap-pipe | template | 1 |
| 6 | date-separator-dot | revise | 13 |
| 7 | date-separator-underscore | template | 7 |
| 8 | code-upper | revise | 22 |
| | **total** | | **73** |

---

## Implementation

### R1 — pattern mining in `library.py`

`PATTERN_KEY_FIELDS` fixes the stored fields per kind:

| edit kind | pattern key | stored fields after `pattern_id`/`kind` |
|-----------|-------------|----------------------------------------|
| value | `("value", role)` | `role` |
| swap | `("swap", from_op[0], to_op[0])` | `from_op`, `to_op` (names only) |
| insert | `("insert", op[0])` | `op` (name only) |
| remove | `("remove", op[0])` | `op` (name only) |

`maybe_promote_patterns(case_base, library)` scans `case.history["edits"]`
(winning edits only; failed attempts are not in `edits`). It builds
`key -> [task_id]` in case-base order, de-duplicating repeated task IDs, then
promotes keys whose support reaches `MIN_SUPPORT_CASES` (the existing constant,
same recurrence threshold as templates). A new pattern is:

```json
{"pattern_id": "P1", "kind": "value", "role": "string",
 "support": ["name-swap-semicolon", "date-separator-dot"]}
```

IDs are `P<n>` with `library.next_pattern_number`; the counter is persisted as
`next_pattern` beside `next_template`. On load, a missing/stale counter is
replaced by `max(saved, derived from existing P ids)`, so IDs cannot be reused.

Mining is idempotent in state and events:

- an existing key updates `support` in place and never creates a second pattern;
- if support is unchanged, no event is emitted (a second call returns `[]`);
- if support changes, the event is `updated P<n> support=...: ...`;
- a pattern whose key disappears from all histories gets support `[]` but is
  never removed (patterns are not dissolved this round).

The event format mirrors template promotions: `promoted P1 support=2: ...` /
`updated P1 support=3: ...`.

### R2 — persistence

`Library` now has `patterns = []` and `next_pattern_number = 1` by default.
`load()` accepts both shapes already supported for templates: a dict with
`templates` (and now optional `patterns`/`next_pattern`) or the old bare
template list. A stored file without `"patterns"` loads with `patterns = []`;
a file with patterns but no counter derives the next number from them.
`save()` writes `next_template`, `next_pattern`, `templates`, and `patterns`
into `library.json`. `cases.py` is unchanged.

### R3 — application in `solver.py`

`_revise()` now receives the library and, before value/structural tier
enumeration, iterates applicable promoted patterns in the required order:
support size descending, then numeric `pattern_id` ascending. Only
`("value", role="string")` patterns are applied in this round. A pattern
applies when the materialized source program has at least one string-role
literal and the target examples' output separators are non-empty. Its
candidates are, in value-tier literal order, each distinct string literal `L`
and each output separator `S != L`, yielding `_replace_literal(program,
"string", sites, S)`; this is exactly the value tier's site semantics over all
occurrences of that literal.

Pattern candidates:

- are tested before the value tier and count toward the shared
  `REVISE_CANDIDATE_LIMIT` budget;
- increment `pattern_tested` and the attempt's `tested` total;
- if they win, use the usual value edit record plus `"pattern_id"`;
- also produce the ordinary value edit shape (`kind`, `role`, `from`, `to`,
  `sites`).

The revise attempt record gains `"pattern_tested"` (0 when nothing applied).
`tested` is `pattern_tested + value_tested + structural_tested`.

Swap/insert/remove patterns are mined (their keys/shapes are tested) but their
application is deliberately not implemented: the demo has one swap key at
support 1 and no insert/remove keys at all, so no promoted instance exists.
This is stated here rather than hidden behind speculative machinery.

#### Dedupe: one absorbed occurrence

Dedupe is by canonical JSON (`json.dumps(program_to_data(program),
sort_keys=True)`). Each pattern test records its program key; the first tier
candidate with that key is skipped and the key is removed from the pending set.
This matters for `code-upper` because the pattern candidate
`{"extractors": [[["replace", "-", "-"]]], "joiner": ""}` is generated by the
baseline in **two** places:

- the value tier: source literal `"/"` → `"-"`;
- the swap tier: `["replace", "-", "/"]` → `["replace", "-", "-"]`.

The pattern test absorbs the value-tier occurrence (the occurrence the pattern
candidate replaces); the structural occurrence is a separate baseline candidate
and remains. Thus the same seven programs are tested as before, and the total
stays 22. A permanent global set would suppress both occurrences and reduce
`code-upper` to 21 (total 72), contradicting the brief's required 22/73; this
is called out under “Divergences and interpretations”.

### R4 — demo wiring

`demo.py` calls `maybe_promote_patterns(case_base, library)` immediately after
`maybe_promote`, before saving the library. Pattern events print as
`pattern: <event>` after the existing `promotion:` lines. The library summary
mirrors the templates section:

```text
patterns: 1
  P1 (value/string) support=2
```

No authored task/path/program/repair/promotion/template line changed. The only
pre-existing printed value that moved is the net size delta, because the
pattern store now occupies bytes in `library.json` (see below).

---

## Verification results

### 1. Demo 8/8, identical paths and per-task candidates, total 73

After the change, `python3 demo.py` prints the same per-task table as the
baseline above; the paths are identical and the candidate counts are
`11/14/1/4/1/13/7/22`, total **73** (exactly the baseline total; no task
changed by one).

Summary after the change: 2 templates (`T1` support 3, `T2` support 3),
1 pattern `P1` support 2, 6/7 references, paths
`search=2 revise=3 template=2`, competence check `8/8`. The two demo runs
were byte-identical, so the new path is deterministic.

### 2. P1 promoted exactly after `date-separator-dot`

Replaying the tasks and recording pattern events after each task gives:

| task | pattern events |
|------|----------------|
| name-swap | — |
| date-separator | — |
| name-swap-new | — |
| name-swap-semicolon | — |
| name-swap-pipe | — |
| date-separator-dot | `promoted P1 support=2: name-swap-semicolon, date-separator-dot` |
| date-separator-underscore | — |
| code-upper | — |

The demo line is:

```text
promotion: promoted T2 support=2: date-separator, date-separator-dot
pattern: promoted P1 support=2: name-swap-semicolon, date-separator-dot
```

Final pattern state:

```json
[{"pattern_id": "P1", "kind": "value", "role": "string",
  "support": ["name-swap-semicolon", "date-separator-dot"]}]
```

The final edit-key supports are `("value","string") -> 2`
(`name-swap-semicolon`, `date-separator-dot`) and
`("swap","replace","upper") -> 1` (`code-upper`). The swap key is therefore not
promoted, as required. No insert/remove keys exist in the demo histories.

### 3. `code-upper`: `pattern_tested >= 1`, total still 22

Saved revise attempt (the task's only revise attempt):

```json
{"stage": "revise", "source": "date-separator", "tested": 7,
 "outcome": "win", "pattern_tested": 1, "value_tested": 1,
 "structural_tested": 5, "gated": false,
 "behavior": {"passed": 0, "errors": 0}}
```

The task total is `8 template + 7 reuse + 7 revise = 22`. The pattern candidate
is the `replace "-" "/"` → `replace "-" "-"` program; it is tested once as the
pattern candidate, the value-tier duplicate is absorbed, and the structural
occurrence remains, so the seven tested programs are the same seven as in the
baseline. The winning edit is still the ordinary swap record without a
`pattern_id` (the pattern candidate lost):

```json
{"kind": "swap", "site": [0, 0],
 "from_op": ["replace", "-", "/"], "to_op": ["upper"]}
```

A direct probe of the pattern-win branch (not reached in the demo because P1 is
promoted after the only task it could solve) with a preloaded P1 and a source
needing `"/" -> "."` produced:

```json
{"edit": {"kind": "value", "role": "string", "from": "/", "to": ".",
          "sites": [[0, 0, 1]], "pattern_id": "P1"},
 "attempt": {"tested": 2, "pattern_tested": 2, "value_tested": 0,
             "structural_tested": 0, "outcome": "win"}}
```

This confirms the `pattern_id` addition and the new attempt field on the win
path. A shared-budget probe also confirmed that `budget=1` tests exactly one
pattern candidate and leaves `0` (value/structural tiers do not run).

### 4. Mining idempotence

Immediately after the final demo state, a second
`maybe_promote_patterns(case_base, library)` returned `[]`; the deep-copied
patterns before and after were equal, and the count stayed 1. A synthetic
support-growth check (2 → 3 task IDs) emitted only
`updated P1 support=3: a, b, c`; shrinking to 1 and then 0 updated support
in place without removing the pattern.

### 5. `library.json` round-trip preserves patterns

The saved tail is:

```json
{"next_template":3,"next_pattern":2,
 "templates":[...],
 "patterns":[{"pattern_id":"P1","kind":"value","role":"string",
              "support":["name-swap-semicolon","date-separator-dot"]}]}
```

Save → load produced equal `patterns`, equal `next_pattern_number` (2), and the
same template skeletons/supports. The pattern-store bytes are `+136 B` of the
`+477 B` demo net delta; the rest of the delta is unchanged from baseline. This
is the only pre-existing printed value that moved (+341 → +477).

### 6. Old-format library files still load

- A dict-format file with `next_template` and `templates` but no
  `patterns`/`next_pattern` loads with `patterns=[]`, `next_pattern_number=1`,
  and both templates intact.
- A bare-list template file also loads with `patterns=[]`.
- A file that has `patterns` but no counter derives the next number from the
  highest existing `P<n>` (a stored `P4` gives `next_pattern_number=5`, so a
  later promotion gets `P5`, not a reused ID).

### 7. Other contract checks

- `cases.py` was not modified; `dsl.py` was not modified.
- No new numeric constants were introduced; `MIN_SUPPORT_CASES` is reused and
  remains `NOVEL`.
- No ranking, admission, maintenance, gate, or template logic was changed.
- No failed attempts were mined, no MDL/size acceptance gate was added, and
  swap/insert/remove application was not implemented.
- No commit was made.

---

## Divergences and interpretations

1. **Dedupe scope.** The brief says a pattern candidate that the tier
   enumeration would also generate must be tested once, and that baseline
   totals must not move. For `code-upper` the same canonical program is
   generated by both the value and swap tiers in the baseline. A permanent
   global “already tested” set would suppress both occurrences and yield 21
   (total 72). The implementation instead lets each pattern test absorb one
   matching tier occurrence (the value-tier occurrence here), leaving the
   independent structural occurrence that the baseline already counted. This
   preserves the required 22/73 while ensuring the pattern itself adds no
   duplicate test. The dedupe key is canonical JSON, as specified.
2. **Non-value application.** Swap/insert/remove patterns are mined and
   persisted with their specified key fields, but only value/string patterns
   are applied. The demo has exactly one swap key at support 1 and no
   insert/remove keys, so no promoted instance exists; speculative application
   machinery was deliberately not built.
3. **Update events.** `updated P<n>` is emitted only when the support list
   actually changes. Re-running without change returns `[]`, which is the
   strongest reading of “second call adds nothing” and avoids repeating an
   update line after every later task. Patterns with empty support survive;
   they are not dissolved.
4. **Summary format.** The templates section is a count line plus one indented
   line per entry, so the pattern section follows the same shape:
   `patterns: 1` then `  P1 (value/string) support=2`. The brief's quoted
   `patterns: P1 (value/string) support=2` is the entry content, split in the
   same way the existing `T1: support=3` entries are split from `templates: 2`.
5. **Size accounting.** Storing `patterns` and `next_pattern` necessarily
   changes the net-size line (`+341 B` → `+477 B`; `+136 B` is the pattern
   store). No other output line changed.

---

## Fix round (BRIEF-repair-promotion-fixes.md)

Scope: F1–F3 in `solver.py`/`library.py`, F4 as this addendum plus the
status-doc record. `cases.py`/`dsl.py` untouched. No commit.

F1 supersedes R3's output-separator candidate domain and the §3 2-vs-3
pattern-win probe; both are pre-fix records. The post-fix re-verification is
in F1/F4 and the final table.

### F1 — candidate-set fidelity

`_pattern_candidates` now derives its replacement values from
`_task_separators(examples)` (target input ∪ output separators) instead of
output separators only. Literals remain every distinct string literal of the
source, and the candidate program is still `_replace_literal(program,
"string", sites, separator)` with `separator != literal`. The generator comment
states the candidate set and the subset relation plainly.

With P1 preloaded (`support=["name-swap-semicolon","date-separator-dot"]`):

- name-swap source + name-swap-semicolon examples: `_task_separators` is
  `['; ', ' ']` (the output `Taro Tanaka` contributes `' '`). Pattern candidates
  are `', ' -> '; '` and `', ' -> ' '`; the required `', ' -> '; '` is present
  and is tried first. The pattern branch wins at `tested=1,
  pattern_tested=1` with `pattern_id="P1"`; the no-pattern value tier wins at
  the same one test. Before F1 this configuration produced only
  `', ' -> ' '`; the input-side `', ' -> '; '` was outside the candidate set.
- date-separator source + date-separator-dot examples: pattern candidates are
  now `('-', '.')`, `('/', '-')`, `('/', '.')`; the win is candidate 3. See
  F4(i) for the consequence for the old 2-vs-3 probe.
- code-upper: `pattern_tested` stays 1. The source's separator domain is only
  `['-']`, so the sole pattern candidate is `'/' -> '-'`; the task total
  remains 22 and the demo is unchanged.

### F2 — pattern support pruning on maintenance

`maintain()` now prunes the removed `task_id` from every
`library.patterns` entry's `support` exactly as it already did for templates;
the pattern itself is retained (no dissolution). The comment names both
stores and the no-dissolution rule.

Verification:

- Demo run: the only committed removal is `name-swap-new`; it is in no
  pattern's support, so P1's support is
  `["name-swap-semicolon", "date-separator-dot"]` before and after
  `maintain()`. The decision
  (`removed name-swap-new (redundant, corpus still solvable)`) and the
  competence check (8/8) are unchanged.
- Targeted probe: a redundant case that was the sole supporter of one pattern
  and one of two supporters of another was removed after the
  corpus-still-solvable check; the supports became `[]` and `["name-swap"]`,
  and both patterns remained in the library. No dissolution.

### F3 — citation correction

The mining comment in `library.py` now cites Hanney & Keane 1996, "Learning
Adaptation Rules from a Case-Base", EWCBR-96, LNCS 1168, pp. 179-192, and
labels the mechanism as the adaptation-rule-learning line of CBR. Smyth &
Keane 1998 is kept only for adaptation-guided retrieval (ranking retrieval by
adaptability), which belongs to the revise gate in `solver.py`; the descent is
marked rather than presented as the same mechanism. The `solver.py` gate
comment was not touched.

### F4 — neutrality, unapplied keys, and known v1 limits

(i) **Conditional neutrality, re-verified.** The pattern pass is count-neutral
only when no pattern candidate wins and the budget does not bind. Each pattern
test absorbs one matching tier occurrence; with no win the pass is a
reordering/relabeling of test events, so the count is unchanged. That is what
the demo shows: P1 adds zero net tests and changes no per-task count. The semantic
review's pre-widening probe (output-only generator, run in memory) reproduces
a pattern win at 2 tests versus the baseline's 3 on the date-separator-dot
configuration. After F1's widening that same configuration tests 3 pattern
candidates and wins at 3, equal to the baseline's 3: the input-separator
candidate (`'/' -> '-'`) now precedes the winning output-side candidate in
both enumerations. A win can still come below the baseline when the value
tier would first test non-string-role candidates (int-role literals appear
earlier in `_literal_pairs` order); no demo source has one, so the demo's
pattern wins are count-equal (1/1 on name-swap-semicolon, 3/3 on
date-separator-dot). A synthetic probe with an int-role `slice` ahead of the
string-role `replace` shows the remaining reduction direction: pattern win at
3 tests versus the baseline's 5. The 2-vs-3 figure is therefore superseded by
F1; the conditional claim survives, with "a pattern win reduces the count"
narrowed to "a win is never above the baseline's value-tier position and can
be below it." Note: F1 and F4's parenthetical cannot both hold literally for
that configuration — the widened domain necessarily adds the losing
input-side candidate — so the code follows F1's explicit `_task_separators`
requirement and the re-verified post-fix probe is reported as 3 vs 3.

(ii) **General neutrality argument.** A pattern candidate is
`_replace_literal` over a string literal and a separator from
`_task_separators`, with `S != L`; the value tier enumerates the same
`_replace_literal` over the same domain for every literal (string, joiner, and
int when present). Pattern candidates are therefore a subset of the value
tier's candidates; this was re-checked on all four demo revise configurations
(2/2, 2/2, 3/3, 1/1 pattern candidates in the value tier, all distinct). The
scoped absorb removes one matching tier occurrence per tested pattern
candidate, so a non-winning pattern pass adds no test events. A winning
pattern pass skips the remaining tier enumeration; because its string
candidates are in the value tier's literal/separator order, the count to a
string win equals the baseline's unless the baseline would have tested
non-string candidates first. Budget binding is the other escape: if the shared
budget runs out inside the pattern pass, the tiers do not run and the
comparison is budget-limited, not neutral.

(iii) **Mined-but-not-applied set.** `_pattern_candidates` filters to
`kind == "value" and role == "string"`. Everything else that
`PATTERN_KEY_FIELDS` can mine is stored but not applied this round: swap,
insert, remove, plus value edits with `role == "int"` or `role == "joiner"`
(possible future keys; no demo instance). This now states the full unapplied
set rather than only the structural kinds.

(iv) F1–F3 above, with their verification.

### Known v1 limits (acknowledged non-fixes; next round's design inputs)

- **The key discards the learned content.** `("value", "string")` stores no
  observed from/to values and no input-side/output-side distinction, so there
  is one value/string slot forever. Support counts the edit class
  (value/string wins), not the pattern's own trigger/candidate wins (semantic
  Q2/Q4). F1 widens the candidate set to the value domain, but does not change
  the key.
- **Win-only mining with no dissolution is a ratchet.** Failed pattern
  applications are recorded only as `pattern_tested` counts; they are not
  mined. A promoted pattern is never removed (support may fall to `[]`), so an
  ineffective pattern is permanent and its support only tracks class wins
  (semantic Q3).
- **No composition consultation and no structural application.** Only revise
  consults patterns; templates still drive the front of solve, and
  swap/insert/remove and value/int/joiner patterns are not applied.

These are recorded in `docs/entry-001-status.md` as the next round's design
inputs.

### Re-verified numbers

| check | result |
|-------|--------|
| demo solved | 8/8 |
| paths | `search/search/reuse/revise/template/revise/template/revise` (unchanged) |
| per-task candidates | `11/14/1/4/1/13/7/22`, total **73** (unchanged) |
| P1 promotion | after `date-separator-dot`; `promoted P1 support=2: name-swap-semicolon, date-separator-dot`; final support same |
| swap key | support 1 (`code-upper`), not promoted |
| code-upper revise | `tested=7`, `pattern_tested=1`, `value_tested=1`, `structural_tested=5`, `gated=false`, win; task total 22 |
| maintenance | `removed name-swap-new (redundant, corpus still solvable)`; competence 8/8; T1/T2 support 3 each; references 6/7; removed case not in P1 support |
| stats | rt=14, rw=1, ra=4, rw2=3 (unchanged) |
| determinism | two runs byte-identical; sha256 `2386b94d331851bf0efa15a36f5efe7ba0d8b764d3c043ee073bad3f979e3ba4` (same as pre-fix because output is unchanged) |
| library round-trip | patterns equal, `next_pattern=2`, template skeletons/supports intact; `library.json` 503 B |
| old-format loads | dict without patterns, bare template list, and patterns without counter all still load |
| semicolon F1 probe | `', ' -> '; '` in the pattern candidates (tried first); pattern win at 1 test with `pattern_id="P1"` |
| date-dot pattern-win probe | post-F1: 3 pattern tests vs baseline 3; pre-F1 2 vs 3 no longer applies (see F4(i)) |
| sizes | pattern store **+136 B**; demo net delta **+477 B** |
| other | no new numeric constants; no commit |
