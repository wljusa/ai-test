#!/usr/bin/env python3
"""Tests for parse_cases.py."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_cases import detect_delimiter, directory_parts, main, parse_rows, split_steps

TSV = (
    "测试项\t前置条件\t步骤描述\t预期结果\t优先级\t负责人\t备注\n"
    "登录_账号_密码正确进入首页\t已注册账号\t1. 打开登录页；2. 输入正确密码并提交\t进入首页\tP0\t测试员甲\t忽略\n"
    "\t空标题跳过\t1. 无操作\t无\tP2\t测试员甲\t\n"
    "购物车_结算_空购物车不可提交\t购物车为空\t1. 打开购物车；2. 点击结算\t结算按钮不可用\tP1\t测试员乙\t\n"
    "无下划线标题\t无\t整段一步\t页面可见\tP2\t测试员甲\t\n"
)


def test_split_steps_strips_numbers():
    assert split_steps("1. 打开登录页；2. 输入正确密码并提交") == ["打开登录页", "输入正确密码并提交"]


def test_directory_parts():
    assert directory_parts("登录_账号_密码正确进入首页") == ["登录", "账号"]
    assert directory_parts("无下划线标题") == []


def test_parse_rows_skips_blank_title_and_keeps_expected_on_last_step():
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False) as handle:
        handle.write(TSV)
        path = Path(handle.name)
    try:
        rows = parse_rows(path, "\t")
    finally:
        path.unlink()
    assert len(rows) == 3
    first = rows[0]
    assert first["title"] == "登录_账号_密码正确进入首页"
    assert first["directory"] == ["登录", "账号"]
    assert first["owner"] == "测试员甲"
    assert len(first["steps"]) == 2
    assert first["steps"][0]["expected"] is None
    assert first["steps"][1]["expected"] == "进入首页"
    assert rows[2]["directory"] == []
    assert "testSteps" not in first


def test_summary_omits_cases():
    with tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False) as handle:
        handle.write(TSV)
        path = Path(handle.name)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as skip:
        skip.write("无下划线标题\n")
        skip_path = Path(skip.name)
    try:
        buf = StringIO()
        with redirect_stdout(buf):
            code = main([str(path), "--summary", "--skip-subjects", str(skip_path)])
        assert code == 0
        payload = json.loads(buf.getvalue())
        assert payload["total"] == 3
        assert payload["kept"] == 2
        assert "cases" not in payload
        assert payload["groups"] == {"登录_账号": 1, "购物车_结算": 1}
        assert payload["skippedSubjects"] == ["无下划线标题"]
    finally:
        path.unlink()
        skip_path.unlink()


def test_missing_title_column_exits():
    with tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", delete=False) as handle:
        handle.write("名称,步骤\n登录,打开\n")
        path = Path(handle.name)
    try:
        with pytest.raises(SystemExit, match="测试项"):
            parse_rows(path, ",")
    finally:
        path.unlink()


def test_detect_delimiter_by_suffix():
    assert detect_delimiter(Path("a.tsv"), None) == "\t"
    assert detect_delimiter(Path("a.csv"), None) == ","
