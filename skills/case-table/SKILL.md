---
name: case-table
description: >-
  Parses a local TSV or CSV test-case table into neutral JSON
  (title, precondition, priority, owner, directory, steps).
  Use when the user asks to 解析用例, 用例表, 拆步骤, or gives a
  .tsv/.csv case table.
---

# 用例表解析

把本地 TSV/CSV 解析成与测试平台无关的 JSON。不调用任何外部系统。

## 输入

缺文件路径就问，不要猜。

- 编码 UTF-8
- `.tsv` 用制表符，`.csv` 用逗号；其它扩展名看内容里哪种分隔符更多
- 表头必须有「测试项」。可选列：前置条件、步骤描述、预期结果、优先级、负责人
- 未列出的列忽略

## 步骤

1. 先跑摘要，不要整文件读表，也不要把用例正文读进对话：

```bash
python3 skills/case-table/scripts/parse_cases.py <path> --summary
```

2. 用户要正文时去掉 `--summary`。已有标题放在一个文本文件里，每行一个，用 `--skip-subjects` 按整标题跳过。
3. 把 stdout 里的条数和分组贴进回复。脚本失败（退出码非 0）就停，不要手改 JSON 补上。

## 规则

- 步骤按中文分号加编号切开：`1. …；2. …`。去掉行首 `N.`。切不开则整段当一步。
- 中间步的 `expected` 为 `null`，预期结果只写在最后一步。
- 标题用 `_` 分段。前两段放进 `directory`，标题全文仍是 `title`。
- 空标题的行跳过。

## 不要做

- 不要评价优先级划得对不对。
- 不要把脚本输出改写成另一种字段名。
