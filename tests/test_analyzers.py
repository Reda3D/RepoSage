import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from reposage.config import Config
from reposage.context import Context
from reposage.analyzers.dependencies import (
    parse_cargo, parse_gemfile, parse_gomod, parse_package_json,
    parse_pom, parse_pyproject, parse_requirements,
)
from reposage.analyzers.endpoints import EndpointsAnalyzer
from reposage.analyzers.security import SecurityAnalyzer
from reposage.analyzers.todos import TodosAnalyzer


@contextmanager
def _ctx():
    with tempfile.TemporaryDirectory() as tmp:
        yield Context(Path(tmp), Config(), None)


FLASK = '''
from flask import Flask
app = Flask(__name__)

@app.route("/api/users", methods=["GET"])
def users():
    pass

@app.route("/api/users/<int:uid>")
def user(uid):
    pass
'''

FASTAPI = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items")
@app.post("/items")
async def items():
    pass
'''

EXPRESS = '''
const express = require("express");
const app = express();

app.get("/api/ping", (req, res) => res.send("pong"));
app.post("/api/users", handler);
router.delete("/api/users/:id", handler);
'''

GO_GIN = '''
package main

func main() {
    r := gin.Default()
    r.GET("/health", health)
    r.POST("/api/upload", upload)
    http.HandleFunc("/legacy", legacy)
}
'''

SPRING = '''
@RestController
public class UserController {
    @GetMapping("/users")
    public List<User> list() { return null; }

    @PostMapping(value = "/users")
    public void create() {}
}
'''


class TestEndpoints(unittest.TestCase):
    def _findings(self, rel, text):
        with _ctx() as ctx:
            analyzer = EndpointsAnalyzer()
            return analyzer.analyze_file(rel, text, ctx)

    def test_flask(self):
        findings = self._findings("app.py", FLASK)
        paths = {f["path"] for f in findings}
        self.assertIn("/api/users", paths)
        self.assertIn("/api/users/<int:uid>", paths)
        self.assertTrue(all(f["framework"] == "flask" for f in findings))

    def test_fastapi(self):
        findings = self._findings("main.py", FASTAPI)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["method"], "GET")
        self.assertEqual(findings[1]["method"], "POST")

    def test_express(self):
        findings = self._findings("server.js", EXPRESS)
        paths = {f["path"] for f in findings}
        self.assertEqual(paths, {"/api/ping", "/api/users", "/api/users/:id"})

    def test_go(self):
        findings = self._findings("main.go", GO_GIN)
        paths = {f["path"] for f in findings}
        self.assertEqual(paths, {"/health", "/api/upload", "/legacy"})

    def test_spring(self):
        findings = self._findings("UserController.java", SPRING)
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["method"], "GET")

    def test_line_numbers(self):
        findings = self._findings("app.py", FLASK)
        self.assertEqual(findings[0]["line"], 5)


class TestDependencies(unittest.TestCase):
    def test_requirements(self):
        text = "# comment\nrequests==2.32.3\nflask>=3.0,<4\npytest\n-r other.txt\n"
        deps = parse_requirements(text)["dependencies"]
        self.assertEqual(deps["requests"], "==2.32.3")
        self.assertEqual(deps["flask"], ">=3.0,<4")
        self.assertEqual(deps["pytest"], "any")
        self.assertNotIn("other.txt", deps)

    def test_package_json(self):
        text = '{"dependencies": {"react": "^18.3.1"}, "devDependencies": {"jest": "^29"}, "scripts": {"test": "jest"}}'
        data = parse_package_json(text)
        self.assertEqual(data["dependencies"]["react"], "^18.3.1")
        self.assertEqual(data["scripts"]["test"], "jest")
        self.assertIsNone(parse_package_json("{not json"))

    def test_pyproject(self):
        text = '''
[project]
name = "demo"
dependencies = [
    "requests>=2.31",
    "typer",
]

