# Code review: repair-pattern promotion v1

Review performed against `BRIEF-repair-promotion.md` and the current source
(`library.py`, `solver.py`, `demo.py`, `cases.py`, `dsl.py`). All observations
below were reproduced from the code, not taken from `REPORT-repair-promotion.md`.

---

## 1. Mining

**Key abstraction.** `_pattern_key_for_edit` in `library.py` maps exactly the
four required shapes (`library.py:325-333`):

| edit kind | key produced | stored fields (`PATTERN_KEY_FIELDS`, `library.py:8-13`) |
|-----------|--------------|--------------------------------------------------------|
| value     | `("value", role)` | `role` |
| swap      | `("swap", from_op[0], to_op[0])` | `from_op`, `to_op` (names only) |
| insert    | `("insert", op[0])` | `op` |
| remove    | `("remove", op[0])` | `op` |

**Support.** `maybe_promote_patterns` iterates `case_base.all()` and uses
`case["history"]["edits"]` (winning edits only; failed attempts live in
`attempts`, not `edits`). It appends `case["task_id"]` only if not already
present, so support is the set of distinct task IDs in case-base order
(`library.py:336-347`).

**Threshold.** Promotion uses the existing `MIN_SUPPORT_CASES = 2`
(`library.py:5`) as the gate (`library.py:356`).

**IDs and persistence.** Pattern IDs are allocated by `_next_pattern_id`
(`library.py:291-294`), which consumes `library.next_pattern_number`. On load,
`next_pattern_number` is `max(saved_counter, derived_from_existing_P_ids)`
(`library.py:193-196`), so stale or missing counters cannot reuse an ID. Old
files without patterns load with `patterns = []` and counter `1`
(`library.py:171-178`).

**Idempotence / no duplication / no dissolution.** `maybe_promote_patterns`
builds a `patterns_by_key` index from the current library (`library.py:349-350`).
An existing key updates `support` in place only when the list actually changes
and emits `updated ...` (`library.py:368-370`). A brand-new key is promoted only
when support reaches the threshold (`library.py:355-367`). If a key disappears
from all histories, its pattern's support is cleared to `[]` but the pattern
is never removed (`library.py:374-379`).

Reproduced: after the full demo run, a second call returned `[]` and left the
pattern list unchanged.

**Verdict:** clean.

---

## 2. Persistence

`Library.__init__` defaults `patterns = []` and `next_pattern_number = 1`
(`library.py:156-157`). `load` accepts both the dict shape
(`templates`/`patterns`/`next_template`/`next_pattern`) and the old bare-list
shape, defaulting missing `patterns` to `[]` (`library.py:169-178`). `save`
writes `next_template`, `next_pattern`, `templates`, and `patterns`
(`library.py:208-217`). `_pattern_from_data`/`_pattern_to_data` use
`PATTERN_KEY_FIELDS` so only the per-kind fields are serialized
(`library.py:297-316`).

Reproduced:
- Save → load round-trip preserved `P1` and `next_pattern_number == 2`.
- A dict-format file with `templates` but no `patterns`/`next_pattern` loaded
  with `patterns == []` and `next_pattern_number == 1`.
- A bare-list template file also loaded with `patterns == []`.
- A file containing `P4` but no counter derived `next_pattern_number == 5`, so
  the next promotion did not reuse `P4`.

Template loading/instantiation logic is untouched.

**Verdict:** clean.

---

## 3. Application

`_revise` now receives `library` and runs pattern candidates before the value
and structural tiers (`solver.py:227-313`).

**Order.** `_pattern_candidates` selects only promoted `("value", role="string")`
patterns, sorts them by `(-len(support), numeric_pattern_id)`
(`solver.py:461`, `_pattern_order` at `solver.py:484-485`), matching the required
support-descending / pattern-id-ascending order.

**Trigger conditions.** A pattern is tried only when `library` is not `None`,
promoted value/string patterns exist, the source program has at least one string
literal, and the target outputs have at least one observed separator
(`solver.py:445-460`). The candidate set is: for each distinct string literal
`L` (in `_literal_pairs` order), for each output separator `S != L`, replace all
occurrences of `L` with `S` using `_replace_literal` (`solver.py:461-473`). This
is the same program-wide replacement semantics the value tier uses.

**Budget and counting.** Each pattern candidate decrements the shared
`REVISE_CANDIDATE_LIMIT` budget and increments `pattern_tested`; the attempt's
`tested` total is `pattern_tested + value_tested + structural_tested`
(`solver.py:302-305`). Therefore pattern candidates feed both the per-attempt
and the global `candidates_tested` counts.

**Attempt record.** The revise attempt carries `"pattern_tested"` (`solver.py:307`),
set to `0` when no pattern applies. A winning pattern candidate returns a value
edit record with the additional field `"pattern_id": <id>`
(`solver.py:466-473`).

**Swap/insert/remove.** These keys are mined and persisted, but
`_pattern_candidates` explicitly filters them out (`solver.py:450-454`), so no
speculative application machinery exists.

