import itertools
import json
import re

from cases import CaseBase
from dsl import DslError, apply_program, program_to_data
from library import (
    OP_ARG_ROLES,
    instantiate,
    materialize,
    slot_sites,
    slots_of,
)

FIELD_INDEX_LIMIT = 3  # NOVEL: try field indexes 0..2; the demo needs 0 and 1.
REVISE_SOURCE_LIMIT = 3  # NOVEL: cap on cases tried as revision sources; tunable.
# NOVEL: total repaired programs revise may test per solve() call. Structural
# enumeration is wide, so the budget is shared across all sources and tiers.
# The budget caps revise's worst case far below the search stage's own worst
# case (MAX_CHAIN_PAIRS pairs, each with several joiners). It does not make a
# failed revise cheap on small tasks: a task with no winning repair pays the
# full eligible-tier enumeration first (measured after the execution-eligibility
# gate: 8 value tests on date-separator, whose search then needs 5; before the
# gate the same task paid 88, 80 of them structural tests from a source that
# raised DslError on every target input).
REVISE_CANDIDATE_LIMIT = 256
MAX_OBSERVED_SEPARATORS = 8  # NOVEL: cap distinct observed separators per side.
MAX_SINGLE_CHAINS = 64  # NOVEL: cap on generated single-chain candidates.
MAX_CHAIN_PAIRS = 1024  # NOVEL: cap on chain pairs tried by the fallback search.

# Parts inventory for structural repairs. Every op is string -> string, so any
# op fits any slot (component-based synthesis: Jha et al. 2010,
# "Oracle-Guided Component-Based Program Synthesis"). Slice is excluded because
# its integer domains are not example-derived, matching the search stage.
PARTS_INVENTORY = tuple(name for name in OP_ARG_ROLES if name != "slice")


def solve(examples, case_base, library=None):
    tested = 0
    attempts = []
    program, source_template, bindings, count = _solve_with_templates(
        examples, library, case_base
    )
    tested += count
    attempts.append(
        {
            "stage": "template",
            "tested": count,
            "outcome": "win" if program is not None else "miss",
            "template": source_template,
        }
    )
    if program is not None:
        return (
            program,
            _report(
                "template",
                source_template=source_template,
                bindings=bindings,
                attempts=attempts,
            ),
            tested,
        )

    revise_sources = []
    for case in _rank_cases(examples, case_base.all()):
        if library is None and "template_id" in case:
            continue
        program = materialize(case, library)
        tested += 1
        first_failure = _first_failure(program, examples)
        attempts.append(
            {
                "stage": "reuse",
                "source": case["task_id"],
                "outcome": "win" if first_failure is None else "miss",
                "first_failure": first_failure,
            }
        )
        if first_failure is None:
            return (
                program,
                _report("reuse", source_case=case["task_id"], attempts=attempts),
                tested,
            )
        if len(revise_sources) < REVISE_SOURCE_LIMIT:
            revise_sources.append((case, program))

    # Revise is the third step of the CBR cycle (Aamodt & Plaza 1994):
    # adapt a retrieved solution locally instead of discarding it.
    revise_budget = REVISE_CANDIDATE_LIMIT
    for case, source_program in revise_sources:
        program, edits, attempt, revise_budget = _revise(
            examples, case, source_program, revise_budget, library
        )
        attempts.append(attempt)
        tested += attempt["tested"]
        if program is not None:
            return (
                program,
                _report(
                    "revise",
                    source_case=case["task_id"],
                    edits=edits,
                    attempts=attempts,
                ),
                tested,
            )
        if revise_budget == 0:
            break

    program, count = _search(examples)
    tested += count
    attempts.append(
        {
            "stage": "search",
            "tested": count,
            "outcome": "win" if program is not None else "miss",
        }
    )
    if program is not None:
        return program, _report("search", attempts=attempts), tested
    return (
        None,
        _report(
            None,
            reason="no exact match in case base reuse or bounded search",
            attempts=attempts,
        ),
        tested,
    )


