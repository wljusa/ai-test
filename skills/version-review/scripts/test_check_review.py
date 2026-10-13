#!/usr/bin/env python3
"""Tests for check_review.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_review import analyze, main
from summarize_diff import parse_diff

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
POINTS = Path(__file__).resolve().parents[2] / "test-point" / "scripts" / "check_points.py"


def paths_of(name: str = "change.diff") -> set[str]:
    files = parse_diff((EXAMPLES / name).read_text(encoding="utf-8"))
    return {item["path"] for item in files}


def review_text(name: str) -> str:
    return (EXAMPLES / name).read_text(encoding="utf-8")


MINIMAL = """# 版本代码审核

## 概述

版本：1.3.0
需求：登录与购物车
问题：无
diff：examples/change.diff

## 测试点

| 编号 | 模块 | 测试点 | 场景类型 | 优先级 | 来源 |
|---|---|---|---|---|---|
| TP1 | 登录 | 正确密码提交后进入首页 | 主路径 | P0 | 需求：已注册用户输入正确密码后进入首页 |

## 结论

- 缺陷：0
- 引起的问题：0
- 测试点：1
"""


def test_good_example_passes():
    errors, data = analyze(review_text("good-review.md"), paths_of())
    assert errors == []
    assert data["defects"] == 1
    assert data["problems"] == 1
    assert data["points"] == 3


def test_omitted_optional_sections_pass():
    assert analyze(MINIMAL, paths_of())[0] == []


def test_bad_example_names_each_failure():
    errors = analyze(review_text("bad-review.md"), paths_of())[0]
    assert "概述: 缺少版本" in errors
    assert "缺陷: 没有数据行时应整节省略" in errors
    assert any("引起的问题:" in item and "BUG-1" in item and "编号" in item for item in errors)
    assert any("引起的问题:" in item and "高" in item and "严重级别" in item for item in errors)
    assert any("missing.py" in item and "不在 diff 中" for item in errors)
    assert any(item.startswith("结论:") and "缺陷条数不一致" in item for item in errors)
    assert any(item.startswith("结论:") and "引起的问题条数不一致" in item for item in errors)
    assert any(item.startswith("结论:") and "测试点条数不一致" in item for item in errors)


def test_prose_only_defect_section_must_be_omitted():
    text = MINIMAL.replace("## 测试点", "## 缺陷\n\n没有条目。\n\n## 测试点")
    text = text.replace("- 缺陷：0", "- 缺陷：1")
    errors = analyze(text, paths_of())[0]
    assert "缺陷: 没有数据行时应整节省略" in errors
    assert any("缺陷条数不一致" in item for item in errors)


def test_missing_required_section():
    text = review_text("good-review.md").replace("## 测试点\n", "## 范围\n")
    errors = analyze(text, paths_of())[0]
    assert "测试点: 缺少必填章节" in errors
    assert "范围: 未知章节" in errors


def test_source_must_cite_known_finding():
    text = MINIMAL.replace("需求：已注册用户输入正确密码后进入首页", "DF9")
    errors = analyze(text, paths_of())[0]
    assert any("来源" in item and "DF9" in item for item in errors)


def test_bare_action_point_is_rejected():
    text = MINIMAL.replace("正确密码提交后进入首页", "打开页面")
    errors = analyze(text, paths_of())[0]
    assert any("测试点" in item and "打开页面" in item for item in errors)


def test_summary_omits_finding_text():
    buf = StringIO()
    with redirect_stdout(buf):
        code = main([str(EXAMPLES / "good-review.md"), "--diff", str(EXAMPLES / "change.diff"), "--summary"])
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["defects"] == 1
    assert payload["problems"] == 1
    assert payload["points"] == 3
    assert "can_checkout" not in buf.getvalue()


def test_export_points_pass_check_points():
    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / "points.tsv"
        out = StringIO()
        with redirect_stdout(out):
            code = main([
                str(EXAMPLES / "good-review.md"),
                "--diff",
                str(EXAMPLES / "change.diff"),
                "--export-points",
                str(dest),
            ])
        assert code == 0
        assert dest.is_file()
        checked = subprocess.run([sys.executable, str(POINTS), str(dest)], capture_output=True, text=True)
        assert checked.returncode == 0
        assert "校验通过" in checked.stdout


def test_cli_exit_codes():
    err = StringIO()
    with redirect_stderr(err):
        bad = main([str(EXAMPLES / "bad-review.md"), "--diff", str(EXAMPLES / "change.diff")])
    assert bad == 1
    assert "概述:" in err.getvalue()
    out = StringIO()
    with redirect_stdout(out):
        ok = main([str(EXAMPLES / "good-review.md"), "--diff", str(EXAMPLES / "change.diff")])
    assert ok == 0
    assert "校验通过" in out.getvalue()
