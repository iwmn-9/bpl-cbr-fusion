import json
import os
import tempfile

from cases import CaseBase
from dsl import program_repr
from library import (
    Library,
    materialize,
    maybe_promote,
    maybe_promote_patterns,
)
from solver import classify_admission, maintain, solve

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


def _new_stats():
    # NOVEL: zero initializers for the usage counters; structural, not tuned.
    return {
        "reuse_tested": 0,
        "reuse_wins": 0,
        "revise_attempts": 0,
        "revise_wins": 0,
    }


def _update_usage_stats(case_base, attempts):
    cases = {case["task_id"]: case for case in case_base.all()}
    for attempt in attempts:
        case = cases.get(attempt.get("source"))
        if case is None:
            continue
        stats = case.setdefault("stats", _new_stats())
        if attempt["stage"] == "reuse":
            stats["reuse_tested"] += 1
            if attempt["outcome"] == "win":
                stats["reuse_wins"] += 1
        elif attempt["stage"] == "revise":
            stats["revise_attempts"] += 1
            if attempt["outcome"] == "win":
                stats["revise_wins"] += 1


def _stats_text(case):
    stats = case["stats"]
    return (
        f"{case['task_id']}(rt={stats['reuse_tested']}, "
        f"rw={stats['reuse_wins']}, ra={stats['revise_attempts']}, "
        f"rw2={stats['revise_wins']})"
    )


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


def _pattern_label(pattern):
    if pattern["kind"] == "value":
        return f"value/{pattern['role']}"
    if pattern["kind"] == "swap":
        return f"swap/{pattern['from_op']}->{pattern['to_op']}"
    return f"{pattern['kind']}/{pattern['op']}"


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
            _update_usage_stats(case_base, report["attempts"])
            if program is None:
                print("solved: no")
                print("path: none")
                print(f"reason: {report['reason']}")
                print(f"candidates_tested: {candidates_tested}")
                print()
                continue

            admission = classify_admission(examples, case_base, library)
            print("solved: yes")
            print(f"path: {report['path']}")
            if report["path"] == "revise":
                for edit in report["edits"]:
                    print(
                        f"repair: {report['source_case']} {_repair_text(edit)}"
                    )
            print(f"program: {program_repr(program)}")
            print(f"candidates_tested: {candidates_tested}")
            print(f"admission: {admission}")
            history = {
                key: value for key, value in report.items() if key != "reason"
            }
            case_base.add(
                {
                    "task_id": task_id,
                    "examples": examples,
                    "program": program,
                    "history": history,
                    "stats": _new_stats(),
                    "admission": admission,
                }
            )
            events = maybe_promote(case_base, library)
            pattern_events = maybe_promote_patterns(case_base, library)
            case_base.save(case_path)
            library.save(library_path)
            for event in events:
                print(f"promotion: {event}")
            for event in pattern_events:
                print(f"pattern: {event}")
            print()

        decisions = maintain(case_base, library)
        case_base.save(case_path)
        library.save(library_path)
        for decision in decisions:
            print(decision)
        print(f"removed records: {len(case_base.removed)}")
        solved_count = 0
        for _, examples in TASKS:
            program, _, _ = solve(examples, case_base, library)
            if program is not None:
                solved_count += 1
        print(f"competence check: {solved_count}/{len(TASKS)}")
        print()

        print("library summary:")
        print(f"templates: {len(library.templates)}")
        for template in library.templates:
            print(f"  {template['id']}: support={len(template['support'])}")
        print(f"patterns: {len(library.patterns)}")
        for pattern in library.patterns:
            print(
                f"  {pattern['pattern_id']} "
                f"({_pattern_label(pattern)}) "
                f"support={len(pattern['support'])}"
            )
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
        print("stats: " + " ".join(_stats_text(case) for case in cases))

        baseline = CaseBase()
        # The baseline carries history/stats/admission verbatim so the delta
        # measures representation only.
        for case in cases:
            baseline_case = {
                "task_id": case["task_id"],
                "examples": case["examples"],
                "program": materialize(case, library),
            }
            if "history" in case:
                baseline_case["history"] = case["history"]
            if "stats" in case:
                baseline_case["stats"] = case["stats"]
            if "admission" in case:
                baseline_case["admission"] = case["admission"]
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
