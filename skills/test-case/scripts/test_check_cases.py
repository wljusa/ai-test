#!/usr/bin/env python3
"""Tests for check_cases.py."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent
CASE_TABLE = SCRIPTS.parents[1] / "case-table" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(CASE_TABLE))

from check_cases import check, load_cases, main
from parse_cases import parse_rows

EXAMPLES = SCRIPTS.parents[0] / "examples"
POINTS = SCRIPTS.parents[1] / "test-point" / "examples" / "good-points.tsv"

HEADER = "测试项\t前置条件\t步骤描述\t预期结果\t优先级\t负责人\t测试点编号\n"
GOOD_ROW = (
    "登录_主路径_正确密码进入首页\t已注册用户；从登录页进入；账号已设置密码\t"
    "1. 打开登录页；2. 输入正确密码并提交\t进入首页\tP0\t\tTP1\n"
)


def _write(text: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False)
    handle.write(text)
    handle.close()
    return Path(handle.name)


def test_good_example_passes_and_parses():
    from check_points import load_points

    cases = load_cases(EXAMPLES / "good-cases.tsv")
    points = load_points(POINTS)
    assert check(cases, points) == []
    parsed = parse_rows(EXAMPLES / "good-cases.tsv", "\t")
    assert len(parsed) == 6
    assert parsed[0]["directory"] == ["登录", "主路径"]
    assert parsed[0]["steps"][0]["expected"] is None
    assert parsed[0]["steps"][1]["expected"] == "进入首页"
    assert "测试点编号" not in parsed[0]


def test_bad_example_names_row_and_missing_point():
    from check_points import load_points

    errors = check(load_cases(EXAMPLES / "bad-cases.tsv"), load_points(POINTS))
    assert any("第2行" in item and "模块_场景类型_结果" in item for item in errors)
    assert any("第2行" in item and "1. …；2. …" in item for item in errors)
    assert any("第3行" in item and "TP99" in item for item in errors)
    assert any("测试点「TP2」没有对应用例" in item for item in errors)


def test_title_must_match_point_scene():
    from check_points import load_points

    text = HEADER + GOOD_ROW.replace("登录_主路径_", "登录_异常_", 1)
    path = _write(text)
    try:
        errors = check(load_cases(path), load_points(POINTS))
    finally:
        path.unlink()
    assert any("TP1" in item and "不一致" in item for item in errors)


def test_missing_column_exits():
    path = _write("测试项\t前置条件\n登录\t无\n")
    try:
        with pytest.raises(SystemExit, match="测试点编号"):
            load_cases(path)
    finally:
        path.unlink()


def test_summary_omits_case_text():
    buf = StringIO()
    with redirect_stdout(buf):
        code = main([str(EXAMPLES / "good-cases.tsv"), "--points", str(POINTS), "--summary"])
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["total"] == 6
    assert payload["covered"] == 6
    assert payload["groups"]["登录_主路径"] == 1
    assert "进入首页" not in buf.getvalue()


def test_cli_exit_codes():
    err = StringIO()
    with redirect_stderr(err):
        bad = main([str(EXAMPLES / "bad-cases.tsv"), "--points", str(POINTS)])
    assert bad == 1
    assert "第2行" in err.getvalue()
    out = StringIO()
    with redirect_stdout(out):
        ok = main([str(EXAMPLES / "good-cases.tsv"), "--points", str(POINTS)])
    assert ok == 0
    assert "校验通过" in out.getvalue()
