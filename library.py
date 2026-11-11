import json

from dsl import program_from_data, program_to_data

MIN_SUPPORT_CASES = 2  # NOVEL: smallest count evidencing recurrence; tunable.

# Key fields stored alongside a pattern's kind; the tuple forms its identity.
PATTERN_KEY_FIELDS = {
    "value": ("role",),
    "swap": ("from_op", "to_op"),
    "insert": ("op",),
    "remove": ("op",),
}

OP_ARG_ROLES = {
    "field": ("string", "int"),
    "replace": ("string", "string"),
    "slice": ("int", "int"),
    "upper": (),
    "lower": (),
    "strip": (),
}


def slot_name(value):
    if isinstance(value, dict) and "slot" in value:
        return value["slot"]
    return None


def slot_sites(template):
    for chain in template["extractors"]:
        for op in chain:
            for role, arg in zip(OP_ARG_ROLES[op[0]], op[1:]):
                name = slot_name(arg)
                if name is not None:
                    yield name, role
    name = slot_name(template["joiner"])
    if name is not None:
        yield name, "joiner"


def slots_of(template):
    names = []
    for name, _ in slot_sites(template):
        if name not in names:
            names.append(name)
    return names


# Anti-unification / least general generalization, restricted to structurally
# identical skeletons (Plotkin 1970); the promotion loop is the same family of
# move as DreamCoder's library learning (Ellis et al. 2021), minus the neural
# parts and minus its MDL acceptance test.
def anti_unify(program_a, program_b):
    extractors_a = program_a["extractors"]
    extractors_b = program_b["extractors"]
    if len(extractors_a) != len(extractors_b):
        return None

    slot_names = {}
    used_names = set(slots_of(program_a)) | set(slots_of(program_b))
    template_extractors = []
    for chain_a, chain_b in zip(extractors_a, extractors_b):
        if len(chain_a) != len(chain_b):
            return None
        template_chain = []
        for op_a, op_b in zip(chain_a, chain_b):
            if len(op_a) != len(op_b) or op_a[0] != op_b[0]:
                return None
            template_op = [op_a[0]]
            for value_a, value_b in zip(op_a[1:], op_b[1:]):
                template_op.append(
                    _anti_unify_value(value_a, value_b, slot_names, used_names)
                )
            template_chain.append(tuple(template_op))
        template_extractors.append(template_chain)

    joiner = _anti_unify_value(
        program_a["joiner"], program_b["joiner"], slot_names, used_names
    )
    return {"extractors": template_extractors, "joiner": joiner}


def _anti_unify_value(value_a, value_b, slot_names, used_names):
    name_a = slot_name(value_a)
    name_b = slot_name(value_b)
    if name_a is not None and name_b is not None:
        if name_a == name_b:
            return value_a
        pair = ("slot", name_a, name_b)
    elif name_a is not None:
        return value_a
    elif name_b is not None:
        return value_b
    elif value_a == value_b:
        return value_a
    else:
        pair = (value_a, value_b)

    if pair not in slot_names:
        name = _fresh_slot_name(used_names)
        slot_names[pair] = name
        used_names.add(name)
    return {"slot": slot_names[pair]}


def _fresh_slot_name(used_names):
    index = 1
    while f"s{index}" in used_names:
        index += 1
    return f"s{index}"


def instantiate(template, bindings):
    extractors = []
    for chain in template["extractors"]:
        concrete_chain = []
        for op in chain:
            concrete_op = [op[0]]
            for arg in op[1:]:
                concrete_op.append(_fill(arg, bindings))
            concrete_chain.append(tuple(concrete_op))
        extractors.append(concrete_chain)
    return {
        "extractors": extractors,
        "joiner": _fill(template["joiner"], bindings),
    }


def _fill(value, bindings):
    name = slot_name(value)
    if name is None:
        return value
    if name not in bindings:
        raise KeyError(f"missing binding for slot {name!r}")
    return bindings[name]


def materialize(case, library):
    if "template_id" not in case:
        return case["program"]
    if library is None:
        raise ValueError(
            f"case {case['task_id']!r} references {case['template_id']} "
            "but no library was given"
        )
    template = library.get(case["template_id"])
    return instantiate(template["skeleton"], case["bindings"])


