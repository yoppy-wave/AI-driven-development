"""The AWS CI/CD workflow contract must preserve preview safety boundaries."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def workflow(path: str) -> str:
    return (WORKFLOWS / path).read_text(encoding="utf-8")


class CicdWorkflowTests(unittest.TestCase):
    def test_reusable_workflows_are_supported_and_called(self) -> None:
        for name in ("reusable-ci.yml", "reusable-aws-cdk.yml"):
            self.assertIn("workflow_call:", workflow(name))
        self.assertEqual(workflow("cicd.yml").count("uses: ./.github/workflows/reusable-aws-cdk.yml"), 5)

    def test_update_and_close_cleanup_share_a_queued_pr_lock(self) -> None:
        for content in (workflow("cicd.yml"), workflow("cicd-preview-cleanup.yml")):
            self.assertIn("group: preview-${{ github.event.pull_request.number", content)
            self.assertIn("cancel-in-progress: false", content)
            self.assertNotIn("queue: max", content)

    def test_preview_requires_trusted_pr_and_environment_gate(self) -> None:
        content = workflow("cicd.yml")
        self.assertEqual(content.count("head.repo.fork == false"), 2)
        self.assertIn("contains(fromJSON('[\"OWNER\",\"MEMBER\",\"COLLABORATOR\"]')", content)
        self.assertIn("github-environment: preview", content)
        self.assertNotIn("secrets: inherit", content)

    def test_aws_oidc_is_limited_to_aws_operation_jobs(self) -> None:
        self.assertIn("id-token: write", workflow("reusable-aws-cdk.yml"))
        self.assertIn("permissions:\n      contents: read\n      id-token: write", workflow("cicd-preview-cleanup.yml"))

    def test_preview_comment_permissions_are_not_required_for_standard_deployments(self) -> None:
        adapter = workflow("reusable-aws-cdk.yml")
        self.assertNotIn("issues: write", adapter)
        self.assertNotIn("pull-requests: write", adapter)
        cicd = workflow("cicd.yml")
        self.assertEqual(cicd.count("issues: write"), 3)
        self.assertEqual(cicd.count("pull-requests: write"), 3)

    def test_preview_rechecks_pr_state_and_head_before_aws(self) -> None:
        adapter = workflow("reusable-aws-cdk.yml")
        self.assertEqual(adapter.count("Confirm pull request is current"), 2)
        self.assertLess(adapter.index("Confirm pull request is current before AWS operation"), adapter.index("Configure AWS credentials with OIDC"))

    def test_cleanup_never_checks_out_or_executes_pr_source(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        self.assertIn("ref: ${{ github.workflow_sha }}", cleanup)
        self.assertIn("ref: ${{ needs.cleanup-target.outputs.workflow-ref }}", cleanup)
        self.assertNotIn("npm ci", cleanup)
        self.assertNotIn("npm run cdk", cleanup)

    def test_cleanup_validates_cloudformation_identity_and_tags_before_delete(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        for required in ("aws sts get-caller-identity", "aws cloudformation describe-stacks", "app:managed-by", "app:preview-pr", "DELETE_IN_PROGRESS", "aws cloudformation delete-stack"):
            self.assertIn(required, cleanup)

    def test_cleanup_handles_reopened_pr_and_missing_stack_idempotently(self) -> None:
        cleanup = workflow("cicd-preview-cleanup.yml")
        for required in ("Confirm pull request remains closed", "does not exist", "exists=false", "status destroying", "status destroyed"):
            self.assertIn(required, cleanup)