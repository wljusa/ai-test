#!/usr/bin/env python3
"""校验测试报告 Markdown 结构。失败则退出码 1。

用法:
  python3 skills/report-check/scripts/check_report.py path/to/report.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_SECTIONS = ("概述", "执行结果", "结论")
OMIT_WHEN_EMPTY = ("缺陷", "风险")
RESULT_HEADERS = ("用例", "结果", "说明")
ALLOWED_RESULTS = ("通过", "失败", "阻塞")

SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.M)
COUNT_RE = {
    name: re.compile(rf"^[-*]\s*{name}\s*[:：]\s*(\d+)\s*$", re.M)
    for name in ALLOWED_RESULTS
}
SEPARATOR_CELL = re.compile(r":?-{3,}:?")


def split_sections(text: str) -> list[tuple[str, str]]:
    matches = list(SECTION_RE.finditer(text))
    sections = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections.append((match.group(1).strip(), text[start:end]))
    return sections


def split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator(line: str) -> bool:
    cells = split_row(line)
    return bool(cells) and all(SEPARATOR_CELL.fullmatch(cell.replace(" ", "")) for cell in cells)


def parse_table(body: str) -> tuple[list[str], list[list[str]]] | None:
    lines = [line.strip() for line in body.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2 or not is_separator(lines[1]):
        return None
    header = split_row(lines[0])
    rows = []
    for line in lines[2:]:
        cells = split_row(line)
        if any(cells):
            rows.append(cells)
    return header, rows


def check(text: str) -> list[str]:
    errors: list[str] = []
    found: dict[str, str] = {}
    for name, body in split_sections(text):
        if name in found:
            errors.append(f"{name}: 章节重复")
            continue
        found[name] = body

    for name in REQUIRED_SECTIONS:
        if name not in found:
            errors.append(f"{name}: 缺少必填章节")

    if "概述" in found and not found["概述"].strip():
        errors.append("概述: 章节为空")

    counts = {name: 0 for name in ALLOWED_RESULTS}
    if "执行结果" in found:
        parsed = parse_table(found["执行结果"])
        if parsed is None:
            errors.append("执行结果: 缺少表格")
        else:
            header, rows = parsed
            if tuple(header) != RESULT_HEADERS:
                errors.append(f"执行结果: 表头须为 {'、'.join(RESULT_HEADERS)}")
            elif not rows:
                errors.append("执行结果: 至少要有一行结果")
            else:
                result_at = header.index("结果")
                for row in rows:
                    value = row[result_at] if result_at < len(row) else ""
                    if value not in ALLOWED_RESULTS:
                        errors.append(f"执行结果: 结果「{value or '空'}」不在允许值内")
                    else:
                        counts[value] += 1

    for name in OMIT_WHEN_EMPTY:
        if name not in found:
            continue
        parsed = parse_table(found[name])
        if parsed is None or not parsed[1]:
            errors.append(f"{name}: 没有数据行时应整节省略")

    if "结论" in found:
        body = found["结论"]
        reported: dict[str, int] = {}
        for name, pattern in COUNT_RE.items():
            match = pattern.search(body)
            if not match:
                errors.append(f"结论: 缺少{name}条数")
            else:
                reported[name] = int(match.group(1))
        if len(reported) == len(ALLOWED_RESULTS) and "执行结果: 缺少表格" not in errors:
            for name in ALLOWED_RESULTS:
                if reported[name] != counts[name]:
                    errors.append(
                        f"结论: {name}条数不一致（报告 {reported[name]}，表格 {counts[name]}）"
                    )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验测试报告 Markdown 结构")
    parser.add_argument("report", type=Path, help="测试报告路径")
    args = parser.parse_args(argv)

    if not args.report.is_file():
        print(f"找不到文件：{args.report}", file=sys.stderr)
        return 1

    errors = check(args.report.read_text(encoding="utf-8"))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
