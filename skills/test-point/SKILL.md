---
name: test-point
description: >-
  Generates test points from a requirement and reviews an existing point
  table. Checks the TSV with check_points.py (ids, scene, priority, source).
  Use when the user asks to 生成测试点, 写测试点, 审核测试点, or 检查测试点.
---

# 测试点

从需求写出测试点，或审核已有测试点。不调用任何外部系统。

模板：[templates/test-points.tsv](templates/test-points.tsv)。合格与不合格样例在 [examples/](examples/)。

## 判定

- 要生成、补写 → 生成
- 已有测试点，要审核、检查 → 审核
- 缺需求来源就问，不要猜

## 生成

1. 需求先落盘。粘贴的正文写成文件再填表。
2. 按模板写 TSV。列：`编号`、`模块`、`测试点`、`场景类型`、`优先级`、`来源`。
3. 运行：

```bash
python3 skills/test-point/scripts/check_points.py <points.tsv>
```

4. 退出码 0 后，再看漏测、过测、含糊。有问题就改文件，重新跑脚本。不要口头说通过。

要条数和场景分布时加 `--summary`。不要把整表贴进回复。

## 审核

1. 先跑上面的命令。退出码 1 时按 stderr 的行号和列名改，再跑。
2. 脚本通过后，对照需求看：每条需求是否有测试点或写明不测原因；有没有需求外功能；测试点是否写可观察结果。
3. 意见改回文件后再跑脚本。回复写脚本结果，并写上仍在的漏测或过测。

## 写法

- 编号用 `TP1`、`TP2`，不重复。
- 场景类型只写：主路径、异常、边界、权限、空数据、回放。
- 主路径用 P0。权限、会造成数据损坏的用 P0。其余默认 P1。纯展示细节用 P2。
- 测试点写结果，不写「打开页面」。来源指向需求原句。

## 不要做

- 不要把测试点写成用例步骤。
- 不要在脚本失败时改口说通过。
