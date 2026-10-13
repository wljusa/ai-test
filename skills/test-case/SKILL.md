---
name: test-case
description: >-
  Generates a test-case TSV from reviewed test points and reviews cases
  against those points. Checks columns, numbered steps, and TP coverage
  with check_cases.py. Use when the user asks to 生成测试用例, 写用例,
  审核测试用例, or 检查用例.
---

# 测试用例

从已审核的测试点写出用例表，或审核已有用例表。不调用任何外部系统。

模板：[templates/test-cases.tsv](templates/test-cases.tsv)。合格与不合格样例在 [examples/](examples/)。

## 判定

- 要生成、补写，且已有测试点文件 → 生成
- 已有用例表，要审核、检查 → 审核
- 缺测试点文件就问，不要猜。测试点还没通过 `check_points.py` 时，先走 test-point

## 生成

1. 按模板写 TSV。列：`测试项`、`前置条件`、`步骤描述`、`预期结果`、`优先级`、`负责人`、`测试点编号`。
2. 运行：

```bash
python3 skills/test-case/scripts/check_cases.py <cases.tsv> --points <points.tsv>
```

3. 退出码 0 后再确认能被用例表解析：

```bash
python3 skills/case-table/scripts/parse_cases.py <cases.tsv> --summary
```

4. 两条都通过后，再看步骤是否从真实入口开始、预期是否可判定、是否把多个测试点塞进一条。有问题就改文件，重新跑。不要口头说通过。

要条数和分组时给 `check_cases.py` 加 `--summary`。不要把整表贴进回复。

## 审核

1. 先跑 `check_cases.py`。退出码 1 时按 stderr 的行号改，再跑。
2. 脚本通过后看：前置是否写了角色、入口和已有数据；步骤是否从真实入口开始；预期是否看得判；一条用例是否只覆盖一个测试点。
3. 意见改回文件后再跑脚本。回复写脚本结果，并写上仍在的问题。

## 写法

- 测试项：`{模块}_{场景类型}_{结果}`，场景类型与测试点一致。
- 步骤：`1. …；2. …`。预期结果只写最终可观察结果。
- 每个 `TP*` 至少一条用例。负责人留空，除非用户指定。
- 优先级沿用测试点。主路径、权限、会造成数据损坏的用 P0。

## 不要做

- 不要改字段名，也不要删掉 `测试点编号`。
- 不要在脚本失败时手改 JSON 或口头说通过。