[project.optional-dependencies]
dev = ["pytest"]

[project.scripts]
demo = "demo.cli:main"
'''
        data = parse_pyproject(text)
        self.assertIn("requests", data["dependencies"])
        self.assertIn("typer", data["dependencies"])
        self.assertEqual(data["optional"]["dev"], 1)
        self.assertEqual(data["scripts"]["demo"], "demo.cli:main")

    def test_gomod(self):
        text = "module example.com/app\n\ngo 1.22\n\nrequire (\n\tgithub.com/gin-gonic/gin v1.10.0\n\tgithub.com/stretchr/testify v1.9.0 // indirect\n)\n\nrequire golang.org/x/sync v0.7.0\n"
        deps = parse_gomod(text)
        self.assertEqual(deps["github.com/gin-gonic/gin"], "v1.10.0")
        self.assertEqual(deps["github.com/stretchr/testify"], "v1.9.0")
        self.assertEqual(deps["golang.org/x/sync"], "v0.7.0")

    def test_cargo(self):
        text = '[package]\nname = "demo"\n\n[dependencies]\nserde = "1.0"\ntokio = { version = "1.37", features = ["full"] }\n'
        deps = parse_cargo(text)
        self.assertEqual(deps["serde"], "1.0")
        self.assertEqual(deps["tokio"], "1.37")

    def test_gemfile(self):
        text = "source 'https://rubygems.org'\ngem 'rails', '~> 7.1'\ngem 'pg'\n"
        deps = parse_gemfile(text)
        self.assertEqual(deps["rails"], "~> 7.1")
        self.assertEqual(deps["pg"], "any")

    def test_pom(self):
        text = "<project><dependencies><dependency><groupId>org.x</groupId><artifactId>core</artifactId><version>1.2</version></dependency></dependencies></project>"
        deps = parse_pom(text)
        self.assertEqual(deps["org.x:core"], "1.2")


class TestSecurity(unittest.TestCase):
    def _findings(self, rel, text):
        with _ctx() as ctx:
            return SecurityAnalyzer().analyze_file(rel, text, ctx)

    def test_detects_aws_key(self):
        findings = self._findings("config.py", 'key = "AKIAIOSFODNN7EXAMPLE"')
        ids = {f["id"] for f in findings}
        self.assertIn("aws-access-key", ids)

    def test_skips_placeholders(self):
        findings = self._findings("config.py", 'api_key = "your_api_key_here"')
        ids = {f["id"] for f in findings}
        self.assertNotIn("hardcoded-secret", ids)

    def test_skips_env_lookup(self):
        findings = self._findings("config.py", 'password = os.environ["DB_PASSWORD"]')
        ids = {f["id"] for f in findings}
        self.assertNotIn("hardcoded-secret", ids)

    def test_detects_hardcoded_password(self):
        findings = self._findings("config.py", 'password = "SuperSecret123!"')
        ids = {f["id"] for f in findings}
        self.assertIn("hardcoded-secret", ids)

    def test_detects_risky_calls(self):
        findings = self._findings("run.py", "import subprocess\nsubprocess.run(cmd, shell=True)\n")
        ids = {f["id"] for f in findings}
        self.assertIn("shell-true", ids)

    def test_detects_env_file(self):
        findings = self._findings(".env", "DB_PASSWORD=abc\n")
        ids = {f["id"] for f in findings}
        self.assertIn("env-file", ids)


class TestTodos(unittest.TestCase):
    def test_todos(self):
        with _ctx() as ctx:
            analyzer = TodosAnalyzer()
            text = "def f():\n    pass  # TODO: implement this\n\n# FIXME broken\n"
            findings = analyzer.analyze_file("a.py", text, ctx)
            tags = {f["tag"] for f in findings}
            self.assertEqual(tags, {"TODO", "FIXME"})
            self.assertEqual(findings[0]["line"], 2)


if __name__ == "__main__":
    unittest.main()
