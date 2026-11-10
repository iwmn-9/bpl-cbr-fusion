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
        self._cases = [
            {
                "task_id": case["task_id"],
                "examples": [list(pair) for pair in case["examples"]],
                "program": program_from_data(case["program"]),
            }
            for case in stored
        ]

    def save(self, path):
        stored = [
            {
                "task_id": case["task_id"],
                "examples": case["examples"],
                "program": program_to_data(case["program"]),
            }
            for case in self._cases
        ]
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(stored, handle, ensure_ascii=False)

    def add(self, case):
        self._cases.append(case)

    def all(self):
        return list(self._cases)
