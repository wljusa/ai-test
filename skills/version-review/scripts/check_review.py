#!/usr/bin/env python3
"""校验版本代码审核稿。失败则退出码 1。

用法:
  python3 skills/version-review/scripts/check_review.py path/to/review.md --diff path/to/change.diff
  python3 skills/version-review/scripts/check_review.py path/to/review.md --diff path/to/change.diff --summary
  python3 skills/version-review/scripts/check_review.py path/to/review.md --diff path/to/change.diff --export-points points.tsv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from summarize_diff import parse_diff

REQUIRED_SECTIONS = ("概述", "测试点", "结论")
OPTIONAL_SECTIONS = ("缺陷", "引起的问题")
KNOWN_SECTIONS = REQUIRED_SECTIONS + OPTIONAL_SECTIONS
OVERVIEW_KEYS = ("版本", "需求", "问题", "diff")
FINDING_HEADERS = ("编号", "位置", "描述", "严重级别", "依据")
POINT_HEADERS = ("编号", "模块", "测试点", "场景类型", "优先级", "来源")
SEVERITIES = ("致命", "严重", "一般")
SCENES = ("主路径", "异常", "边界", "权限", "空数据", "回放")
PRIORITIES = ("P0", "P1", "P2")
COUNT_NAMES = ("缺陷", "引起的问题", "测试点")
ID_PREFIX = {"缺陷": "DF", "引起的问题": "IP", "测试点": "TP"}

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$")
FIELD_RE = re.compile(r"^(版本|需求|问题|diff)\s*[:：]\s*(.*?)\s*$", re.M)
LOCATION_RE = re.compile(r"^(.+):([1-9]\d*)$")
ID_RE = {name: re.compile(rf"^{prefix}[1-9]\d*$") for name, prefix in ID_PREFIX.items()}
COUNT_RE = {
    name: re.compile(rf"^[-*]\s*{re.escape(name)}\s*[:：]\s*(\d+)\s*$", re.M)
    for name in COUNT_NAMES
}
REF_RE = re.compile(r"(?:DF|IP)[1-9]\d*")
SOURCE_MARK = re.compile(r"需求|问题|ISS[1-9]\d*")
SEPARATOR_CELL = re.compile(r":?-{3,}:?")
ACTION_ONLY = re.compile(r"^(打开|点击|访问|查看).{0,12}$")
RESULT_MARKS = ("提示", "不可", "失败", "成功", "错误", "可见", "显示", "不能", "无法")


def is_bare_action(text: str) -> bool:
    if any(mark in text for mark in RESULT_MARKS):
        return False
    return ACTION_ONLY.fullmatch(text) is not None


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(SEPARATOR_CELL.fullmatch(cell.replace(" ", "")) for cell in cells)


def split_sections(text: str) -> tuple[list[str], dict[str, tuple[list[str], int]]]:
    """返回错误，以及 章节名 -> (正文行, 正文首行行号)。行号从 1 计。"""
    errors: list[str] = []
    found: dict[str, tuple[list[str], int]] = {}
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = SECTION_RE.match(line)
        if match:
            headings.append((index, match.group(1).strip()))
    for index, (start, name) in enumerate(headings):
        end = headings[index + 1][0] if index + 1 < len(headings) else len(lines)
        if name not in KNOWN_SECTIONS:
            errors.append(f"{name}: 未知章节")
            continue
        if name in found:
            errors.append(f"{name}: 章节重复")
            continue
        found[name] = (lines[start + 1:end], start + 2)
    return errors, found


def parse_table(body: list[str], start_line: int) -> tuple[list[str], list[tuple[int, list[str]]]] | None:
    rows = [(start_line + offset, line.strip()) for offset, line in enumerate(body) if line.strip().startswith("|")]
    if len(rows) < 2 or not is_separator(rows[1][1]):
        return None
    header = split_row(rows[0][1])
    data = []
    for line_no, line in rows[2:]:
        cells = split_row(line)
        if any(cells):
            data.append((line_no, cells))
    return header, data


def cell(header: list[str], row: list[str], name: str) -> str:
    if name not in header:
        return ""
    index = header.index(name)
    return row[index] if index < len(row) else ""


def check_overview(body: list[str]) -> list[str]:
    text = "\n".join(body)
    if not text.strip():
        return ["概述: 章节为空"]
    errors: list[str] = []
    values: dict[str, str] = {}
    for match in FIELD_RE.finditer(text):
        key, value = match.group(1), match.group(2).strip()
        if key in values:
            errors.append(f"概述: {key}重复")
            continue
        values[key] = value
    for key in OVERVIEW_KEYS:
        if key not in values:
            errors.append(f"概述: 缺少{key}")
            continue
        value = values[key]
        if not value or value.startswith("<"):
            errors.append(f"概述: {key}为空")
        elif key != "问题" and value == "无":
            errors.append(f"概述: {key}不能为无")
    return errors


def check_finding_rows(
    section: str,
    header: list[str],
    rows: list[tuple[int, list[str]]],
    paths: set[str] | None,
) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    ids: set[str] = set()
    id_re = ID_RE[section]
    prefix = ID_PREFIX[section]
    for line_no, row in rows:
        finding_id = cell(header, row, "编号")
        if not id_re.fullmatch(finding_id):
            errors.append(f"{section}: 第{line_no}行: 列「编号」取值「{finding_id or '空'}」须为 {prefix}1、{prefix}2 这种格式")
        elif finding_id in seen:
            errors.append(f"{section}: 第{line_no}行: 编号「{finding_id}」与第{seen[finding_id]}行重复")
        else:
            seen[finding_id] = line_no
            ids.add(finding_id)
        for column in ("描述", "依据"):
            if not cell(header, row, column):
                errors.append(f"{section}: 第{line_no}行: 列「{column}」为空")
        severity = cell(header, row, "严重级别")
        if severity not in SEVERITIES:
            errors.append(
                f"{section}: 第{line_no}行: 列「严重级别」取值「{severity or '空'}」不在允许范围：{'、'.join(SEVERITIES)}"
            )
        location = cell(header, row, "位置")
        match = LOCATION_RE.fullmatch(location)
        if not match:
            errors.append(f"{section}: 第{line_no}行: 列「位置」取值「{location or '空'}」须为路径:行号")
        elif paths is not None and match.group(1) not in paths:
            errors.append(f"{section}: 第{line_no}行: 列「位置」中的路径「{match.group(1)}」不在 diff 中")
    return errors, ids


def check_point_rows(
    header: list[str],
    rows: list[tuple[int, list[str]]],
    finding_ids: set[str],
) -> tuple[list[str], list[dict]]:
    errors: list[str] = []
    seen: dict[str, int] = {}
    exported: list[dict] = []
    for line_no, row in rows:
        record = {column: cell(header, row, column) for column in POINT_HEADERS}
        record["sourceRow"] = line_no
        point_id = record["编号"]
        if not ID_RE["测试点"].fullmatch(point_id):
            errors.append(f"测试点: 第{line_no}行: 列「编号」取值「{point_id or '空'}」须为 TP1、TP2 这种格式")
        elif point_id in seen:
            errors.append(f"测试点: 第{line_no}行: 编号「{point_id}」与第{seen[point_id]}行重复")
        else:
            seen[point_id] = line_no
        for column in ("模块", "测试点", "来源"):
            if not record[column]:
                errors.append(f"测试点: 第{line_no}行: 列「{column}」为空")
        if record["测试点"] and is_bare_action(record["测试点"]):
            errors.append(f"测试点: 第{line_no}行: 列「测试点」只写了动作「{record['测试点']}」，要写可观察结果")
        if record["场景类型"] not in SCENES:
            errors.append(
                f"测试点: 第{line_no}行: 列「场景类型」取值「{record['场景类型'] or '空'}」不在允许范围：{'、'.join(SCENES)}"
            )
        if record["优先级"] not in PRIORITIES:
            errors.append(
                f"测试点: 第{line_no}行: 列「优先级」取值「{record['优先级'] or '空'}」不在允许范围：{'、'.join(PRIORITIES)}"
            )
        source = record["来源"]
        if source:
            refs = REF_RE.findall(source)
            unknown = [ref for ref in refs if ref not in finding_ids]
            if unknown:
                errors.append(
                    f"测试点: 第{line_no}行: 列「来源」引用了不存在的编号 {'、'.join(unknown)}"
                )
            elif not refs and not SOURCE_MARK.search(source):
                errors.append(f"测试点: 第{line_no}行: 列「来源」须指向需求、问题编号或本稿 DF/IP")
        exported.append({column: record[column] for column in POINT_HEADERS})
    return errors, exported


def check_table(
    section: str,
    body: list[str],
    start_line: int,
    expected: tuple[str, ...],
) -> tuple[list[str], list[str] | None, list[tuple[int, list[str]]]]:
    parsed = parse_table(body, start_line)
    if parsed is None:
        return [f"{section}: 缺少表格"], None, []
    header, rows = parsed
    if tuple(header) != expected:
        return [f"{section}: 表头须为 {'、'.join(expected)}"], None, []
    if not rows:
        return [f"{section}: 没有数据行时应整节省略"], header, []
    return [], header, rows


def analyze(text: str, paths: set[str] | None = None) -> tuple[list[str], dict]:
    errors, found = split_sections(text)
    for name in REQUIRED_SECTIONS:
        if name not in found:
            errors.append(f"{name}: 缺少必填章节")
    if "概述" in found:
        errors.extend(check_overview(found["概述"][0]))

    counts = {name: 0 if name not in found else None for name in COUNT_NAMES}
    finding_ids: set[str] = set()
    points: list[dict] = []

    for section in OPTIONAL_SECTIONS:
        if section not in found:
            counts[section] = 0
            continue
        body, start_line = found[section]
        parsed = parse_table(body, start_line)
        if parsed is None or not parsed[1]:
            errors.append(f"{section}: 没有数据行时应整节省略")
            counts[section] = 0
            continue
        header, rows = parsed
        if tuple(header) != FINDING_HEADERS:
            errors.append(f"{section}: 表头须为 {'、'.join(FINDING_HEADERS)}")
            continue
        counts[section] = len(rows)
        row_errors, ids = check_finding_rows(section, header, rows, paths)
        errors.extend(row_errors)
        finding_ids.update(ids)

    if "测试点" in found:
        body, start_line = found["测试点"]
        table_errors, header, rows = check_table("测试点", body, start_line, POINT_HEADERS)
        if any(item.endswith("没有数据行时应整节省略") for item in table_errors):
            table_errors = ["测试点: 至少要有一行"]
        errors.extend(table_errors)
        if header is not None:
            counts["测试点"] = len(rows)
            row_errors, points = check_point_rows(header, rows, finding_ids)
            errors.extend(row_errors)

    if "结论" in found:
        body = "\n".join(found["结论"][0])
        for name, pattern in COUNT_RE.items():
            match = pattern.search(body)
            if not match:
                errors.append(f"结论: 缺少{name}条数")
                continue
            if counts[name] is None:
                continue
            reported = int(match.group(1))
            if reported != counts[name]:
                errors.append(f"结论: {name}条数不一致（报告 {reported}，表格 {counts[name]}）")

    data = {
        "defects": counts["缺陷"] or 0,
        "problems": counts["引起的问题"] or 0,
        "points": counts["测试点"] or 0,
        "rows": points,
    }
    return errors, data


def export_points(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(POINT_HEADERS),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验版本代码审核稿")
    parser.add_argument("review", type=Path, help="审核稿 Markdown 路径")
    parser.add_argument("--diff", type=Path, help="unified diff，用于核对位置里的路径")
    parser.add_argument("--summary", action="store_true", help="通过时只输出三类条数")
    parser.add_argument("--export-points", type=Path, help="通过后把测试点写成 TSV")
    args = parser.parse_args(argv)

    if not args.review.is_file():
        print(f"找不到文件：{args.review}", file=sys.stderr)
        return 1
    paths: set[str] | None = None
    if args.diff is not None:
        if not args.diff.is_file():
            print(f"找不到文件：{args.diff}", file=sys.stderr)
            return 1
        try:
            parsed = parse_diff(args.diff.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        if not parsed:
            print("diff 中没有文件", file=sys.stderr)
            return 1
        paths = {item["path"] for item in parsed}

    errors, data = analyze(args.review.read_text(encoding="utf-8"), paths)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    if args.export_points is not None:
        export_points(args.export_points, data["rows"])
    if args.summary:
        payload = {
            "source": str(args.review),
            "defects": data["defects"],
            "problems": data["problems"],
            "points": data["points"],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print("校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
