import json


class DslError(ValueError):
    pass


def apply_program(program, text):
    parts = [_apply_chain(chain, text) for chain in program["extractors"]]
    return program["joiner"].join(parts)


def _apply_chain(chain, text):
    result = text
    for op in chain:
        result = _apply_op(op, result)
    return result


def _apply_op(op, text):
    try:
        name = op[0]
        if name == "field":
            _, separator, index = op
            return text.split(separator)[index]
        if name == "replace":
            _, old, new = op
            return text.replace(old, new)
        if name == "upper":
            return text.upper()
        if name == "lower":
            return text.lower()
        if name == "strip":
            return text.strip()
        if name == "slice":
            _, start, end = op
            return text[start:end]
        raise DslError(f"unknown op: {name!r}")
    except DslError:
        raise
    except (IndexError, TypeError, ValueError) as exc:
        raise DslError(f"cannot apply op {op!r} to {text!r}: {exc}") from exc


def program_to_data(program):
    return {
        "extractors": [[list(op) for op in chain] for chain in program["extractors"]],
        "joiner": program["joiner"],
    }


def program_from_data(data):
    return {
        "extractors": [[tuple(op) for op in chain] for chain in data["extractors"]],
        "joiner": data["joiner"],
    }


def program_repr(program):
    return json.dumps(program_to_data(program), ensure_ascii=False)
