import json

from dsl import program_from_data, program_to_data


class CaseBase:
    def __init__(self):
        self._cases = []
        self.removed = []

    def load(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                stored = json.load(handle)
        except FileNotFoundError:
            self._cases = []
            self.removed = []
            return
        if isinstance(stored, dict):
            cases_data = stored["cases"]
            self.removed = list(stored.get("removed", []))
        else:
            # Old format: a bare case list, with no tombstones.
            cases_data = stored
            self.removed = []
        self._cases = [_case_from_data(case) for case in cases_data]

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "removed": self.removed,
                    "cases": [_case_to_data(case) for case in self._cases],
                },
                handle,
                ensure_ascii=False,
            )

    def add(self, case):
        self._cases.append(case)

    def remove(self, case):
        for index, stored in enumerate(self._cases):
            if stored is case:
                del self._cases[index]
                return
        raise ValueError(f"case not in base: {case['task_id']!r}")

    def all(self):
        return list(self._cases)


def _case_from_data(case):
    loaded = {
        "task_id": case["task_id"],
        "examples": [list(pair) for pair in case["examples"]],
    }
    if "template_id" in case:
        loaded["template_id"] = case["template_id"]
        loaded["bindings"] = dict(case["bindings"])
    if "program" in case:
        loaded["program"] = program_from_data(case["program"])
    if "history" in case:
        loaded["history"] = case["history"]
    if "stats" in case:
        loaded["stats"] = case["stats"]
    if "admission" in case:
        loaded["admission"] = case["admission"]
    return loaded


def _case_to_data(case):
    stored = {
        "task_id": case["task_id"],
        "examples": case["examples"],
    }
    if "template_id" in case:
        stored["template_id"] = case["template_id"]
        stored["bindings"] = case["bindings"]
    if "program" in case:
        stored["program"] = program_to_data(case["program"])
    if "history" in case:
        stored["history"] = case["history"]
    if "stats" in case:
        stored["stats"] = case["stats"]
    if "admission" in case:
        stored["admission"] = case["admission"]
    return stored
