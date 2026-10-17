#!/usr/bin/env python3
"""Run every registered project test suite on a pull request."""

import json
import os
import subprocess
import sys
import tomllib
from pathlib import Path


IGNORED_DIRS = {
    ".git", ".github", ".devcontainer", ".venv", "venv", "node_modules",
    "dist", "build", "obj", "coverage", ".next", "cdk.out", "__pycache__",
}


def repository_files(root: Path) -> list[Path]:
    found = []
    for directory, children, filenames in os.walk(root):
        children[:] = sorted(child for child in children if child not in IGNORED_DIRS)
        found.extend(Path(directory, name).relative_to(root) for name in filenames)
    return sorted(found)


def nearest_project(path: Path, projects: set[Path]) -> Path | None:
    for parent in (path.parent, *path.parents):
        if parent in projects:
            return parent
    return None


def test_file(path: Path) -> bool:
    return path.name.endswith("_test.py")


def discover(root: Path) -> tuple[list[Path], list[Path]]:
    files = repository_files(root)
    python_roots = {
        path.parent for path in files
        if path.name in {"pyproject.toml", "requirements.txt", "requirements-dev.txt"}
    }
    node_roots = {path.parent for path in files if path.name == "package.json"}
    # A workspace root owns its nested packages; its test script must test them all.
    node_roots = {
        path for path in node_roots
        if nearest_project(path / "package.json", node_roots - {path}) is None
    }
    for project in python_roots:
        if not any(test_file(path) and nearest_project(path, python_roots) == project for path in files):
            raise RuntimeError(f"Python project {project} has no *_test.py tests")
    for project in node_roots:
        package = json.loads((root / project / "package.json").read_text(encoding="utf-8"))
        if not isinstance(package.get("scripts", {}).get("test"), str):
            raise RuntimeError(f"Node project {project} has no test script")
    for path in files:
        if path.suffix == ".py" and nearest_project(path, python_roots) is None:
            raise RuntimeError(f"Python source {path} has no project manifest")
        if path.suffix in {".ts", ".tsx", ".mts", ".cts"} and nearest_project(path, node_roots) is None:
            raise RuntimeError(f"TypeScript source {path} has no package.json")
    return sorted(python_roots), sorted(node_roots)


def run(command: list[str], cwd: Path) -> None:
    print(f"::group::{cwd}: {' '.join(command)}", flush=True)
    try:
        subprocess.run(command, cwd=cwd, check=True)
    finally:
        print("::endgroup::", flush=True)


def python_project(root: Path, project: Path) -> None:
    directory = root / project
    pyproject = directory / "pyproject.toml"
    if pyproject.exists():
        config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if "project" in config or "build-system" in config:
            extras = config.get("project", {}).get("optional-dependencies", {})
            extra = next((name for name in ("test", "dev") if name in extras), None)
            target = f".[{extra}]" if extra else "."
            run([sys.executable, "-m", "pip", "install", "-e", target], directory)
    requirements = next((directory / name for name in ("requirements-dev.txt", "requirements.txt")
                         if (directory / name).exists()), None)
    if requirements:
        run([sys.executable, "-m", "pip", "install", "-r", requirements.name], directory)
    run([sys.executable, "-m", "pytest", "-q"], directory)


def node_project(root: Path, project: Path) -> None:
    directory = root / project
    package = json.loads((directory / "package.json").read_text(encoding="utf-8"))
    locks = [name for name in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock")
             if (directory / name).exists()]
    if len(locks) != 1:
        raise RuntimeError(f"Node project {project} needs exactly one supported lockfile")
    if locks[0] == "package-lock.json":
        manager = ["npm"]
        run(["npm", "ci"], directory)
    else:
        manager = ["corepack", "pnpm" if locks[0] == "pnpm-lock.yaml" else "yarn"]
        run([*manager, "install", "--frozen-lockfile" if manager[-1] == "pnpm" else "--immutable"], directory)
    for name in ("test", "lint", "typecheck", "build", "synth", "actionlint"):
        if name in package.get("scripts", {}):
            run([*manager, "run", name], directory)


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    python_roots, node_roots = discover(root)
    for project in python_roots:
        python_project(root, project)
    for project in node_roots:
        node_project(root, project)
    print("All discovered regression suites passed.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from None