Reproduced:
- `code-upper` revise attempt: `pattern_tested=1`, `value_tested=1`,
  `structural_tested=5`, total `7`, task total `22`.
- A preloaded `P1` with a source needing `"/" -> "."` produced a revise win
  whose edit record contained `"pattern_id": "P1"` and attempt record
  `"pattern_tested": 2`.

**Verdict:** clean.

---

## 4. Deduplication

The dedupe state is `pattern_occurrences_to_absorb`, a local `set` of canonical
JSON program keys created fresh for each `_revise` call (`solver.py:252`).

- **Pattern-vs-pattern:** The pattern loop itself skips a candidate whose key is
  already in the set (`solver.py:260-261`), so the same program generated by
  multiple patterns is tested only once.
- **Pattern-vs-tier:** Each tested pattern candidate adds its key to the set
  (`solver.py:266`). The value and structural generators are wrapped with
  `_remaining_candidates` (`solver.py:488-496`), which removes the key and
  skips the *first* matching tier occurrence it sees.

**What this means for `code-upper`.** The source is
`{"extractors": [[["replace", "-", "/"]]], "joiner": ""}`. `P1` produces the
candidate `"/" -> "-"` (program `replace - -`). This program is also produced
by the value tier (literal `"/"` → `"-"`) and by the swap tier
(`replace - /` → `replace - -`). The trace shows:

1. Pattern tests `replace - -` once (`pattern_tested=1`) and records its key.
2. The value-tier occurrence of `replace - -` is absorbed (skipped), but a
   separate value-tier candidate `joiner "" -> "-"` is still tested
   (`value_tested=1`).
3. The swap-tier occurrence of `replace - -` is *not* absorbed; it is tested
   in the structural tier (`structural_tested=5` includes it).

So the code dedupes **one tier occurrence per pattern-candidate key** and keeps
any additional independent occurrences the baseline already generated. The same
seven distinct programs are executed as in the baseline, preserving the required
`22` candidates for `code-upper` and total `73`.

**Gaps the dedupe does not cover.**
- It is local to one `_revise` call, so the same program can be tested again
  when a different source case goes through its own `_revise`.
- Within a single `_revise`, after `_remaining_candidates` removes a key on the
  first tier hit, any *later* tier occurrence of the same program is yielded and
  tested. The current generators do not produce such later duplicates in the
  demo, but the data structure would not prevent it.
- Pattern-vs-pattern duplicates are covered, but only because the pattern loop
  consults the same set.

This is a deliberate design judgment: strict global canonical-JSON dedupe would
have dropped the structural `replace - -` occurrence and produced `21`
candidates for `code-upper` (`72` total), violating the brief's requirement that
baseline totals not move. The implementation's narrower "absorb one matching
occurrence" rule satisfies the brief's stated constraints.

**Verdict:** judgment call — the behavior is internally consistent and meets the
letter of the brief (pattern candidate tested once, baseline totals preserved),
but the dedupe scope is intentionally narrower than a global per-program set.

---

## 5. Non-goals

- **Ranking:** `_rank_cases` (`solver.py:580-587`) is unchanged.
- **Templates:** `maybe_promote`, `_promote`, anti-unification, and template
  loading/saving are unchanged except for the addition of `next_pattern` to the
  saved JSON.
- **Admission:** `classify_admission` (`solver.py:134-145`) is unchanged.
- **Maintenance:** `maintain` (`solver.py:148-186`) is unchanged.
- **Execution-eligibility gate:** `_behavior` and the `eligible`/`gated` logic
  inside `_revise` (`solver.py:243-245`) are unchanged; structural tiers still
  run only when the source executes without `DslError`.
- **Demo output:** The only new lines are the `pattern: promoted P1 ...` line
  and the `patterns: ...` summary block. The per-task paths and candidate counts
  are `11/14/1/4/1/13/7/22` (total `73`), matching the pre-change baseline.
  `net size delta` moved from `+341 B` to `+477 B` because `library.json` now
  stores the pattern and its counter.

**Verdict:** clean.

---

## 6. Determinism

Two consecutive `python3 demo.py` runs produced byte-identical output:

```text
2386b94d331851bf0efa15a36f5efe7ba0d8b764d3c043ee073bad3f979e3ba4  demo_run_1
2386b94d331851bf0efa15a36f5efe7ba0d8b764d3c043ee073bad3f979e3ba4  demo_run_2
```

**Verdict:** clean.

---

## Verdict summary

| item | verdict | note |
|------|---------|------|
| 1. Mining | clean | keys, support, IDs, idempotence, no dissolution all correct |
| 2. Persistence | clean | round-trip, old-format loading, counter derivation correct |
| 3. Application | clean | order, trigger, budget, `pattern_tested`, `pattern_id` win record correct |
| 4. Dedupe | judgment call | absorbs one tier occurrence per pattern key; preserves required 22/73 totals; gaps are across sources and later identical tier occurrences |
| 5. Non-goals | clean | ranking, templates, admission, maintain, gate, and demo output unchanged except intended pattern/size additions |
| 6. Determinism | clean | observed SHA-256 `2386b94d...979e3ba4` identical across two runs |
