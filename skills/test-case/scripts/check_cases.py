#!/usr/bin/env python3
"""校验用例 TSV，并对照测试点编号。失败则退出码 1。

用法:
  python3 skills/test-case/scripts/check_cases.py cases.tsv --points points.tsv
  python3 skills/test-case/scripts/check_cases.py cases.tsv --points points.tsv --summary
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

POINT_SCRIPTS = Path(__file__).resolve().parents[2] / "test-point" / "scripts"
CASE_TABLE = Path(__file__).resolve().parents[2] / "case-table" / "scripts"
sys.path.insert(0, str(POINT_SCRIPTS))
sys.path.insert(0, str(CASE_TABLE))

from check_points import PRIORITIES, SCENES, check as check_points, load_points
from parse_cases import directory_parts, split_steps

COLUMNS = ("测试项", "前置条件", "步骤描述", "预期结果", "优先级", "负责人", "测试点编号")
STEP_SPLIT = re.compile(r"；\s*(?=\d+\.\s*)")
STEP_ITEM = re.compile(r"^\d+\.\s*\S")


def load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise SystemExit("表头为空")
        headers = {(name or "").strip(): name for name in reader.fieldnames}
        missing = [name for name in COLUMNS if name not in headers]
        if missing:
            raise SystemExit(f"缺少列「{'、'.join(missing)}」，实际表头：{list(headers)}")
        rows = []
        for index, raw in enumerate(reader, start=2):
            row = {key: (raw.get(headers[key]) or "").strip() for key in COLUMNS}
            if not any(row.values()):
                continue
            row["sourceRow"] = index
            rows.append(row)
    return rows


def steps_are_numbered(text: str) -> bool:
    raw = text.strip()
    if not raw:
        return False
    parts = [part.strip() for part in STEP_SPLIT.split(raw)]
    return bool(parts) and all(STEP_ITEM.match(part) for part in parts)


def check(cases: list[dict], points: list[dict]) -> list[str]:
    errors = [f"测试点: {item}" for item in check_points(points)]
    if not cases:
        errors.append("没有数据行")
    by_id = {row["编号"]: row for row in points if row.get("编号")}
    covered: set[str] = set()
    for row in cases:
        line = row["sourceRow"]
        title = row["测试项"]
        parts = [part for part in title.split("_") if part]
        if len(parts) < 3 or len(directory_parts(title)) < 2:
            errors.append(f"第{line}行: 测试项须为「模块_场景类型_结果」")
        elif parts[1] not in SCENES:
            errors.append(f"第{line}行: 测试项中的场景类型「{parts[1]}」不在允许范围：{'、'.join(SCENES)}")
        for column in ("前置条件", "步骤描述", "预期结果", "测试点编号"):
            if not row[column]:
                errors.append(f"第{line}行: 列「{column}」为空")
        if row["步骤描述"] and not steps_are_numbered(row["步骤描述"]):
            errors.append(f"第{line}行: 步骤描述须为「1. …；2. …」")
        elif row["步骤描述"] and not split_steps(row["步骤描述"]):
            errors.append(f"第{line}行: 步骤描述没有可执行步骤")
        if row["优先级"] not in PRIORITIES:
            errors.append(
                f"第{line}行: 列「优先级」取值「{row['优先级'] or '空'}」不在允许范围：{'、'.join(PRIORITIES)}"
            )
        point_id = row["测试点编号"]
        point = by_id.get(point_id)
        if point_id and point is None:
            errors.append(f"第{line}行: 测试点编号「{point_id}」不在测试点文件中")
        elif point is not None and len(parts) >= 2:
            covered.add(point_id)
            if parts[0] != point["模块"] or (len(parts) > 1 and parts[1] != point["场景类型"]):
                errors.append(
                    f"第{line}行: 测试项与测试点「{point_id}」不一致（应为 {point['模块']}_{point['场景类型']}_结果）"
                )
    for point in points:
        point_id = point.get("编号", "")
        if point_id and point_id not in covered:
            errors.append(f"测试点「{point_id}」没有对应用例")
    return errors


def summarize(cases_path: Path, points_path: Path, cases: list[dict], points: list[dict]) -> dict:
    groups: dict[str, int] = {}
    for row in cases:
        key = "_".join(directory_parts(row["测试项"])) or "(未分组)"
        groups[key] = groups.get(key, 0) + 1
    point_ids = {row["编号"] for row in points if row.get("编号")}
    covered = {row["测试点编号"] for row in cases if row["测试点编号"] in point_ids}
    return {
        "source": str(cases_path),
        "points": str(points_path),
        "total": len(cases),
        "covered": len(covered),
        "groups": groups,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验用例 TSV，并对照测试点")
    parser.add_argument("cases", type=Path, help="用例 TSV 路径")
    parser.add_argument("--points", type=Path, required=True, help="测试点 TSV 路径")
    parser.add_argument("--summary", action="store_true", help="通过时只输出条数、覆盖数和分组")
    args = parser.parse_args(argv)

    for label, path in (("用例", args.cases), ("测试点", args.points)):
        if not path.is_file():
            print(f"找不到{label}文件：{path}", file=sys.stderr)
            return 1
    try:
        cases = load_cases(args.cases)
        points = load_points(args.points)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    errors = check(cases, points)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.summary:
        print(json.dumps(summarize(args.cases, args.points, cases, points), ensure_ascii=False, indent=2))
    else:
        print("校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
