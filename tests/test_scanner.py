import tempfile
import unittest
from pathlib import Path

from reposage.config import Config
from reposage.scanner import IgnoreRules, scan


def _write(root: Path, rel: str, content: str = "x\n"):
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestIgnoreRules(unittest.TestCase):
    def _rules(self, root: Path, extra=None):
        config = Config()
        if extra:
            config.extra_ignore = extra
        return IgnoreRules(root, config, "reposage-out")

    def test_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = self._rules(root)
            self.assertTrue(rules.ignored("node_modules/foo.js", False))
            self.assertTrue(rules.ignored("a/b/node_modules", True))
            self.assertTrue(rules.ignored("a/b/__pycache__", True))
            self.assertTrue(rules.ignored("x.pyc", False))
            self.assertFalse(rules.ignored("src/main.py", False))

    def test_gitignore_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text(
                "build/\n*.log\n!important.log\n/docs/secret.txt\n", encoding="utf-8"
            )
            rules = self._rules(root)
            self.assertTrue(rules.ignored("build", True))
            self.assertTrue(rules.ignored("a/b/build", True))
            self.assertTrue(rules.ignored("debug.log", False))
            self.assertFalse(rules.ignored("important.log", False))
            self.assertTrue(rules.ignored("docs/secret.txt", False))
            self.assertFalse(rules.ignored("docs/other.txt", False))

    def test_extra_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rules = self._rules(root, extra=["generated/"])
            self.assertTrue(rules.ignored("generated", True))
            self.assertTrue(rules.ignored("generated/x.py", False))


class TestScan(unittest.TestCase):
    def test_scan_respects_ignores(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "src/main.py")
            _write(root, "src/util.py")
            _write(root, "node_modules/dep/index.js")
            _write(root, "build/output.bin")
            _write(root, "README.md")
            files, skipped, _ = scan(root, Config())
            rels = {rel for rel, _, _ in files}
            self.assertIn("src/main.py", rels)
            self.assertIn("README.md", rels)
            self.assertNotIn("node_modules/dep/index.js", rels)
            self.assertNotIn("build/output.bin", rels)
            self.assertEqual(skipped, 0)

    def test_scan_size_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "big.txt", "x" * 2048)
            _write(root, "small.txt", "x")
            config = Config()
            config.max_file_kb = 1
            files, skipped, _ = scan(root, config)
            rels = {rel for rel, _, _ in files}
            self.assertNotIn("big.txt", rels)
            self.assertIn("small.txt", rels)
            self.assertEqual(skipped, 1)

    def test_scan_max_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(10):
                _write(root, "f%d.py" % i)
            config = Config()
            config.max_files = 5
            files, skipped, _ = scan(root, config)
            self.assertEqual(len(files), 5)
            self.assertEqual(skipped, 1)


if __name__ == "__main__":
    unittest.main()
