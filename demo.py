import json
import os
import tempfile

from cases import CaseBase
from dsl import program_repr
from library import Library, materialize, maybe_promote
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
    (
        "name-swap-semicolon",
        [
            ["Tanaka; Taro", "Taro Tanaka"],
            ["Suzuki; Hanako", "Hanako Suzuki"],
        ],
    ),
    (
        "name-swap-pipe",
        [
            ["Kim | Jiwoo", "Jiwoo Kim"],
            ["Lee | Minjun", "Minjun Lee"],
        ],
    ),
    (
        "date-separator-dot",
        [
            ["2026-11-10", "2026.11.10"],
            ["2025-01-05", "2025.01.05"],
        ],
    ),
    (
        "date-separator-underscore",
        [
            ["2026-11-10", "2026_11_10"],
            ["2025-01-05", "2025_01_05"],
        ],
    ),
    (
        "code-upper",
        [
            ["ab-cd", "AB-CD"],
            ["wx-yz", "WX-YZ"],
        ],
    ),
]


def _repair_text(edit):
    if edit["kind"] == "value":
        return f"{edit['role']} {edit['from']!r} -> {edit['to']!r}"
    site = edit["site"]
    if edit["kind"] == "swap":
        from_op = json.dumps(edit["from_op"], ensure_ascii=False)
        to_op = json.dumps(edit["to_op"], ensure_ascii=False)
        return f"swap {site} {from_op} -> {to_op}"
    op = json.dumps(edit["op"], ensure_ascii=False)
    return f"{edit['kind']} {site} {op}"


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        case_path = os.path.join(temp_dir, "cases.json")
        library_path = os.path.join(temp_dir, "library.json")
        case_base = CaseBase()
        case_base.load(case_path)
        library = Library()
        library.load(library_path)

        for task_id, examples in TASKS:
            print(f"task: {task_id}")
            program, report, candidates_tested = solve(
                examples, case_base, library
            )
            if program is None:
                print("solved: no")
                print("path: none")
                print(f"reason: {report['reason']}")
                print(f"candidates_tested: {candidates_tested}")
                print()
                continue

            print("solved: yes")
            print(f"path: {report['path']}")
            if report["path"] == "revise":
                for edit in report["edits"]:
                    print(
                        f"repair: {report['source_case']} {_repair_text(edit)}"
                    )
            print(f"program: {program_repr(program)}")
            print(f"candidates_tested: {candidates_tested}")
            history = {
                key: value for key, value in report.items() if key != "reason"
            }
            case_base.add(
                {
                    "task_id": task_id,
                    "examples": examples,
                    "program": program,
                    "history": history,
                }
            )
            events = maybe_promote(case_base, library)
            case_base.save(case_path)
            library.save(library_path)
            for event in events:
                print(f"promotion: {event}")
            print()

        print("library summary:")
        print(f"templates: {len(library.templates)}")
        for template in library.templates:
            print(f"  {template['id']}: support={len(template['support'])}")
        cases = case_base.all()
        references = sum(1 for case in cases if "template_id" in case)
        print(f"references: {references}/{len(cases)} cases stored as references")
        path_counts = {}
        for case in cases:
            path = case["history"]["path"]
            path_counts[path] = path_counts.get(path, 0) + 1
        print(
            "paths: "
            + " ".join(f"{path}={count}" for path, count in path_counts.items())
        )

        baseline = CaseBase()
        for case in cases:
            baseline_case = {
                "task_id": case["task_id"],
                "examples": case["examples"],
                "program": materialize(case, library),
            }
            if "history" in case:
                baseline_case["history"] = case["history"]
            baseline.add(baseline_case)
        baseline_path = os.path.join(temp_dir, "baseline-cases.json")
        baseline.save(baseline_path)
        current_size = os.path.getsize(case_path) + os.path.getsize(library_path)
        baseline_size = os.path.getsize(baseline_path)
        net_delta = current_size - baseline_size
        print(
            f"net size delta: {net_delta:+d} B "
            "((cases.json + library.json) - all-concrete cases-only baseline)"
        )


if __name__ == "__main__":
    main()
