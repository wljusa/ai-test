#!/usr/bin/env python3
"""Tests for check_report.py."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_report import check

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
SCRIPT = Path(__file__).resolve().parent / "check_report.py"

GOOD = """# 测试报告

## 概述

版本：1.2.0
环境：测试环境
范围：登录与购物车

## 执行结果

| 用例 | 结果 | 说明 |
|---|---|---|
| 登录_账号_密码正确进入首页 | 通过 | |
| 购物车_结算_空购物车不可提交 | 失败 | 空购物车仍可点击结算 |

## 缺陷

| 编号 | 严重级别 | 现象 | 对应用例 |
|---|---|---|---|
| BUG-1 | 严重 | 空购物车仍可点击结算 | 购物车_结算_空购物车不可提交 |

## 结论

- 通过：1
- 失败：1
- 阻塞：0
- 结论：不通过
"""

ALL_PASS = """# 测试报告

## 概述

版本：1.2.0
环境：测试环境
范围：登录

## 执行结果

| 用例 | 结果 | 说明 |
|---|---|---|
| 登录_账号_密码正确进入首页 | 通过 | |

## 结论

- 通过：1
- 失败：0
- 阻塞：0
- 结论：通过
"""

BAD_COUNTS = """# 测试报告

## 概述

版本：1.2.0
环境：测试环境
范围：登录与购物车

## 执行结果

| 用例 | 结果 | 说明 |
|---|---|---|
| 登录_账号_密码正确进入首页 | 通过 | |
| 购物车_结算_空购物车不可提交 | 失败 | 空购物车仍可点击结算 |

## 缺陷

| 编号 | 严重级别 | 现象 | 对应用例 |
|---|---|---|---|
| BUG-1 | 严重 | 空购物车仍可点击结算 | 购物车_结算_空购物车不可提交 |

## 结论

- 通过：2
- 失败：0
- 阻塞：0
- 结论：通过
"""


class CheckReportTest(unittest.TestCase):
    def test_good_report_passes(self):
        self.assertEqual(check(GOOD), [])

    def test_omitted_optional_sections_pass(self):
        self.assertEqual(check(ALL_PASS), [])

    def test_wrong_counts_name_the_section(self):
        errors = check(BAD_COUNTS)
        self.assertTrue(any(item.startswith("结论:") for item in errors))
        self.assertTrue(any("通过条数不一致" in item for item in errors))

    def test_missing_required_section(self):
        errors = check(GOOD.replace("## 概述\n\n版本：1.2.0\n环境：测试环境\n范围：登录与购物车\n\n", ""))
        self.assertIn("概述: 缺少必填章节", errors)

    def test_empty_defect_section_must_be_omitted(self):
        text = ALL_PASS.replace("## 结论", "## 缺陷\n\n没有条目。\n\n## 结论")
        self.assertIn("缺陷: 没有数据行时应整节省略", check(text))

    def test_invalid_result_value(self):
        text = ALL_PASS.replace("| 通过 |", "| 待测 |", 1)
        errors = check(text)
        self.assertTrue(any("执行结果:" in item and "待测" in item for item in errors))

    def test_example_files(self):
        self.assertEqual(check((EXAMPLES / "good-report.md").read_text(encoding="utf-8")), [])
        errors = check((EXAMPLES / "bad-report.md").read_text(encoding="utf-8"))
        self.assertTrue(any(item.startswith("结论:") for item in errors))

    def test_cli_exit_codes(self):
        ok = subprocess.run([sys.executable, str(SCRIPT), str(EXAMPLES / "good-report.md")], capture_output=True, text=True)
        bad = subprocess.run([sys.executable, str(SCRIPT), str(EXAMPLES / "bad-report.md")], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0)
        self.assertIn("校验通过", ok.stdout)
        self.assertEqual(bad.returncode, 1)
        self.assertIn("结论:", bad.stderr)


if __name__ == "__main__":
    unittest.main()
