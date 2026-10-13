# ai-test

Agent skill framework for test automation: case tables become structured JSON, and test reports are checked before they are treated as done.

给 Agent 用的测试自动化框架。技能文件写清何时用、跑哪条命令；拆步骤、对条数这些确定性工作放在 Python 脚本里，并用 pytest 固定下来。

模型适合决定「要不要跑、跑哪一步」。编号步骤怎么切、报告里的通过条数和表格是否一致，每次现编都会漂。这里把这类步骤做成可重复执行的命令。

## 分工

```text
需求 + 版本 diff
  -> version-review 对照需求与问题审核代码，导出测试点
    -> test-point 生成并审核测试点
      -> test-case 生成并审核用例
        -> case-table 解析用例表
          -> 执行后 report-check 校验报告
```

Agent 读取 `SKILL.md`，运行 `scripts/` 里的命令。pytest 固定脚本行为。模型写内容和判断漏测、过测、含糊；字段、枚举、编号追溯和条数以脚本退出码为准。

Agent 默认只看 `--summary` 或校验结果，不把整张用例表读进对话。

## 目录

```text
docs/skill-convention.md     如何再加一个技能
skills/version-review/        对照 diff 审核版本代码，导出测试点
skills/test-point/            从需求生成并审核测试点
skills/test-case/             从测试点生成并审核用例表
skills/case-table/            用例表 TSV/CSV → JSON
skills/report-check/          测试报告 Markdown 结构校验
```

依赖：Python 3.9+，标准库。跑测试另需 pytest。

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

## 版本代码审核

对照 unified diff、需求和问题写审核稿：缺陷、引起的问题、测试点。脚本锁章节、编号、严重级别和结论条数；位置里的路径必须出现在 diff 中。漏审仍由模型在脚本通过后判断。失败时退出码为 1。

```bash
python3 skills/version-review/scripts/summarize_diff.py \
  skills/version-review/examples/change.diff --summary

python3 skills/version-review/scripts/check_review.py \
  skills/version-review/examples/good-review.md \
  --diff skills/version-review/examples/change.diff
```

没有缺陷或引起的问题时删掉整章，不要留空表。测试点可导出成测试点表，再交给 `check_points.py`。空着的骨架在 [`skills/version-review/templates/version-review.md`](skills/version-review/templates/version-review.md)。

## 测试点

从需求生成测试点，或审核已有测试点。列：`编号`、`模块`、`测试点`、`场景类型`、`优先级`、`来源`。脚本锁编号、场景、优先级和空字段；漏测和过测由模型对照需求判断。失败时退出码为 1，并打印行号和列名。

```bash
python3 skills/test-point/scripts/check_points.py \
  skills/test-point/examples/good-points.tsv
```

样例需求在 [`skills/test-point/examples/requirement.md`](skills/test-point/examples/requirement.md)。空表头在 [`skills/test-point/templates/test-points.tsv`](skills/test-point/templates/test-points.tsv)。

## 测试用例

从已审核的测试点生成用例表，或审核已有用例。用例列对齐用例表解析，并多一列 `测试点编号`。每个测试点至少一条用例，测试项为 `{模块}_{场景类型}_{结果}`。

```bash
python3 skills/test-case/scripts/check_cases.py \
  skills/test-case/examples/good-cases.tsv \
  --points skills/test-point/examples/good-points.tsv
```

通过后再解析：

```bash
python3 skills/case-table/scripts/parse_cases.py \
  skills/test-case/examples/good-cases.tsv --summary
```

## 测试

```bash
python3 -m pip install pytest
python3 -m pytest
```

## 安装到 Cursor

```bash
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/skills/version-review" ~/.cursor/skills/version-review
ln -s "$(pwd)/skills/test-point" ~/.cursor/skills/test-point
ln -s "$(pwd)/skills/test-case" ~/.cursor/skills/test-case
ln -s "$(pwd)/skills/case-table" ~/.cursor/skills/case-table
ln -s "$(pwd)/skills/report-check" ~/.cursor/skills/report-check
```

## 再加一个技能

在 `skills/` 下新建目录，写 `SKILL.md` 和带测试的脚本。约定见 [docs/skill-convention.md](docs/skill-convention.md)。

## 许可

[MIT](LICENSE)
