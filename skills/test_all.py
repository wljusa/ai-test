#!/usr/bin/env python3
"""让 `unittest discover -s skills` 能跑到带连字符的技能目录。

技能目录名用连字符，不能当作 Python 包。发现命令只看见本文件，
再由它加载各技能 scripts/ 下的 test_*.py。
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load(path: Path):
    name = "ai_test_" + path.parent.parent.name.replace("-", "_") + "_" + path.stem
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_tests(loader: unittest.TestLoader, standard_tests: unittest.TestSuite, pattern: str):
    suite = unittest.TestSuite()
    for path in sorted(ROOT.glob("*/scripts/test_*.py")):
        suite.addTests(loader.loadTestsFromModule(_load(path)))
    return suite