class Library:
    def __init__(self):
        self.templates = []
        self.next_template_number = 1
        self.patterns = []
        self.next_pattern_number = 1

    def load(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                stored = json.load(handle)
        except FileNotFoundError:
            self.templates = []
            self.next_template_number = 1
            self.patterns = []
            self.next_pattern_number = 1
            return
        if isinstance(stored, dict):
            templates_data = stored["templates"]
            patterns_data = stored.get("patterns", [])
            saved_next_template = stored.get("next_template", 0)
            saved_next_pattern = stored.get("next_pattern", 0)
        else:
            templates_data = stored
            patterns_data = []
            saved_next_template = 0
            saved_next_pattern = 0
        self.templates = [
            {
                "id": template["id"],
                "skeleton": program_from_data(template["skeleton"]),
                "support": list(template["support"]),
            }
            for template in templates_data
        ]
        # Old files have no counter; a stale counter must not resurrect an ID.
        self.next_template_number = max(
            saved_next_template, _next_free_template_number(self.templates)
        )
        self.patterns = [
            _pattern_from_data(pattern) for pattern in patterns_data
        ]
        self.next_pattern_number = max(
            saved_next_pattern, _next_free_pattern_number(self.patterns)
        )

    def save(self, path):
        stored = [
            {
                "id": template["id"],
                "skeleton": program_to_data(template["skeleton"]),
                "support": template["support"],
            }
            for template in self.templates
        ]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "next_template": self.next_template_number,
                    "next_pattern": self.next_pattern_number,
                    "templates": stored,
                    "patterns": [
                        _pattern_to_data(pattern)
                        for pattern in self.patterns
                    ],
                },
                handle,
                ensure_ascii=False,
                # Compact separators keep the counter from shifting demo.py's
                # net-size delta.
                separators=(",", ":"),
            )

    def get(self, template_id):
        for template in self.templates:
            if template["id"] == template_id:
                return template
        raise KeyError(template_id)


def maybe_promote(case_base, library):
    cases = case_base.all()
    if len(cases) < MIN_SUPPORT_CASES:
        return []

    newest = cases[-1]
    newest_program = materialize(newest, library)
    events = []

    for template in list(library.templates):
        skeleton = anti_unify(template["skeleton"], newest_program)
        if skeleton is None or not slots_of(skeleton):
            continue
        events.extend(_promote(skeleton, cases, library, template))

    for earlier in cases[:-1]:
        # A referenced case is already represented by a template; re-promoting
        # it would only duplicate that template.
        if "template_id" in earlier:
            continue
        earlier_program = materialize(earlier, library)
        skeleton = anti_unify(newest_program, earlier_program)
        if skeleton is None or not slots_of(skeleton):
            continue
        events.extend(_promote(skeleton, cases, library, None))
    return events


def _next_free_template_number(templates):
    highest = 0
    for template in templates:
        template_id = template["id"]
        if template_id.startswith("T") and template_id[1:].isdigit():
            highest = max(highest, int(template_id[1:]))
    return highest + 1


def _next_template_id(library):
    template_id = f"T{library.next_template_number}"
    library.next_template_number += 1
    return template_id


def _find_template(library, template_id):
    for template in library.templates:
        if template["id"] == template_id:
            return template
    return None


def _next_free_pattern_number(patterns):
    highest = 0
    for pattern in patterns:
        pattern_id = pattern["pattern_id"]
        if pattern_id.startswith("P") and pattern_id[1:].isdigit():
            highest = max(highest, int(pattern_id[1:]))
    return highest + 1


def _next_pattern_id(library):
    pattern_id = f"P{library.next_pattern_number}"
    library.next_pattern_number += 1
    return pattern_id


def _pattern_from_data(data):
    pattern = {
        "pattern_id": data["pattern_id"],
        "kind": data["kind"],
    }
    for field in PATTERN_KEY_FIELDS[data["kind"]]:
        pattern[field] = data[field]
    pattern["support"] = list(data["support"])
    return pattern


def _pattern_to_data(pattern):
    data = {
        "pattern_id": pattern["pattern_id"],
        "kind": pattern["kind"],
    }
    for field in PATTERN_KEY_FIELDS[pattern["kind"]]:
        data[field] = pattern[field]
    data["support"] = pattern["support"]
    return data


def _pattern_key(pattern):
    return (pattern["kind"],) + tuple(
        pattern[field] for field in PATTERN_KEY_FIELDS[pattern["kind"]]
    )


def _pattern_key_for_edit(edit):
    kind = edit["kind"]
    if kind == "value":
        return ("value", edit["role"])
    if kind == "swap":
        return ("swap", edit["from_op"][0], edit["to_op"][0])
    if kind in ("insert", "remove"):
        return (kind, edit["op"][0])
    raise ValueError(f"unknown edit kind: {kind!r}")