def classify_admission(examples, case_base, library):
    # Zero search: reuse the template stage's own enumeration. The check runs
    # before the new case is added, so the base and library are the pre-add ones.
    program, _, _, _ = _solve_with_templates(examples, library, case_base)
    if program is not None:
        return "absorbed"
    for case in case_base.all():
        if library is None and "template_id" in case:
            continue
        if _matches(materialize(case, library), examples):
            return "redundant"
    return "novel"


def maintain(case_base, library):
    # The CBR utility problem (Smyth & Cunningham 1996): an ever-growing case
    # base degrades retrieval, so retention must be earned. Usage statistics
    # are distilled into tombstones before the body is deleted, so the record
    # of what was removed and how it performed survives.
    decisions = []
    for case in case_base.all():
        if case.get("admission") != "redundant":
            continue
        reduced = _case_base_without(case_base, case)
        broken_task = _first_unsolved_task(reduced, case, library)
        if broken_task is not None:
            decisions.append(
                f"kept {case['task_id']} (removal breaks {broken_task})"
            )
            continue
        removed_id = case["task_id"]
        case_base.removed.append(
            {
                "task_id": removed_id,
                "admission": case.get("admission"),
                "stats": dict(case.get("stats", {})),
                "decision": "removed",
            }
        )
        if library is not None:
            # Support is live recurrence evidence, not provenance: a removed
            # case must not keep counting toward a template's or pattern's
            # support. Patterns are not dissolved here even if emptied.
            for template in library.templates:
                template["support"] = [
                    task_id
                    for task_id in template["support"]
                    if task_id != removed_id
                ]
            for pattern in library.patterns:
                pattern["support"] = [
                    task_id
                    for task_id in pattern["support"]
                    if task_id != removed_id
                ]
        case_base.remove(case)
        decisions.append(
            f"removed {removed_id} (redundant, corpus still solvable)"
        )
    return decisions


def _case_base_without(case_base, removed_case):
    reduced = CaseBase()
    for case in case_base.all():
        if case is not removed_case:
            reduced.add(case)
    return reduced


def _first_unsolved_task(reduced, removed_case, library):
    tasks = [(case["task_id"], case["examples"]) for case in reduced.all()]
    tasks.append((removed_case["task_id"], removed_case["examples"]))
    for task_id, examples in tasks:
        program, _, _ = solve(examples, reduced, library)
        if program is None:
            return task_id
    return None


def _report(
    path,
    reason=None,
    source_case=None,
    source_template=None,
    bindings=None,
    edits=None,
    attempts=None,
):
    return {
        "path": path,
        "reason": reason,
        "source_case": source_case,
        "source_template": source_template,
        "bindings": bindings,
        "edits": [] if edits is None else edits,
        "attempts": [] if attempts is None else attempts,
    }


