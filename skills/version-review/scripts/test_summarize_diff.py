#!/usr/bin/env python3
"""Tests for summarize_diff.py."""

from __future__ import annotations

import json
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from summarize_diff import main, parse_diff

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"

NEW_FILE = """diff --git a/shop/ping.py b/shop/ping.py
new file mode 100644
index 0000000..aaaaaaa
--- /dev/null
+++ b/shop/ping.py
@@ -0,0 +1,2 @@
+def ping():
+    return "pong"
"""

DELETED = """diff --git a/shop/old.py b/shop/old.py
deleted file mode 100644
index bbbbbbb..0000000
--- a/shop/old.py
+++ /dev/null
@@ -1 +0,0 @@
-def gone():
"""


def test_example_counts_files_and_lines():
    files = parse_diff((EXAMPLES / "change.diff").read_text(encoding="utf-8"))
    assert [item["path"] for item in files] == ["shop/cart.py", "shop/auth.py"]
    cart, auth = files
    assert cart["added"] == 3
    assert cart["removed"] == 1
    assert auth["added"] == 0
    assert auth["removed"] == 1


def test_new_file_ignores_dev_null():
    files = parse_diff(NEW_FILE)
    assert files == [{"path": "shop/ping.py", "added": 2, "removed": 0}]


def test_deleted_file_keeps_old_path():
    files = parse_diff(DELETED)
    assert files == [{"path": "shop/old.py", "added": 0, "removed": 1}]


def test_summary_omits_diff_body():
    buf = StringIO()
    with redirect_stdout(buf):
        code = main([str(EXAMPLES / "change.diff"), "--summary"])
    assert code == 0
    payload = json.loads(buf.getvalue())
    assert payload["fileCount"] == 2
    assert payload["added"] == 3
    assert payload["removed"] == 2
    assert "user.session.clear" not in buf.getvalue()
    assert "can_checkout" not in buf.getvalue()


def test_empty_diff_exits():
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.diff"
        empty.write_text("", encoding="utf-8")
        err = StringIO()
        with redirect_stderr(err):
            code = main([str(empty), "--summary"])
        assert code == 1
        assert "没有文件" in err.getvalue()


def test_missing_file_exits():
    err = StringIO()
    with redirect_stderr(err):
        code = main([str(EXAMPLES / "missing.diff")])
    assert code == 1
    assert "找不到文件" in err.getvalue()
