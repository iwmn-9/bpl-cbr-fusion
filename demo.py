import os
import tempfile

from cases import CaseBase
from dsl import program_repr
from solver import solve

TASKS = [
    (
        "name-swap",
        [
            ["Tanaka, Taro", "Taro Tanaka"],
            ["Suzuki, Hanako", "Hanako Suzuki"],
        ],
    ),
    (
        "date-separator",
        [
            ["2026-11-10", "2026/11/10"],
            ["2025-01-05", "2025/01/05"],
        ],
    ),
    (
        "name-swap-new",
        [
            ["Kim, Jiwoo", "Jiwoo Kim"],
            ["Lee, Minjun", "Minjun Lee"],
        ],
    ),
]


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        case_path = os.path.join(temp_dir, "cases.json")
        case_base = CaseBase()
        case_base.load(case_path)

        for task_id, examples in TASKS:
            print(f"task: {task_id}")
            program, result = solve(examples, case_base)
            if program is None:
                print("solved: no")
                print("path: none")
                print(f"reason: {result}")
            else:
                print("solved: yes")
                print(f"path: {result}")
                print(f"program: {program_repr(program)}")
                case_base.add(
                    {"task_id": task_id, "examples": examples, "program": program}
                )
                case_base.save(case_path)
            print()


if __name__ == "__main__":
    main()