def maybe_promote_patterns(case_base, library):
    # Mining adaptation rules from a case base (Hanney & Keane 1996, "Learning
    # Adaptation Rules from a Case-Base", EWCBR-96, LNCS 1168, pp. 179-192):
    # adaptation knowledge is itself reusable case knowledge, so recurring
    # winning edits become patterns, mirroring how recurring solution
    # skeletons become templates. This is the adaptation-rule-learning line of
    # CBR; adaptation-guided retrieval (Smyth & Keane 1998) is the separate
    # ranking-by-adaptability principle used at the revise gate.
    support_by_key = {}
    for case in case_base.all():
        history = case.get("history", {})
        for edit in history.get("edits", []):
            key = _pattern_key_for_edit(edit)
            support = support_by_key.setdefault(key, [])
            if case["task_id"] not in support:
                support.append(case["task_id"])

    patterns_by_key = {
        _pattern_key(pattern): pattern for pattern in library.patterns
    }
    events = []
    for key, support in support_by_key.items():
        pattern = patterns_by_key.get(key)
        if pattern is None:
            if len(support) < MIN_SUPPORT_CASES:
                continue
            pattern = {
                "pattern_id": _next_pattern_id(library),
                "kind": key[0],
            }
            for field, value in zip(PATTERN_KEY_FIELDS[key[0]], key[1:]):
                pattern[field] = value
            pattern["support"] = list(support)
            library.patterns.append(pattern)
            patterns_by_key[key] = pattern
            events.append(_pattern_event("promoted", pattern))
        elif pattern["support"] != support:
            pattern["support"] = list(support)
            events.append(_pattern_event("updated", pattern))

    # Existing patterns survive a support drop (no dissolution this round), but
    # their support is live evidence, so a vanished key must clear it.
    for pattern in library.patterns:
        if _pattern_key(pattern) in support_by_key:
            continue
        if pattern["support"]:
            pattern["support"] = []
            events.append(_pattern_event("updated", pattern))
    return events


def _pattern_event(event, pattern):
    text = f"{event} {pattern['pattern_id']} support={len(pattern['support'])}"
    if pattern["support"]:
        text += ": " + ", ".join(pattern["support"])
    return text


def _promote(skeleton, cases, library, existing):
    # An earlier update in this pass may have dissolved the template.
    if existing is not None and all(
        entry is not existing for entry in library.templates
    ):
        return []

    covered = []
    for case in cases:
        program = materialize(case, library)
        bindings = _match_program(skeleton, program)
        if bindings is None:
            continue
        covered.append((case, program, bindings))
    if len(covered) < MIN_SUPPORT_CASES:
        return []

    for case, program, bindings in covered:
        reproduced = instantiate(skeleton, bindings)
        if program_to_data(reproduced) != program_to_data(program):
            return []

    if existing is None:
        template = {
            "id": _next_template_id(library),
            "skeleton": skeleton,
            "support": [],
        }
        library.templates.append(template)
        event = "promoted"
    else:
        template = existing
        template["skeleton"] = skeleton
        event = "updated"

    covered_by_task = {case["task_id"]: case for case, _, _ in covered}
    previous_templates = {}
    for case in covered_by_task.values():
        previous_id = case.get("template_id")
        if previous_id is None or previous_id == template["id"]:
            continue
        old = _find_template(library, previous_id)
        if old is not None:
            previous_templates[previous_id] = old

    for old in previous_templates.values():
        old["support"] = [
            task_id for task_id in old["support"] if task_id not in covered_by_task
        ]

    template["support"] = list(covered_by_task)
    for case, _, bindings in covered:
        case["template_id"] = template["id"]
        case["bindings"] = dict(bindings)
        case.pop("program", None)

    events = [
        f"{event} {template['id']} support={len(template['support'])}: "
        + ", ".join(template["support"])
    ]
    for old in previous_templates.values():
        if len(old["support"]) < MIN_SUPPORT_CASES:
            events.extend(_dissolve(old, cases, library))
    return events


def _dissolve(template, cases, library):
    cases_by_task = {case["task_id"]: case for case in cases}
    for task_id in template["support"]:
        case = cases_by_task.get(task_id)
        if case is None or case.get("template_id") != template["id"]:
            continue
        case["program"] = instantiate(template["skeleton"], case["bindings"])
        case.pop("template_id", None)
        case.pop("bindings", None)
    library.templates = [
        entry for entry in library.templates if entry is not template
    ]
    return [f"dissolved {template['id']}"]


def _match_program(template, program):
    extractors_t = template["extractors"]
    extractors_p = program["extractors"]
    if len(extractors_t) != len(extractors_p):
        return None

    bindings = {}
    for chain_t, chain_p in zip(extractors_t, extractors_p):
        if len(chain_t) != len(chain_p):
            return None
        for op_t, op_p in zip(chain_t, chain_p):
            if len(op_t) != len(op_p) or op_t[0] != op_p[0]:
                return None
            for expected, actual in zip(op_t[1:], op_p[1:]):
                if not _match_value(expected, actual, bindings):
                    return None
    if not _match_value(template["joiner"], program["joiner"], bindings):
        return None
    return bindings


def _match_value(expected, actual, bindings):
    name = slot_name(expected)
    if name is None:
        return expected == actual
    if name in bindings:
        return bindings[name] == actual
    bindings[name] = actual
    return True
