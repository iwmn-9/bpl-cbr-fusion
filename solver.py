import re

from dsl import DslError, apply_program

FIELD_INDEX_LIMIT = 3  # NOVEL: try field indexes 0..2; the demo needs 0 and 1.
MAX_OBSERVED_SEPARATORS = 8  # NOVEL: cap distinct observed separators per side.
MAX_SINGLE_CHAINS = 64  # NOVEL: cap on generated single-chain candidates.
MAX_CHAIN_PAIRS = 1024  # NOVEL: cap on chain pairs tried by the fallback search.


def solve(examples, case_base):
    for case in _rank_cases(examples, case_base.all()):
        if _matches(case["program"], examples):
            return case["program"], "reuse"
    program = _search(examples)
    if program is not None:
        return program, "search"
    return None, "no exact match in case base reuse or bounded search"


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

    for chain in chains:
        program = {"extractors": [chain], "joiner": ""}
        if _matches(program, examples):
            return program

    pairs_tested = 0
    for first in chains:
        for second in chains:
            if pairs_tested >= MAX_CHAIN_PAIRS:
                return None
            pairs_tested += 1
            for joiner in output_separators:
                program = {"extractors": [first, second], "joiner": joiner}
                if _matches(program, examples):
                    return program
    return None


def _observed_separators(texts):
    separators = []
    seen = set()
    for text in texts:
        for separator in re.findall(r"\W+", text):
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
