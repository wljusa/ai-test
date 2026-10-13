#!/usr/bin/env python3
"""校验测试点 TSV。失败则退出码 1。

用法:
  python3 skills/test-point/scripts/check_points.py path/to/points.tsv
  python3 skills/test-point/scripts/check_points.py path/to/points.tsv --summary
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

COLUMNS = ("编号", "模块", "测试点", "场景类型", "优先级", "来源")
SCENES = ("主路径", "异常", "边界", "权限", "空数据", "回放")
PRIORITIES = ("P0", "P1", "P2")
ID_RE = re.compile(r"^TP[1-9][0-9]*$")
ACTION_ONLY = re.compile(r"^(打开|点击|访问|查看).{0,12}$")
RESULT_MARKS = ("提示", "不可", "失败", "成功", "错误", "可见", "显示", "不能", "无法")


def is_bare_action(text: str) -> bool:
    if any(mark in text for mark in RESULT_MARKS):
        return False
    return ACTION_ONLY.fullmatch(text) is not None


def load_points(path: Path) -> list[dict]:
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


def check(rows: list[dict]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["没有数据行"]
    seen: dict[str, int] = {}
    for row in rows:
        line = row["sourceRow"]
        point_id = row["编号"]
        if not ID_RE.fullmatch(point_id):
            errors.append(f"第{line}行: 编号「{point_id or '空'}」须为 TP1、TP2 这种格式")
        elif point_id in seen:
            errors.append(f"第{line}行: 编号「{point_id}」与第{seen[point_id]}行重复")
        else:
            seen[point_id] = line
        for column in ("模块", "测试点", "来源"):
            if not row[column]:
                errors.append(f"第{line}行: 列「{column}」为空")
        if row["测试点"] and is_bare_action(row["测试点"]):
            errors.append(f"第{line}行: 列「测试点」只写了动作「{row['测试点']}」，要写可观察结果")
        if row["场景类型"] not in SCENES:
            errors.append(
                f"第{line}行: 列「场景类型」取值「{row['场景类型'] or '空'}」不在允许范围：{'、'.join(SCENES)}"
            )
        if row["优先级"] not in PRIORITIES:
            errors.append(
                f"第{line}行: 列「优先级」取值「{row['优先级'] or '空'}」不在允许范围：{'、'.join(PRIORITIES)}"
            )
    return errors


def summarize(path: Path, rows: list[dict]) -> dict:
    scenes: dict[str, int] = {}
    for row in rows:
        scenes[row["场景类型"]] = scenes.get(row["场景类型"], 0) + 1
    return {"source": str(path), "total": len(rows), "scenes": scenes}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验测试点 TSV")
    parser.add_argument("points", type=Path, help="测试点 TSV 路径")
    parser.add_argument("--summary", action="store_true", help="通过时只输出条数和场景分布")
    args = parser.parse_args(argv)

    if not args.points.is_file():
        print(f"找不到文件：{args.points}", file=sys.stderr)
        return 1
    try:
        rows = load_points(args.points)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    errors = check(rows)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.summary:
        print(json.dumps(summarize(args.points, rows), ensure_ascii=False, indent=2))
    else:
        print("校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
