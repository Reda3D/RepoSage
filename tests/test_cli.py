import json
import tempfile
import unittest
from pathlib import Path

from reposage.cli import run


def _make_repo() -> Path:
    tmp = tempfile.mkdtemp()
    root = Path(tmp)
    (root / "app.py").write_text(
        'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/api/hello")\ndef hello():\n    pass  # TODO: add docs\n',
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("flask==3.0.3\n", encoding="utf-8")
    (root / "README.md").write_text("# Demo\n", encoding="utf-8")
    (root / "node_modules").mkdir()
    (root / "node_modules" / "dep.js").write_text("// noise\n", encoding="utf-8")
    return root


class TestCli(unittest.TestCase):
    def test_generate_writes_outputs(self):
        root = _make_repo()
        out = root / "reposage-out"
        rc = run(["generate", str(root), "--quiet"])
        self.assertEqual(rc, 0)
        self.assertTrue((out / "reposage.md").is_file())
        self.assertTrue((out / "reposage.json").is_file())
        md = (out / "reposage.md").read_text(encoding="utf-8")
        self.assertIn("/api/hello", md)
        self.assertIn("flask", md)
        self.assertIn("TODO", md)
        self.assertNotIn("node_modules", md)
        data = json.loads((out / "reposage.json").read_text(encoding="utf-8"))
        self.assertIn("overview", data)
        self.assertEqual(data["overview"]["total_files"], 3)

    def test_update_detects_changes(self):
        root = _make_repo()
        rc = run(["generate", str(root), "--quiet"])
        self.assertEqual(rc, 0)
        out = root / "reposage-out"
        first = (out / "reposage.md").read_text(encoding="utf-8")
        (root / "app.py").write_text(
            'from flask import Flask\napp = Flask(__name__)\n\n@app.route("/api/goodbye")\ndef bye():\n    pass\n',
            encoding="utf-8",
        )
        rc = run(["update", str(root), "--quiet"])
        self.assertEqual(rc, 0)
        second = (out / "reposage.md").read_text(encoding="utf-8")
        self.assertIn("/api/goodbye", second)
        self.assertNotIn("/api/hello", second)
        self.assertNotEqual(first, second)
        before = (out / "reposage.md").stat().st_mtime_ns
        rc = run(["update", str(root), "--quiet"])
        self.assertEqual(rc, 0)
        self.assertEqual((out / "reposage.md").stat().st_mtime_ns, before)

    def test_check_fails_on_secret(self):
        root = _make_repo()
        (root / "config.py").write_text('aws_key = "AKIAIOSFODNN7EXAMPLE"\n', encoding="utf-8")
        rc = run(["check", str(root), "--quiet"])
        self.assertEqual(rc, 1)
        rc = run(["check", str(root), "--quiet"])
        self.assertEqual(rc, 1)

    def test_check_passes_clean(self):
        root = _make_repo()
        rc = run(["check", str(root), "--quiet"])
        self.assertEqual(rc, 0)

    def test_brief(self):
        import contextlib
        import io
        root = _make_repo()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run(["brief", str(root)])
        self.assertEqual(rc, 0)
        self.assertIn("/api/hello", buf.getvalue())

    def test_init(self):
        root = _make_repo()
        rc = run(["init", str(root), "--force"])
        self.assertEqual(rc, 0)
        self.assertTrue((root / ".reposage.toml").is_file())

    def test_prompt(self):
        import contextlib
        import io
        root = _make_repo()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run(["prompt", str(root), "--quiet"])
        self.assertEqual(rc, 0)
        self.assertIn("<repository_context>", buf.getvalue())
        self.assertIn("/api/hello", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
