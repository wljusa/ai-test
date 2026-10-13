# 技能约定

一个技能是一个目录。Agent 读 `SKILL.md` 决定要不要用它；真正改数据、拆文本、对数字的步骤写在 `scripts/` 里，并且有单元测试。

## 目录

```text
skills/<name>/
  SKILL.md          何时用、跑哪条命令、失败就停
  scripts/          可单独执行的 Python，只用标准库
  examples/         可公开的样例，不含真实账号和单据
  templates/        固定输出结构（需要时才有）
```

`name` 用小写和连字符，例如 `case-table`、`report-check`。

## SKILL.md

文件开头用 frontmatter：

```yaml
---
name: case-table
description: >-
  一两句说明做什么。写上用户可能说的关键词，方便 Agent 选中这个技能。
---
```

正文保持短。写清输入、命令、成功时看什么、失败时停。不要把分支规则、表格列和边界情况全写进正文；那些放在脚本和测试里，避免每次对话都重新发明一遍。

## 脚本

- 可单独执行：`python3 skills/<name>/scripts/<tool>.py ...`
- 失败用非 0 退出码，错误信息里带上章节名、列名或行号
- 给 Agent 的默认输出用 `--summary`：条数、分组、跳过了什么。整份 JSON 或报告正文不要默认塞进对话
- 依赖只使用 Python 3.9+ 标准库

## 测试

每个脚本配 `scripts/test_*.py`，用 `unittest`。技能目录名含连字符，不能当作 Python 包，所以发现入口是 `skills/test_all.py`，它再加载这些测试。在仓库根运行：

```bash
python3 -m unittest discover -s skills -p 'test_*.py'
```

改解析或校验规则时，先改测试再改脚本。样例用虚构的登录、购物车一类数据。

## 安装

Cursor 从 `~/.cursor/skills/` 加载技能。在仓库根执行：

```bash
mkdir -p ~/.cursor/skills
ln -s "$(pwd)/skills/case-table" ~/.cursor/skills/case-table
ln -s "$(pwd)/skills/report-check" ~/.cursor/skills/report-check
```

其他 Agent 按各自文档链到或复制 `skills/` 下的目录。改完脚本后链接仍然有效。
