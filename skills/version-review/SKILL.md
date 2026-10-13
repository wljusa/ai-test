---
name: version-review
description: >-
  Reviews a version diff against requirements and issues, and writes
  defects, regressions, and test points. Checks the review with
  check_review.py. Use when the user asks to 版本代码审核, 审核版本代码,
  对照 diff, 找出缺陷, or 引起的问题.
---

# 版本代码审核

对照版本 diff、需求和问题，写出缺陷、引起的问题和测试点。不调用 git，也不解析代码语义。

模板：[templates/version-review.md](templates/version-review.md)。合格与不合格样例在 [examples/](examples/)。

## 判定

- 已有版本 diff，要对照需求或问题审核 → 审核
- 缺 diff 或需求就问，不要猜。没有问题单时，概述写 `问题：无`

## 审核

1. diff、需求、问题先落盘。粘贴的正文写成文件再审。
2. 先看改了哪些文件：

```bash
python3 skills/version-review/scripts/summarize_diff.py <change.diff> --summary
```

3. 再读 diff 里相关改动，对照需求和问题，按模板写审核稿。
4. 运行：

```bash
python3 skills/version-review/scripts/check_review.py <review.md> --diff <change.diff>
```

5. 退出码 0 后，再看有没有漏掉的缺陷、引起的问题或测试点。有就改稿，重新跑。不要口头说通过。
6. 要把测试点交给后续流程时：

```bash
python3 skills/version-review/scripts/check_review.py <review.md> \
  --diff <change.diff> --export-points <points.tsv>
python3 skills/test-point/scripts/check_points.py <points.tsv>
```

要三类条数时给 `check_review.py` 加 `--summary`。不要把整份 diff 或整张表贴进回复。

## 写法

- 缺陷：实现和需求或问题不符，或改动本身写错。编号 `DF1`。没有就整章删除。
- 引起的问题：这次改动带来的回归或副作用。编号 `IP1`。没有就整章删除。
- 位置写 diff 里的路径加行号，例如 `shop/cart.py:12`。
- 严重级别只写：致命、严重、一般。
- 测试点列与测试点技能相同。编号 `TP1`。来源指向需求原句、问题编号，或本稿里的 `DF*` / `IP*`。
- 结论里的三条计数必须和表格行数一致。省略的章节计 0。

## 不要做

- 不要调用 git，也不要用脚本没给出的路径。
- 不要为了凑章节编造缺陷或引起的问题；没有就删章。
- 不要在脚本失败时改口说通过。
