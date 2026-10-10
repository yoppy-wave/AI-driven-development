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
        self.assertIn("Recover recorded preview cleanup target", content)
        self.assertNotIn("preview-enabled", content)
        self.assertNotIn("cicd_config.py", content)

    def test_preview_and_up_for_the_same_stack_are_serialized(self) -> None:
        content = workflow("cicd.yml")
        self.assertIn("needs: [ci, preview]", content)
        self.assertIn("group: cicd-${{ github.event.pull_request.number || github.ref }}", content)
        self.assertIn("cancel-in-progress: true", content)

    def test_untrusted_pull_requests_cannot_create_preview_environments(self) -> None:
        content = workflow("cicd.yml")
        self.assertEqual(content.count("head.repo.fork == false"), 2)
        self.assertEqual(
            content.count("contains(fromJSON('[\"OWNER\",\"MEMBER\",\"COLLABORATOR\"]'), github.event.pull_request.author_association)"),
            2,
        )
        self.assertIn("github-environment: preview", content)
        self.assertNotIn("secrets: inherit", content)

    def test_cloud_provider_secrets_are_limited_to_github_environments(self) -> None:
        content = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("environment: ${{ inputs.github-environment }}", content)
        self.assertNotIn("secrets:", content)
        self.assertIn("permissions:\n  contents: read\n  issues: write\n  pull-requests: write", content)

    def test_cleanup_uses_the_immutable_preview_source_revision(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        adapter = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("source-ref: ${{ needs.cleanup-target.outputs.source-ref }}", cleanup)
        self.assertIn("ref: ${{ inputs.source-ref || github.sha }}", adapter)
        self.assertIn("source-ref: ${{ github.event.pull_request.head.sha }}", workflow("cicd.yml"))
        self.assertIn("--source-ref '${{ inputs.source-ref }}'", adapter)

    def test_cleanup_target_is_recorded_before_pulumi_can_create_resources(self) -> None:
        content = workflow("reusable-cloudflare-worker.yml")
        self.assertLess(content.index("Record preview cleanup target"), content.index("Run Pulumi ${{ inputs.operation }}"))

    def test_cleanup_reads_all_comment_pages(self) -> None:
        self.assertIn("gh api --paginate --slurp", workflow("cicd-preview-cleanup.yml"))

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