---
name: report-check
description: >-
  Checks a Markdown test report for required sections, allowed
  result values, and conclusion counts that match the result table.
  Use when the user asks to 校验测试报告, 检查报告结构, or lint a test report.
---

# 测试报告校验

检查 Markdown 测试报告的结构。不判断用例本身对不对，只判断报告能不能当正式结果用。

模板：[templates/test-report.md](templates/test-report.md)。

## 必填

- 概述：版本、环境、范围，不能空
- 执行结果：表头为「用例、结果、说明」。结果只允许 `通过`、`失败`、`阻塞`
- 结论：写出通过、失败、阻塞三条计数，并且和执行结果表一致

## 可省略

缺陷、风险没有数据行时，整章都不要写。写了标题却没有表格数据行，校验失败。

## 步骤

1. 报告落盘后运行：

```bash
python3 skills/report-check/scripts/check_report.py <report.md>
```

2. 退出码 0 时，回复里写「校验通过」。退出码 1 时，按 stderr 的章节名改报告，再跑一次。不要口头声明通过。

## 不要做

- 不要手算条数去覆盖脚本结果。
- 不要为了凑结构编造缺陷或风险；没有就删章。
