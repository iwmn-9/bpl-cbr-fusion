import itertools
import re

from dsl import DslError, apply_program
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
# full tier enumeration first (measured: 88 tests on date-separator, whose
# search then needs 5).
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
    program, source_template, bindings, count = _solve_with_templates(
        examples, library, case_base
    )
    tested += count
    if program is not None:
        return (
            program,
            _report("template", source_template=source_template, bindings=bindings),
            tested,
        )

    revise_sources = []
    for case in _rank_cases(examples, case_base.all()):
        if library is None and "template_id" in case:
            continue
        program = materialize(case, library)
        tested += 1
        if _matches(program, examples):
            return program, _report("reuse", source_case=case["task_id"]), tested
        if len(revise_sources) < REVISE_SOURCE_LIMIT:
            revise_sources.append((case, program))

    # Revise is the third step of the CBR cycle (Aamodt & Plaza 1994):
    # adapt a retrieved solution locally instead of discarding it.
    revise_budget = REVISE_CANDIDATE_LIMIT
    for case, source_program in revise_sources:
        program, edits, count, revise_budget = _revise(
            examples, source_program, revise_budget
        )
        tested += count
        if program is not None:
            return (
                program,
                _report("revise", source_case=case["task_id"], edits=edits),
                tested,
            )
        if revise_budget == 0:
            break

    program, count = _search(examples)
    tested += count
    if program is not None:
        return program, _report("search"), tested
    return (
        None,
        _report(
            None,
            reason="no exact match in case base reuse or bounded search",
        ),
        tested,
    )


def _report(
    path,
    reason=None,
    source_case=None,
    source_template=None,
    bindings=None,
    edits=None,
):
    return {
        "path": path,
        "reason": reason,
        "source_case": source_case,
        "source_template": source_template,
        "bindings": bindings,
        "edits": [] if edits is None else edits,
    }


def _revise(examples, source_program, budget):
    domains = {
        "string": _task_separators(examples),
        "int": list(range(FIELD_INDEX_LIMIT)),
        "joiner": _joiner_domain(examples),
    }
    tested = 0
    for candidate, edit in _repair_candidates(source_program, domains):
        if budget == 0:
            break
        budget -= 1
        tested += 1
        if _matches(candidate, examples):
            return candidate, [edit], tested, budget
    return None, [], tested, budget


# Edit records' sites/site are indices into the SOURCE program (the program
# before the edit is applied).
def _repair_candidates(program, domains):
    yield from _value_candidates(program, domains)
    # Structural tiers are mutation-style operators over one op occurrence
    # (Koza 1992, genetic programming). Tiers are ordered by edit size —
    # value, swap, insert, remove — which orders the edits tried, not their
    # expected cost: a source with no winning repair pays for all four tiers.
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


def _matches(program, examples):
    for input_text, expected in examples:
        try:
            if apply_program(program, input_text) != expected:
                return False
        except DslError:
            return False
    return True


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
