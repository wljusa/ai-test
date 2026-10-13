# ai-test

Agent skill framework for test automation: case tables become structured JSON, and test reports are checked before they are treated as done.

给 Agent 用的测试自动化框架。技能文件写清何时用、跑哪条命令；拆步骤、对条数这些确定性工作放在 Python 脚本里，并用单元测试固定下来。

模型适合决定「要不要跑、跑哪一步」。编号步骤怎么切、报告里的通过条数和表格是否一致，每次现编都会漂。这里把这类步骤做成可重复执行的命令。

## 分工

```text
Agent 读取 SKILL.md
    -> 运行 scripts/ 里的命令
        -> unittest 固定脚本行为
```

Agent 默认只看 `--summary` 或校验结果，不把整张用例表读进对话。

## 目录

```text
docs/skill-convention.md     如何再加一个技能
skills/case-table/            用例表 TSV/CSV → JSON
skills/report-check/          测试报告 Markdown 结构校验
```

依赖：Python 3.9+，标准库。

## 用例表

把本地用例表解析成与平台无关的 JSON：`title`、`precondition`、`priority`、`owner`、`directory`、`steps`。

- `.tsv` 用制表符，`.csv` 用逗号；表头必须有「测试项」
- `1. …；2. …` 拆成步骤，预期结果只挂在最后一步
- 标题按 `_` 分段，前两段作为目录

```bash
python3 skills/case-table/scripts/parse_cases.py \
  skills/case-table/examples/sample.tsv --summary
```

去掉 `--summary` 会把用例正文打到标准输出。已有标题可以按整行匹配跳过：

```bash
python3 skills/case-table/scripts/parse_cases.py \
  skills/case-table/examples/sample.tsv \
  --skip-subjects skills/case-table/examples/already-there.txt
```

## 测试报告

校验一份 Markdown 测试报告：必填章节是否都在、结果取值是否合法、结论里的条数是否和执行结果表一致。失败时退出码为 1，并打印章节名。

```bash
python3 skills/report-check/scripts/check_report.py \
  skills/report-check/examples/good-report.md
```

空着的骨架在 [`skills/report-check/templates/test-report.md`](skills/report-check/templates/test-report.md)。缺陷、风险没有条目时删掉整章，不要留空表。

## 测试

```bash
python3 -m unittest discover -s skills -p 'test_*.py'
```

## 安装到 Cursor

```bash
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/skills/case-table" ~/.cursor/skills/case-table
ln -s "$(pwd)/skills/report-check" ~/.cursor/skills/report-check
```

## 再加一个技能

在 `skills/` 下新建目录，写 `SKILL.md` 和带测试的脚本。约定见 [docs/skill-convention.md](docs/skill-convention.md)。

## 许可

[MIT](LICENSE)
