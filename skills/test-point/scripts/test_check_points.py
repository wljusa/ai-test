#!/usr/bin/env python3
"""Tests for check_points.py."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_points import check, is_bare_action, load_points, main

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _write(text: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False)
    handle.write(text)
    handle.close()
    return Path(handle.name)


def test_good_example_passes():
    rows = load_points(EXAMPLES / "good-points.tsv")
    assert check(rows) == []
    assert len(rows) == 6


def test_bad_example_names_row_and_column():
    errors = check(load_points(EXAMPLES / "bad-points.tsv"))
    assert any("第2行" in item and "测试点" in item and "打开页面" in item for item in errors)
    assert any("第3行" in item and "TP1" in item and "重复" in item for item in errors)
    assert any("第3行" in item and "场景类型" in item and "冒烟" in item for item in errors)
    assert any("第3行" in item and "优先级" in item and "P3" in item for item in errors)
    assert any("第3行" in item and "来源" in item for item in errors)


def test_bare_action_rejects_open_page_only():
    assert is_bare_action("打开页面")
    assert is_bare_action("打开登录页")
    assert not is_bare_action("正确密码提交后进入首页")
    assert not is_bare_action("打开登录页并提示密码错误")


def test_missing_column_exits():
    path = _write("编号\t模块\nTP1\t登录\n")
    try:
        with pytest.raises(SystemExit, match="测试点"):
            load_points(path)
    finally:
        path.unlink()


def test_header_only_has_no_rows():
    path = _write("编号\t模块\t测试点\t场景类型\t优先级\t来源\n")
    try:
        assert check(load_points(path)) == ["没有数据行"]
    finally:
        path.unlink()


def test_summary_omits_point_text():
    buf = StringIO()
    with redirect_stdout(buf):
        code = main([str(EXAMPLES / "good-points.tsv"), "--summary"])
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["total"] == 6
    assert payload["scenes"]["主路径"] == 1
    assert payload["scenes"]["回放"] == 1
    assert "正确密码" not in buf.getvalue()


def test_cli_exit_codes():
    err = StringIO()
    with redirect_stderr(err):
        bad = main([str(EXAMPLES / "bad-points.tsv")])
    assert bad == 1
    assert "第2行" in err.getvalue()
    out = StringIO()
    with redirect_stdout(out):
        ok = main([str(EXAMPLES / "good-points.tsv")])
    assert ok == 0
    assert "校验通过" in out.getvalue()
