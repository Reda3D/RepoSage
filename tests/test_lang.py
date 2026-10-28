import unittest

from reposage.lang import classify, count_loc, is_code


class TestLang(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify("src/app.py"), "Python")
        self.assertEqual(classify("src/App.tsx"), "TypeScript (TSX)")
        self.assertEqual(classify("go.mod"), "Go")
        self.assertEqual(classify("README.md"), "Markdown")
        self.assertEqual(classify("Dockerfile"), "Dockerfile")
        self.assertEqual(classify("Makefile"), "Makefile")
        self.assertEqual(classify("unknown.xyz"), "")

    def test_count_loc(self):
        self.assertEqual(count_loc("a = 1\n\n\nb = 2\n"), 2)
        self.assertEqual(count_loc(""), 0)

    def test_is_code(self):
        self.assertTrue(is_code("src/main.py"))
        self.assertTrue(is_code("src/index.js"))
        self.assertFalse(is_code("package.json"))
        self.assertFalse(is_code("README.md"))


if __name__ == "__main__":
    unittest.main()