def _revise(examples, source_case, source_program, budget, library):
    domains = {
        "string": _task_separators(examples),
        "int": list(range(FIELD_INDEX_LIMIT)),
        "joiner": _joiner_domain(examples),
    }
    # Adaptation-guided retrieval (Smyth & Keane 1998) ranks cases by
    # adaptability; this gate applies that principle one step later and one
    # bit coarser. It restricts STRUCTURAL repair effort by executability:
    # the source must run without DslError on every target input. The value
    # tier is never gated, so a non-executing source can still win there
    # (name-swap-semicolon: gated=true, value-tier win). Measured on the demo:
    # name-swap raises DslError on every date-separator input, so the gate
    # blocks 80 of that revise's 88 candidates and leaves its 8 value-tier
    # ones; code-upper's cleanly executing source still reaches its structural
    # swap win. Retrieval ranking is unchanged this round.
    behavior = _behavior(source_program, examples)
    eligible = behavior["errors"] == 0
    gated = not eligible

    winner = None
    winner_edit = None
    pattern_tested = 0
    value_tested = 0
    structural_tested = 0
    pattern_occurrences_to_absorb = set()

    # Adaptation outcomes learned from earlier revise wins are tried as value
    # repairs before the generic tiers. Each distinct pattern candidate absorbs
    # one matching tier occurrence below, so it is not tested twice; an
    # occurrence the baseline already enumerated separately still runs.
    for candidate, edit in _pattern_candidates(source_program, examples, library):
        key = _program_key(candidate)
        if key in pattern_occurrences_to_absorb:
            continue
        if budget == 0:
            break
        budget -= 1
        pattern_tested += 1
        pattern_occurrences_to_absorb.add(key)
        if _matches(candidate, examples):
            winner = candidate
            winner_edit = edit
            break

    # Value repairs are always tried, even for a non-executing source.
    if winner is None:
        for candidate, edit in _remaining_candidates(
            _value_candidates(source_program, domains),
            pattern_occurrences_to_absorb,
        ):
            if budget == 0:
                break
            budget -= 1
            value_tested += 1
            if _matches(candidate, examples):
                winner = candidate
                winner_edit = edit
                break

    if winner is None and eligible and budget > 0:
        for candidate, edit in _remaining_candidates(
            _structural_candidates(source_program, domains),
            pattern_occurrences_to_absorb,
        ):
            if budget == 0:
                break
            budget -= 1
            structural_tested += 1
            if _matches(candidate, examples):
                winner = candidate
                winner_edit = edit
                break

    edits = [] if winner is None else [winner_edit]
    attempt = {
        "stage": "revise",
        "source": source_case["task_id"],
        "tested": pattern_tested + value_tested + structural_tested,
        "outcome": "win" if winner is not None else "miss",
        "pattern_tested": pattern_tested,
        "value_tested": value_tested,
        "structural_tested": structural_tested,
        "gated": gated,
        "behavior": behavior,
    }
    return winner, edits, attempt, budget


def _behavior(program, examples):
    # passed counts exact matches; errors counts DslError. An executed-but-wrong
    # example is neither, so passed + errors can be less than len(examples).
    passed = 0
    errors = 0
    for input_text, expected in examples:
        try:
            actual = apply_program(program, input_text)
        except DslError:
            errors += 1
            continue
        if actual == expected:
            passed += 1
    return {"passed": passed, "errors": errors}


# Edit records' sites/site are indices into the SOURCE program (the program
# before the edit is applied).
def _structural_candidates(program, domains):
    # Structural tiers are mutation-style operators over one op occurrence
    # (Koza 1992, genetic programming). Tiers are ordered by edit size —
    # value, swap, insert, remove — which orders the edits tried, not their
    # expected cost: a source with no winning repair pays for every eligible
    # tier.
    yield from _swap_candidates(program, domains)
    yield from _insert_candidates(program, domains)
    yield from _remove_candidates(program)


def _value_candidates(program, domains):
    for role, old_value, sites in _literal_pairs(program):
        for new_value in domains[role]:
            if new_value == old_value:
                continue
            yield _replace_literal(program, role, sites, new_value), {
                "kind": "value",
                "role": role,
                "from": old_value,
                "to": new_value,
                "sites": sites,
            }


def _swap_candidates(program, domains):
    for chain_idx, chain in enumerate(program["extractors"]):
        for op_idx, old_op in enumerate(chain):
            for op_name in PARTS_INVENTORY:
                for values in _op_value_products(op_name, domains):
                    op = (op_name,) + values
                    # A swap back to the same op is not a repair.
                    if op == tuple(old_op):
                        continue
                    candidate = _program_copy(program)
                    candidate["extractors"][chain_idx][op_idx] = list(op)
                    yield candidate, {
                        "kind": "swap",
                        "site": [chain_idx, op_idx],
                        "from_op": list(old_op),
                        "to_op": list(op),
                    }


def _insert_candidates(program, domains):
    for chain_idx, chain in enumerate(program["extractors"]):
        for position in range(len(chain) + 1):
            for op_name in PARTS_INVENTORY:
                for values in _op_value_products(op_name, domains):
                    op = (op_name,) + values
                    candidate = _program_copy(program)
                    candidate["extractors"][chain_idx].insert(position, list(op))
                    yield candidate, {
                        "kind": "insert",
                        "site": [chain_idx, position],
                        "op": list(op),
                    }


