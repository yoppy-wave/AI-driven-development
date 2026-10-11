"""Tests for immutable PR preview cleanup locators."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preview_cleanup  # noqa: E402


SHA_A = "a" * 40
SHA_B = "b" * 40


class PreviewCleanupTests(unittest.TestCase):
    def values(self, pull_request: int = 42, **overrides: str) -> dict[str, str]:
        values = {
            "work_directory": "examples/cloudflare-worker/infra",
            "project_name": "example-worker",
            "stack_name": f"example-worker-pr-{pull_request}",
            "worker_name": f"example-worker-pr-{pull_request}",
            "backend_url": "https://api.pulumi.com",
            "source_ref": SHA_A,
            "status": "pending",
        }
        values.update(overrides)
        return preview_cleanup.metadata(pull_request, **values)

    def comment(self, values: dict[str, str], comment_id: int = 1, login: str = preview_cleanup.BOT_LOGIN) -> dict[str, object]:
        return {"id": comment_id, "body": preview_cleanup.comment_body(values), "user": {"login": login}}

    def test_pending_update_reuses_one_locator_for_partial_state_cleanup(self) -> None:
        active_a = self.values(status="active")
        pending_b = self.values(source_ref=SHA_B, status="pending")
        self.assertEqual(preview_cleanup.latest_target([self.comment(active_a, 10), self.comment(pending_b, 10)], 42), {**pending_b, "comment_id": "10"})

    def test_destroyed_locator_is_not_selected(self) -> None:
        self.assertIsNone(preview_cleanup.latest_target([self.comment(self.values(status="destroyed"))], 42))

    def test_fixed_locator_fields_detect_stack_backend_worker_directory_and_project_drift(self) -> None:
        target = self.values(status="active")
        for field, changed in {
            "work_directory": "infra/other",
            "project_name": "other-project",
            "stack_name": "other-pr-42",
            "worker_name": "other-pr-42",
            "backend_url": "s3://other-state",
        }.items():
            with self.subTest(field=field):
                self.assertNotEqual(target[field], changed)

    def test_rejects_untrusted_or_invalid_metadata(self) -> None:
        valid = self.values()
        attacker = self.comment(valid, login="contributor")
        invalid = {"id": 2, "body": preview_cleanup.MARKER + json.dumps({**valid, "status": "unknown"}) + " -->", "user": {"login": preview_cleanup.BOT_LOGIN}}
        self.assertIsNone(preview_cleanup.latest_target([attacker, invalid], 42))

    def test_requires_project_name_sha_and_status(self) -> None:
        with self.assertRaisesRegex(ValueError, "project_name"):
            self.values(project_name="")
        with self.assertRaisesRegex(ValueError, "full commit SHA"):
            self.values(source_ref="main")
        with self.assertRaisesRegex(ValueError, "status must be one of"):
            self.values(status="unknown")

    def test_legacy_locator_is_a_cleanup_candidate_but_fails_new_update_drift_validation(self) -> None:
        legacy = self.values()
        legacy.pop("project_name")
        legacy.pop("status")
        comments = [{"id": 7, "body": preview_cleanup.MARKER + json.dumps(legacy) + " -->", "user": {"login": preview_cleanup.BOT_LOGIN}}]
        target = preview_cleanup.latest_target(comments, 42)
        self.assertEqual(target["project_name"], "legacy-project")
        self.assertEqual(target["status"], "pending")
        completed = subprocess.run(
            [sys.executable, str(Path(preview_cleanup.__file__)), "github-output", "--pull-request", "42"],
            input=json.dumps([comments]),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(
            completed.stdout.splitlines(),
            [
                "found=true",
                "work_directory=examples/cloudflare-worker/infra",
                "project_name=legacy-project",
                "stack_name=example-worker-pr-42",
                "worker_name=example-worker-pr-42",
                "backend_url=https://api.pulumi.com",
                f"source_ref={SHA_A}",
                "status=pending",
                "comment_id=7",
            ],
        )

    def test_flattens_paginated_comment_responses(self) -> None:
        values = self.values()
        self.assertEqual(preview_cleanup.comment_pages([[self.comment(values)], []]), [self.comment(values)])


if __name__ == "__main__":
    unittest.main()
