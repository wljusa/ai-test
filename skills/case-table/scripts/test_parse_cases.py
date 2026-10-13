#!/usr/bin/env python3
"""Tests for parse_cases.py."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_cases import detect_delimiter, directory_parts, main, parse_rows, split_steps

TSV = (
    "测试项\t前置条件\t步骤描述\t预期结果\t优先级\t负责人\t备注\n"
    "登录_账号_密码正确进入首页\t已注册账号\t1. 打开登录页；2. 输入正确密码并提交\t进入首页\tP0\t测试员甲\t忽略\n"
    "\t空标题跳过\t1. 无操作\t无\tP2\t测试员甲\t\n"
    "购物车_结算_空购物车不可提交\t购物车为空\t1. 打开购物车；2. 点击结算\t结算按钮不可用\tP1\t测试员乙\t\n"
    "无下划线标题\t无\t整段一步\t页面可见\tP2\t测试员甲\t\n"
)


class ParseCasesTest(unittest.TestCase):
    def test_split_steps_strips_numbers(self):
        self.assertEqual(split_steps("1. 打开登录页；2. 输入正确密码并提交"), ["打开登录页", "输入正确密码并提交"])

    def test_directory_parts(self):
        self.assertEqual(directory_parts("登录_账号_密码正确进入首页"), ["登录", "账号"])
        self.assertEqual(directory_parts("无下划线标题"), [])

    def test_parse_rows_skips_blank_title_and_keeps_expected_on_last_step(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False) as handle:
            handle.write(TSV)
            path = Path(handle.name)
        try:
            rows = parse_rows(path, "\t")
        finally:
            path.unlink()
        self.assertEqual(len(rows), 3)
        first = rows[0]
        self.assertEqual(first["title"], "登录_账号_密码正确进入首页")
        self.assertEqual(first["directory"], ["登录", "账号"])
        self.assertEqual(first["owner"], "测试员甲")
        self.assertEqual(len(first["steps"]), 2)
        self.assertIsNone(first["steps"][0]["expected"])
        self.assertEqual(first["steps"][1]["expected"], "进入首页")
        self.assertEqual(rows[2]["directory"], [])
        self.assertNotIn("testSteps", first)

    def test_summary_omits_cases(self):
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
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["total"], 3)
            self.assertEqual(payload["kept"], 2)
            self.assertNotIn("cases", payload)
            self.assertEqual(payload["groups"], {"登录_账号": 1, "购物车_结算": 1})
            self.assertEqual(payload["skippedSubjects"], ["无下划线标题"])
        finally:
            path.unlink()
            skip_path.unlink()

    def test_missing_title_column_exits(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", encoding="utf-8", delete=False) as handle:
            handle.write("名称,步骤\n登录,打开\n")
            path = Path(handle.name)
        try:
            with self.assertRaises(SystemExit) as raised:
                parse_rows(path, ",")
            self.assertIn("测试项", str(raised.exception))
        finally:
            path.unlink()

    def test_detect_delimiter_by_suffix(self):
        self.assertEqual(detect_delimiter(Path("a.tsv"), None), "\t")
        self.assertEqual(detect_delimiter(Path("a.csv"), None), ",")


if __name__ == "__main__":
    unittest.main()
