"""The reusable CI/CD workflow contract must stay connected to its entrypoints."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(path: str) -> str:
    return (WORKFLOWS / path).read_text(encoding="utf-8")


class CicdWorkflowTests(unittest.TestCase):
    def test_reusable_workflows_are_supported_and_entrypoint_uses_them(self) -> None:
        for name in ("reusable-ci.yml", "reusable-cloudflare-worker.yml"):
            self.assertIn("workflow_call:", workflow(name))
        content = workflow("cicd.yml")
        self.assertIn("uses: ./.github/workflows/reusable-ci.yml", content)
        self.assertEqual(content.count("uses: ./.github/workflows/reusable-cloudflare-worker.yml"), 5)

    def test_preview_updates_one_stack_without_destroying_on_push(self) -> None:
        content = workflow("cicd.yml")
        adapter = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("  preview-locator:\n", content)
        self.assertNotIn("cleanup-previous-preview", content)
        self.assertNotIn("operation: destroy", content)
        preview = content[content.index("  preview:\n") : content.index("  preview-environment:\n")]
        up = content[content.index("  preview-environment:\n") : content.index("  deploy-development:\n")]
        self.assertIn("record-preview-cleanup: true", preview)
        self.assertIn("cleanup-comment-id: ${{ needs.preview-locator.outputs.comment-id }}", preview)
        self.assertIn("record-preview-cleanup: true", up)
        self.assertIn("cleanup-comment-id: ${{ needs.preview.outputs.cleanup-comment-id }}", up)
        self.assertIn("cleanup-comment-id:", adapter)
        self.assertIn("value: ${{ jobs.pulumi.outputs.cleanup-comment-id }}", adapter)
        self.assertIn("cleanup-comment-id: ${{ steps.cleanup-target.outputs.cleanup-comment-id }}", adapter)
        self.assertIn(
            "inputs.record-preview-cleanup && inputs.operation != 'preview' && inputs.operation != 'up'",
            adapter,
        )

    def test_update_and_close_cleanup_share_a_queued_pr_lock(self) -> None:
        for content in (workflow("cicd.yml"), workflow("cicd-preview-cleanup.yml")):
            self.assertIn("group: preview-${{ github.event.pull_request.number", content)
            self.assertIn("queue: max", content)
            self.assertIn("cancel-in-progress: false", content)

    def test_cleanup_can_only_destroy_and_remains_independent_of_preview_configuration(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        self.assertIn("uses: ./.github/workflows/reusable-cloudflare-worker.yml", cleanup)
        self.assertIn("operation: destroy", cleanup)
        self.assertIn("remove-stack: true", cleanup)
        self.assertIn("Recover recorded preview cleanup target", cleanup)
        self.assertNotIn("cicd_config.py", cleanup)
        self.assertNotIn("preview-environment-enabled", cleanup)

    def test_workflow_preserves_environment_secret_boundaries(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        entrypoint = workflow("cicd.yml")
        cleanup = workflow("cicd-preview-cleanup.yml")
        secrets = (
            "PULUMI_ACCESS_TOKEN",
            "PULUMI_CONFIG_PASSPHRASE",
            "CLOUDFLARE_API_TOKEN",
            "CLOUDFLARE_ACCOUNT_ID",
            "CLOUDFLARE_WORKERS_DEV_SUBDOMAIN",
        )
        self.assertIn("environment:\n      name: ${{ inputs.github-environment }}", adapter)
        self.assertIn("permissions:\n  contents: read\n  issues: write\n  pull-requests: write", adapter)
        self.assertNotIn("secrets: inherit", entrypoint)
        self.assertNotIn("secrets: inherit", cleanup)
        for secret in secrets:
            self.assertIn(f"      {secret}:", adapter)
            self.assertIn(f"      {secret}: ${{{{ secrets.{secret} }}}}", entrypoint)
            self.assertIn(f"      {secret}: ${{{{ secrets.{secret} }}}}", cleanup)
        for environment in ("preview", "development", "staging", "production"):
            self.assertIn(f"github-environment: {environment}", entrypoint)

    def test_stale_update_and_reopened_close_are_skipped_before_pulumi(self) -> None:
        content = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("Confirm pull request still permits this operation", content)
        self.assertIn(".head.sha", content)
        self.assertIn("PREVIEW_OPERATION_ALLOWED=false", content)
        self.assertIn("expected-pr-state: open", workflow("cicd.yml"))
        self.assertIn("expected-pr-state: closed", workflow("cicd-preview-cleanup.yml"))

    def test_reconfirmation_is_immediately_before_pulumi_and_guards_all_completion_steps(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        reconfirm = adapter.index("Reconfirm pull request immediately before Pulumi")
        pulumi = adapter.index("Run Pulumi ${{ inputs.operation }}")
        smoke = adapter.index("Smoke test deployed Worker")
        completion = adapter.index("Mark cleanup locator complete")
        self.assertLess(reconfirm, pulumi)
        self.assertLess(pulumi, smoke)
        self.assertLess(smoke, completion)
        guarded = "if: env.PREVIEW_OPERATION_ALLOWED != 'false'"
        for start, end in ((pulumi, smoke), (smoke, completion), (completion, len(adapter))):
            self.assertIn(guarded, adapter[start:end])
        self.assertIn("if: env.PREVIEW_OPERATION_ALLOWED == 'false'", adapter)

    def test_locator_validates_all_fixed_configuration_including_project_name(self) -> None:
        content = workflow("cicd.yml")
        self.assertIn("--project-name '${{ needs.ci.outputs.pulumi-project-name }}'", content)
        self.assertIn("project-name: ${{ needs.ci.outputs.pulumi-project-name }}", content)
        self.assertIn("pulumi-project-name", workflow("reusable-ci.yml"))

    def test_destroy_uses_locator_revision_but_skips_node_dependency_installation(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        cleanup = workflow("cicd-preview-cleanup.yml")
        self.assertIn("source-ref: ${{ needs.cleanup-target.outputs.source-ref }}", cleanup)
        self.assertIn("ref: ${{ inputs.source-ref || github.sha }}", adapter)
        self.assertIn("inputs.operation != 'destroy'", adapter)
        self.assertIn("CLOUDFLARE_API_TOKEN", adapter)
        self.assertIn("required+=(CLOUDFLARE_ACCOUNT_ID CLOUDFLARE_WORKERS_DEV_SUBDOMAIN)", adapter)

    def test_cleanup_marks_locator_destroyed_only_after_destroy(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("CLEANUP_STATUS: ${{ inputs.record-preview-cleanup && 'active' || 'destroyed' }}", adapter)
        self.assertGreater(adapter.index("Mark cleanup locator complete"), adapter.index("Run Pulumi ${{ inputs.operation }}"))

    def test_preview_locator_stays_pending_until_up_and_smoke_test_succeed(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        record = adapter.index("Record pending preview cleanup target")
        pulumi = adapter.index("Run Pulumi ${{ inputs.operation }}")
        complete = adapter.index("Mark cleanup locator complete")
        self.assertLess(record, pulumi)
        self.assertLess(pulumi, complete)
        self.assertIn("inputs.operation == 'up' && inputs.record-preview-cleanup", adapter[complete : complete + 260])

    def test_legacy_locator_values_flow_from_close_recovery_to_destroy(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        for field in ("work-directory", "project-name", "stack-name", "worker-name", "source-ref"):
            self.assertIn(f"{field}: ${{{{ steps.target.outputs.{field.replace('-', '_')} }}}}", cleanup)
            self.assertIn(f"{field}: ${{{{ needs.cleanup-target.outputs.{field} }}}}", cleanup)
        self.assertIn("backend-url: ${{ steps.target.outputs.backend_url }}", cleanup)
        self.assertIn("cloud-url: ${{ needs.cleanup-target.outputs.backend-url }}", cleanup)

    def test_cleanup_reads_all_comment_pages_and_preserves_recording_order(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        adapter = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("gh api --paginate --slurp", cleanup)
        self.assertLess(adapter.index("Record pending preview cleanup target"), adapter.index("Run Pulumi ${{ inputs.operation }}"))

    def test_cloudflare_operations_keep_smoke_test_and_pulumi_version_contracts(self) -> None:
        adapter = workflow("reusable-cloudflare-worker.yml")
        self.assertIn("curl --fail --retry 5", adapter)
        self.assertIn("workers.dev", adapter)
        self.assertIn("pulumi-version-file: ${{ github.workspace }}/.pulumi.version", adapter)

    def test_untrusted_pull_requests_cannot_create_preview_environments(self) -> None:
        content = workflow("cicd.yml")
        self.assertEqual(content.count("head.repo.fork == false"), 2)
        self.assertIn("contains(fromJSON('[\"OWNER\",\"MEMBER\",\"COLLABORATOR\"]')", content)
        self.assertNotIn("secrets: inherit", content)


if __name__ == "__main__":
    unittest.main()
