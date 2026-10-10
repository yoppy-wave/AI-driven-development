"""Tests for the CI/CD configuration contract."""

import json
import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import cicd_config  # noqa: E402


class CicdConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[3])
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config_path = self.root / ".github" / "cicd" / "application.json"

    def write(self, config: dict[str, object], with_project: bool = False) -> None:
        self.config_path.parent.mkdir(parents=True)
        self.config_path.write_text(json.dumps(config), encoding="utf-8")
        if with_project:
            project = self.root / "examples" / "infra"
            project.mkdir(parents=True)
            (project / "Pulumi.yaml").write_text("name: example\nruntime: nodejs\n", encoding="utf-8")

    def valid(self) -> dict[str, object]:
        return {
            "version": 1,
            "application": {"name": "example", "workerPrefix": "example"},
            "ci": {"enabled": True},
            "pulumi": {
                "enabled": False,
                "workDirectory": "examples/infra",
                "backendUrl": "",
                "stackPrefix": "example",
                "previewEnvironmentEnabled": False,
            },
            "deployments": {"development": False, "staging": False, "production": False},
        }

    def test_disabled_infrastructure_is_valid_without_a_pulumi_project(self) -> None:
        self.write(self.valid())
        self.assertEqual(cicd_config.load(self.config_path)["version"], 1)

    def test_preview_requires_pulumi(self) -> None:
        config = self.valid()
        config["pulumi"]["previewEnvironmentEnabled"] = True
        self.write(config)
        with self.assertRaisesRegex(ValueError, "requires pulumi.enabled"):
            cicd_config.load(self.config_path)

    def test_enabled_deployment_requires_pulumi(self) -> None:
        config = self.valid()
        config["deployments"]["development"] = True
        self.write(config)
        with self.assertRaisesRegex(ValueError, "enabled deployments require"):
            cicd_config.load(self.config_path)

    def test_enabled_pulumi_requires_project_manifest(self) -> None:
        config = self.valid()
        config["pulumi"]["enabled"] = True
        self.write(config)
        with self.assertRaisesRegex(ValueError, "must contain Pulumi.yaml"):
            cicd_config.load(self.config_path)

    def test_preview_names_are_scoped_to_pull_request(self) -> None:
        config = self.valid()
        output = cicd_config.values(config, 42)
        self.assertEqual(output["preview_stack"], "example-pr-42")
        self.assertEqual(output["preview_worker_name"], "example-pr-42")


if __name__ == "__main__":
    unittest.main()