#!/usr/bin/env python3
"""Parse a local TSV/CSV case table into neutral JSON.

Does not call any external system. Agents should pass --summary.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

REQUIRED = "测试项"
STEP_SPLIT = re.compile(r"；\s*(?=\d+\.\s*)")
STEP_PREFIX = re.compile(r"^\d+\.\s*")


def detect_delimiter(path: Path, explicit: str | None) -> str:
    if explicit:
        return "\t" if explicit == "tab" else ","
    if path.suffix.lower() == ".tsv":
        return "\t"
    if path.suffix.lower() == ".csv":
        return ","
    sample = path.read_text(encoding="utf-8")[:2048]
    return "\t" if sample.count("\t") >= sample.count(",") else ","


def split_steps(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    parts = STEP_SPLIT.split(raw)
    steps = []
    for part in parts:
        step = STEP_PREFIX.sub("", part).strip()
        if step:
            steps.append(step)
    return steps or [raw]


def directory_parts(title: str) -> list[str]:
    parts = [part for part in title.split("_") if part]
    if len(parts) >= 2:
        return parts[:2]
    return []


def parse_rows(path: Path, delimiter: str) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames:
            raise SystemExit("表头为空")
        headers = {(name or "").strip(): name for name in reader.fieldnames}
        if REQUIRED not in headers:
            raise SystemExit(f"缺少列「{REQUIRED}」，实际表头：{list(headers)}")
        rows = []
        for index, raw in enumerate(reader, start=2):
            row = {key: (raw.get(headers[key]) or "").strip() for key in headers}
            title = row.get(REQUIRED, "").strip()
            if not title:
                continue
            steps = split_steps(row.get("步骤描述", ""))
            expected = row.get("预期结果", "").strip()
            if not steps:
                steps = [row.get("步骤描述", "").strip() or title]
            content = []
            for step_index, step in enumerate(steps):
                content.append(
                    {
                        "step": step,
                        "expected": expected if step_index == len(steps) - 1 else None,
                    }
                )
            directory = directory_parts(title)
            rows.append(
                {
                    "title": title,
                    "precondition": row.get("前置条件", ""),
                    "priority": row.get("优先级", ""),
                    "owner": row.get("负责人", ""),
                    "directory": directory,
                    "steps": content,
                    "sourceRow": index,
                }
            )
        return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TSV/CSV 用例表 → JSON")
    parser.add_argument("input", type=Path, help="用例表路径（.tsv / .csv）")
    parser.add_argument("-o", "--output", type=Path, help="写出 JSON；默认 stdout")
    parser.add_argument(
        "--delimiter",
        choices=("tab", "comma"),
        help="强制分隔符；默认按扩展名，否则看内容",
    )
    parser.add_argument(
        "--skip-subjects",
        type=Path,
        help="已存在标题，每行一个；匹配到的用例从输出里去掉",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="只输出条数和分组，不含 cases 正文",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        raise SystemExit(f"找不到文件：{args.input}")

    delimiter = detect_delimiter(args.input, args.delimiter)
    cases = parse_rows(args.input, delimiter)

    skip: set[str] = set()
    if args.skip_subjects:
        skip = {
            line.strip()
            for line in args.skip_subjects.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    kept = [case for case in cases if case["title"] not in skip]
    skipped = [case["title"] for case in cases if case["title"] in skip]

    groups: dict[str, int] = {}
    for case in kept:
        key = "_".join(case["directory"]) or "(未分组)"
        groups[key] = groups.get(key, 0) + 1
    payload = {
        "source": str(args.input),
        "delimiter": "tab" if delimiter == "\t" else "comma",
        "total": len(cases),
        "kept": len(kept),
        "skippedCount": len(skipped),
        "groups": groups,
    }
    if args.summary:
        payload["skippedSubjects"] = skipped[:20]
    else:
        payload["skippedSubjects"] = skipped
        payload["cases"] = kept
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    else:
        sys.stdout.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
