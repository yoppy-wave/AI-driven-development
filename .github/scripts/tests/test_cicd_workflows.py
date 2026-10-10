"""The reusable CI/CD workflow contract must stay connected to its entrypoints."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(path: str) -> str:
    return (WORKFLOWS / path).read_text(encoding="utf-8")


class CicdWorkflowTests(unittest.TestCase):
    def test_reusable_workflows_are_in_the_supported_directory(self) -> None:
        for name in ("reusable-ci.yml", "reusable-cloudflare-worker.yml"):
            self.assertTrue((WORKFLOWS / name).is_file())
            self.assertIn("workflow_call:", workflow(name))

    def test_entrypoint_calls_the_reusable_workflows(self) -> None:
        content = workflow("cicd.yml")
        self.assertIn("uses: ./.github/workflows/reusable-ci.yml", content)
        for name in ("preview", "preview-environment", "deploy-development", "deploy-staging", "deploy-production"):
            self.assertIn(f"  {name}:\n", content)
        self.assertEqual(content.count("uses: ./.github/workflows/reusable-cloudflare-worker.yml"), 5)

    def test_cleanup_can_only_call_destroy_with_stack_removal(self) -> None:
        content = workflow("cicd-preview-cleanup.yml")
        self.assertIn("uses: ./.github/workflows/reusable-cloudflare-worker.yml", content)
        self.assertIn("operation: destroy", content)
        self.assertIn("remove-stack: true", content)

    def test_untrusted_pull_requests_cannot_create_preview_environments(self) -> None:
        content = workflow("cicd.yml")
        self.assertEqual(content.count("head.repo.fork == false"), 2)
        self.assertIn("github-environment: preview", content)

    def test_cloudflare_deployments_run_a_smoke_test(self) -> None:
        content = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("curl --fail --retry 5", content)
        self.assertIn("workers.dev", content)

    def test_cloudflare_adapter_uses_the_repository_pulumi_version_file(self) -> None:
        self.assertIn(
            "pulumi-version-file: ${{ github.workspace }}/.pulumi.version",
            workflow("reusable-cloudflare-worker.yml"),
        )


if __name__ == "__main__":
    unittest.main()