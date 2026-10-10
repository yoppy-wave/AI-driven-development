"""Tests for immutable PR preview cleanup metadata."""

import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preview_cleanup  # noqa: E402


SHA = "a" * 40


class PreviewCleanupTests(unittest.TestCase):
    def values(self, pull_request: int = 42, **overrides: str) -> dict[str, str]:
        values = {
            "work_directory": "examples/cloudflare-worker/infra",
            "stack_name": f"example-worker-pr-{pull_request}",
            "worker_name": f"example-worker-pr-{pull_request}",
            "backend_url": "https://api.pulumi.com",
            "source_ref": SHA,
        }
        values.update(overrides)
        return preview_cleanup.metadata(pull_request, **values)

    def comment(self, values: dict[str, str], login: str = preview_cleanup.BOT_LOGIN) -> dict[str, object]:
        return {"body": preview_cleanup.comment_body(values), "user": {"login": login}}

    def test_records_a_complete_immutable_cleanup_target(self) -> None:
        values = self.values()
        self.assertEqual(
            preview_cleanup.latest_metadata([self.comment(values)], 42),
            values,
        )

    def test_uses_the_latest_valid_bot_record_after_configuration_changes(self) -> None:
        old = self.values(42, backend_url="https://old-backend.example")
        current = self.values(42, work_directory="infra/current", stack_name="current-pr-42", worker_name="current-pr-42")
        self.assertEqual(preview_cleanup.latest_metadata([self.comment(old), self.comment(current)], 42), current)

    def test_rejects_comment_injection_and_wrong_pr_targets(self) -> None:
        valid = self.values()
        attacker = self.comment(valid, login="contributor")
        wrong_pr = self.comment(self.values(43))
        traversal = {
            "body": preview_cleanup.MARKER
            + json.dumps({**valid, "work_directory": "../other", "stack_name": "example-worker-pr-42"})
            + " -->",
            "user": {"login": preview_cleanup.BOT_LOGIN},
        }
        self.assertIsNone(preview_cleanup.latest_metadata([attacker, wrong_pr, traversal], 42))

    def test_rejects_missing_or_non_immutable_source_revision(self) -> None:
        with self.assertRaisesRegex(ValueError, "full commit SHA"):
            self.values(source_ref="main")
        with self.assertRaisesRegex(ValueError, "full commit SHA"):
            preview_cleanup.metadata(42, "infra", "example-pr-42", "example-pr-42", "", None)

    def test_flattens_paginated_comment_responses(self) -> None:
        values = self.values()
        self.assertEqual(preview_cleanup.comment_pages([[self.comment(values)], []]), [self.comment(values)])


if __name__ == "__main__":
    unittest.main()