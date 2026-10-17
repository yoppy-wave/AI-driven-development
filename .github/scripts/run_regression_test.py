"""Regression checks for run_regression helpers."""

import tempfile
import unittest
from pathlib import Path

import run_regression


class DiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            dir=Path(__file__).resolve().parents[2]
        )
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, path: str, content: str = "") -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def test_empty_repository_has_no_application_projects(self) -> None:
        self.assertEqual(run_regression.discover(self.root), ([], []))

    def test_python_project_requires_tests(self) -> None:
        self.write("backend/pyproject.toml", "[project]\nname = 'backend'\nversion = '0.1'\n")
        self.write("backend/src/backend.py", "def calculate(): return 1")
        with self.assertRaisesRegex(RuntimeError, r"has no \*_test\.py tests"):
            run_regression.discover(self.root)
        self.write("backend/src/backend_test.py", "def test_calculate(): assert True")
        self.assertEqual(run_regression.discover(self.root)[0], [Path("backend")])

    def test_unregistered_python_source_fails(self) -> None:
        self.write("app/feature.py", "def feature(): return True")
        with self.assertRaisesRegex(RuntimeError, "no project manifest"):
            run_regression.discover(self.root)

    def test_node_project_requires_test_script(self) -> None:
        self.write("web/package.json", '{"scripts":{"build":"tsc"}}')
        with self.assertRaisesRegex(RuntimeError, "no test script"):
            run_regression.discover(self.root)
        self.write("web/package.json", '{"scripts":{"test":"vitest run"}}')
        self.write("web/src/app.ts", "export const app = true")
        self.assertEqual(run_regression.discover(self.root)[1], [Path("web")])

    def test_nested_node_package_uses_root_workspace(self) -> None:
        self.write("package.json", '{"scripts":{"test":"npm -ws test"}}')
        self.write("packages/web/package.json", '{"scripts":{"test":"vitest run"}}')
        self.write("packages/web/src/app.ts", "export const app = true")
        self.assertEqual(run_regression.discover(self.root)[1], [Path(".")])


if __name__ == "__main__":
    unittest.main()