#!/usr/bin/env python3
"""解析 unified diff，汇总改动文件和增删行。不输出 diff 正文。

用法:
  python3 skills/version-review/scripts/summarize_diff.py path/to/change.diff --summary
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

GIT_HEADER = re.compile(r"^diff --git a/(.+) b/(.+)$")


def _strip_prefix(path: str) -> str:
    if path.startswith(("a/", "b/")):
        return path[2:]
    return path


def _file_token(text: str) -> str:
    token = text.strip().split("\t", 1)[0].strip()
    if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
        token = token[1:-1]
    return _strip_prefix(token)


def parse_diff(text: str) -> list[dict]:
    """返回按出现顺序合并后的文件列表。每项含 path、added、removed。"""
    order: list[str] = []
    files: dict[str, dict] = {}
    current: dict | None = None

    def finish() -> None:
        nonlocal current
        if current is None:
            return
        path = current["path"]
        if not path or path == "/dev/null":
            raise ValueError("diff: 无法识别文件路径")
        if path not in files:
            files[path] = {"path": path, "added": 0, "removed": 0}
            order.append(path)
        files[path]["added"] += current["added"]
        files[path]["removed"] += current["removed"]
        current = None

    for line in text.splitlines():
        header = GIT_HEADER.match(line)
        if header:
            finish()
            current = {"path": header.group(2), "added": 0, "removed": 0}
            continue
        if current is None:
            continue
        if line.startswith("--- "):
            path = _file_token(line[4:])
            if path != "/dev/null":
                current["path"] = path
            continue
        if line.startswith("+++ "):
            path = _file_token(line[4:])
            if path != "/dev/null":
                current["path"] = path
            continue
        if line.startswith("+"):
            current["added"] += 1
        elif line.startswith("-"):
            current["removed"] += 1
    finish()
    return [files[path] for path in order]


def summarize(path: Path, files: list[dict]) -> dict:
    return {
        "source": str(path),
        "fileCount": len(files),
        "added": sum(item["added"] for item in files),
        "removed": sum(item["removed"] for item in files),
        "files": files,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="汇总 unified diff 的文件与增删行")
    parser.add_argument("diff", type=Path, help="unified diff 路径")
    parser.add_argument("--summary", action="store_true", help="只输出文件数和增删行")
    args = parser.parse_args(argv)

    if not args.diff.is_file():
        print(f"找不到文件：{args.diff}", file=sys.stderr)
        return 1
    try:
        files = parse_diff(args.diff.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not files:
        print("diff 中没有文件", file=sys.stderr)
        return 1
    print(json.dumps(summarize(args.diff, files), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