def _remove_candidates(program):
    for chain_idx, chain in enumerate(program["extractors"]):
        for op_idx, old_op in enumerate(chain):
            candidate = _program_copy(program)
            del candidate["extractors"][chain_idx][op_idx]
            yield candidate, {
                "kind": "remove",
                "site": [chain_idx, op_idx],
                "op": list(old_op),
            }


def _op_value_products(op_name, domains):
    # product() over no roles yields one empty tuple for zero-arg ops.
    yield from itertools.product(
        *(domains[role] for role in OP_ARG_ROLES[op_name])
    )


def _program_copy(program):
    return {
        "extractors": [
            [list(op) for op in chain] for chain in program["extractors"]
        ],
        "joiner": program["joiner"],
    }


def _literal_pairs(program):
    pairs = {}
    for extractor_idx, chain in enumerate(program["extractors"]):
        for op_idx, op in enumerate(chain):
            # arg_idx is 0-based over op[1:]; the op name is not counted.
            for arg_idx, (role, value) in enumerate(
                zip(OP_ARG_ROLES[op[0]], op[1:])
            ):
                sites = pairs.setdefault((role, value), [])
                sites.append([extractor_idx, op_idx, arg_idx])
    joiner = program["joiner"]
    pairs.setdefault(("joiner", joiner), []).append(["joiner"])
    return [(role, value, sites) for (role, value), sites in pairs.items()]


def _replace_literal(program, role, sites, new_value):
    if role == "joiner":
        return {"extractors": program["extractors"], "joiner": new_value}
    candidate = _program_copy(program)
    for extractor_idx, op_idx, arg_idx in sites:
        candidate["extractors"][extractor_idx][op_idx][arg_idx + 1] = new_value
    return candidate


def _pattern_candidates(program, examples, library):
    if library is None:
        return
    # Only value/string patterns are applied this round: swap/insert/remove
    # and value/int or value/joiner keys are mined but not applied (the demo
    # promotes no such instance; its only swap key stands at support 1).
    patterns = [
        pattern
        for pattern in library.patterns
        if pattern["kind"] == "value" and pattern["role"] == "string"
    ]
    if not patterns:
        return
    # Candidate values use the value tier's separator domain: the target
    # examples' input-union-output separators (_task_separators). Pattern
    # candidates therefore remain a subset of the value tier's string-role
    # candidates, so the scoped-absorb dedupe accounting is unchanged.
    separators = _task_separators(examples)
    string_literals = _string_literals(program)
    if not separators or not string_literals:
        return
    for pattern in sorted(patterns, key=_pattern_order):
        for literal, sites in string_literals:
            for separator in separators:
                if separator == literal:
                    continue
                yield _replace_literal(program, "string", sites, separator), {
                    "kind": "value",
                    "role": "string",
                    "from": literal,
                    "to": separator,
                    "sites": sites,
                    "pattern_id": pattern["pattern_id"],
                }


def _string_literals(program):
    return [
        (value, sites)
        for role, value, sites in _literal_pairs(program)
        if role == "string"
    ]


def _pattern_order(pattern):
    return (-len(pattern["support"]), int(pattern["pattern_id"][1:]))


def _remaining_candidates(candidates, pattern_occurrences_to_absorb):
    # Each pattern test absorbs one matching tier occurrence; a program the
    # baseline tiers enumerate more than once keeps its extra baseline counts.
    for candidate, edit in candidates:
        key = _program_key(candidate)
        if key in pattern_occurrences_to_absorb:
            pattern_occurrences_to_absorb.remove(key)
            continue
        yield candidate, edit


def _program_key(program):
    return json.dumps(
        program_to_data(program), sort_keys=True, ensure_ascii=False
    )


def _joiner_domain(examples):
    values = _observed_separators([pair[1] for pair in examples])
    if "" not in values:
        values.append("")
    return values


def _solve_with_templates(examples, library, case_base):
    if library is None:
        return None, None, None, 0
    tested = 0
    for template in library.templates:
        skeleton = template["skeleton"]
        names = slots_of(skeleton)
        domains = _slot_domains(skeleton, template["support"], examples, case_base)
        for values in itertools.product(*(domains[name] for name in names)):
            bindings = dict(zip(names, values))
            program = instantiate(skeleton, bindings)
            tested += 1
            if _matches(program, examples):
                return program, template["id"], bindings, tested
    return None, None, None, tested


