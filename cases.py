import json

from dsl import program_from_data, program_to_data


class CaseBase:
    def __init__(self):
        self._cases = []

    def load(self, path):
        try:
            with open(path, encoding="utf-8") as handle:
                stored = json.load(handle)
        except FileNotFoundError:
            self._cases = []
            return
        self._cases = [_case_from_data(case) for case in stored]

    def save(self, path):
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                [_case_to_data(case) for case in self._cases],
                handle,
                ensure_ascii=False,
            )

    def add(self, case):
        self._cases.append(case)

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
    return stored
