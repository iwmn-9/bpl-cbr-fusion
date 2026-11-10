import itertools
import re

from dsl import DslError, apply_program
from library import instantiate, materialize, slot_sites, slots_of

FIELD_INDEX_LIMIT = 3  # NOVEL: try field indexes 0..2; the demo needs 0 and 1.
MAX_OBSERVED_SEPARATORS = 8  # NOVEL: cap distinct observed separators per side.
MAX_SINGLE_CHAINS = 64  # NOVEL: cap on generated single-chain candidates.
MAX_CHAIN_PAIRS = 1024  # NOVEL: cap on chain pairs tried by the fallback search.


def solve(examples, case_base, library=None):
    tested = 0
    program, count = _solve_with_templates(examples, library, case_base)
    tested += count
    if program is not None:
        return program, "template", tested

    for case in _rank_cases(examples, case_base.all()):
        if library is None and "template_id" in case:
            continue
        program = materialize(case, library)
        tested += 1
        if _matches(program, examples):
            return program, "reuse", tested

    program, count = _search(examples)
    tested += count
    if program is not None:
        return program, "search", tested
    return None, "no exact match in case base reuse or bounded search", tested


def _solve_with_templates(examples, library, case_base):
    if library is None:
        return None, 0
    tested = 0
    for template in library.templates:
        skeleton = template["skeleton"]
        names = slots_of(skeleton)
        domains = _slot_domains(skeleton, template["support"], examples, case_base)
        for values in itertools.product(*(domains[name] for name in names)):
            program = instantiate(skeleton, dict(zip(names, values)))
            tested += 1
            if _matches(program, examples):
                return program, tested
    return None, tested


def _slot_domains(template, support, examples, case_base):
    separators = _observed_separators([pair[0] for pair in examples])
    for separator in _observed_separators([pair[1] for pair in examples]):
        if separator not in separators:
            separators.append(separator)

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
