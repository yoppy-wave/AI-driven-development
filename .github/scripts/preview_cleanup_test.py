"""Tests for immutable, stateful AWS PR preview cleanup records."""

import unittest

import preview_cleanup

SHA_A = "a" * 40
SHA_B = "b" * 40


class PreviewCleanupTests(unittest.TestCase):
    def values(self, pull_request: int = 42, **overrides: str) -> dict[str, str]:
        values = {"stack_name": f"app-pr-{pull_request}", "region": "us-east-1", "source_ref": SHA_A, "workflow_ref": SHA_B, "account_id": "123456789012", "status": "pending"}
        values.update(overrides)
        return preview_cleanup.metadata(pull_request, **values)

    def comment(self, values: dict[str, str], comment_id: int = 1, login: str = preview_cleanup.BOT_LOGIN) -> dict[str, object]:
        return {"id": comment_id, "body": preview_cleanup.comment_body(values), "user": {"login": login}}

    def test_new_pending_record_prevents_cleanup_of_an_old_active_preview(self) -> None:
        old = self.values(status="active")
        current = self.values(source_ref=SHA_B, status="pending")
        self.assertEqual(preview_cleanup.latest_target([self.comment(old), self.comment(current, 2)], 42), {**current, "comment_id": "2"})

    def test_destroyed_record_is_not_selected(self) -> None:
        self.assertIsNone(preview_cleanup.latest_target([self.comment(self.values(status="destroyed"))], 42))

    def test_latest_destroyed_record_prevents_reusing_a_previous_active_target(self) -> None:
        active = self.values(status="active")
        destroyed = self.values(source_ref=SHA_B, status="destroyed")
        self.assertIsNone(preview_cleanup.latest_target([self.comment(active), self.comment(destroyed, 2)], 42))

    def test_latest_record_supports_cleanup_retry_after_a_failed_destroy(self) -> None:
        destroying = self.values(status="destroying")
        self.assertEqual(
            preview_cleanup.latest_target([self.comment(destroying, 3)], 42),
            {**destroying, "comment_id": "3"},
        )

    def test_latest_pending_record_is_selected_after_a_redeployment(self) -> None:
        active = self.values(status="active")
        pending = self.values(source_ref=SHA_B, status="pending")
        self.assertEqual(
            preview_cleanup.latest_target([self.comment(active), self.comment(pending, 4)], 42),
            {**pending, "comment_id": "4"},
        )

    def test_rejects_untrusted_wrong_stack_or_invalid_account_metadata(self) -> None:
        self.assertIsNone(preview_cleanup.latest_target([self.comment(self.values(), login="contributor")], 42))
        with self.assertRaisesRegex(ValueError, "exactly match"):
            self.values(stack_name="app-development")
        with self.assertRaisesRegex(ValueError, "12-digit"):
            self.values(account_id="123")

    def test_requires_immutable_source_and_trusted_workflow_revisions(self) -> None:
        with self.assertRaisesRegex(ValueError, "source_ref"):
            self.values(source_ref="main")
        with self.assertRaisesRegex(ValueError, "workflow_ref"):
            self.values(workflow_ref="main")

    def test_flattens_paginated_comment_responses(self) -> None:
        values = self.values()
        self.assertEqual(preview_cleanup.comment_pages([[self.comment(values)], []]), [self.comment(values)])