def _slot_domains(template, support, examples, case_base):
    separators = _task_separators(examples)
    int_slots, joiner_slots = _slot_positions(template)
    support_values = _support_slot_values(support, case_base)
    domains = {}
    for name in slots_of(template):
        if name in int_slots:
            domains[name] = list(range(FIELD_INDEX_LIMIT))
            continue
        values = list(separators)
        for value in support_values.get(name, []):
            if value not in values:
                values.append(value)
        if name in joiner_slots and "" not in values:
            values.append("")
        domains[name] = values
    return domains


def _task_separators(examples):
    separators = _observed_separators([pair[0] for pair in examples])
    for separator in _observed_separators([pair[1] for pair in examples]):
        if separator not in separators:
            separators.append(separator)
    return separators


def _slot_positions(template):
    int_slots = set()
    joiner_slots = set()
    for name, role in slot_sites(template):
        if role == "int":
            int_slots.add(name)
        elif role == "joiner":
            joiner_slots.add(name)
    return int_slots, joiner_slots


def _support_slot_values(support, case_base):
    support_ids = set(support)
    values = {}
    for case in case_base.all():
        if case["task_id"] not in support_ids:
            continue
        for name, value in case.get("bindings", {}).items():
            slot_values = values.setdefault(name, [])
            if value not in slot_values:
                slot_values.append(value)
    return values


def _rank_cases(examples, cases):
    query_tokens = _example_tokens(examples)
    scored = []
    for index, case in enumerate(cases):
        score = _token_overlap(query_tokens, _example_tokens(case["examples"]))
        scored.append((score, index, case))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [case for _, _, case in scored]


def _example_tokens(examples):
    # Punctuation stays in the token set: structural overlap is the useful signal here.
    tokens = set()
    for input_text, _ in examples:
        tokens.update(re.findall(r"\w+|[^\w\s]", input_text.lower()))
    return tokens


def _token_overlap(left, right):
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _first_failure(program, examples):
    for input_text, expected in examples:
        try:
            actual = apply_program(program, input_text)
        except DslError:
            return {"input": input_text, "expected": expected, "actual": None}
        if actual != expected:
            return {"input": input_text, "expected": expected, "actual": actual}
    return None


def _matches(program, examples):
    return _first_failure(program, examples) is None


def _search(examples):
    input_separators = _observed_separators([pair[0] for pair in examples])
    output_separators = _observed_separators([pair[1] for pair in examples])
    chains = _single_chains(input_separators, output_separators)

    tested = 0
    for chain in chains:
        program = {"extractors": [chain], "joiner": ""}
        tested += 1
        if _matches(program, examples):
            return program, tested

    pairs_tested = 0
    for first in chains:
        for second in chains:
            if pairs_tested >= MAX_CHAIN_PAIRS:
                return None, tested
            pairs_tested += 1
            for joiner in output_separators:
                program = {"extractors": [first, second], "joiner": joiner}
                tested += 1
                if _matches(program, examples):
                    return program, tested
    return None, tested


def _observed_separators(texts):
    separators = []
    seen = set()
    for text in texts:
        # Underscore is a word character in Python's regex classes but a separator here.
        for separator in re.findall(r"[\W_]+", text):
            if separator in seen:
                continue
            seen.add(separator)
            separators.append(separator)
            if len(separators) == MAX_OBSERVED_SEPARATORS:
                return separators
    return separators


def _single_chains(input_separators, output_separators):
    candidates = []
    for separator in input_separators:
        for index in range(FIELD_INDEX_LIMIT):
            candidates.append([("field", separator, index)])
    candidates.append([("strip",)])
    # Replace candidates cover separator rewrites that field/strip alone cannot express.
    for old in input_separators:
        for new in output_separators:
            candidates.append([("replace", old, new)])

    chains = []
    seen = set()
    for chain in candidates:
        key = tuple(chain)
        if key in seen:
            continue
        seen.add(key)
        chains.append(chain)
        if len(chains) == MAX_SINGLE_CHAINS:
            break
    return chains
