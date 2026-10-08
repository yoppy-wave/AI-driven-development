"""Regression checks for the issue workflow helpers."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ai_coding  # noqa: E402
import ai_question  # noqa: E402


class IssueWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.environment = patch.dict(
            os.environ,
            {
                "RUNNER_TEMP": self.temp.name,
                "ISSUE_NUMBER": "42",
                "ISSUE_TITLE": "境界値を確認",
                "ISSUE_BODY": "0件の場合は？",
                "GITHUB_SHA": "abc123",
                "COPILOT_GITHUB_TOKEN": "test-secret-token",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def test_question_passes_issue_and_formats_answer(self) -> None:
        ai_question.prepare()
        prompt = (self.temp_path / "ai-question-prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(
            json.loads(prompt[prompt.index("{") :]),
            {"title": "境界値を確認", "body": "0件の場合は？"},
        )

        (self.temp_path / "ai-question-output.txt").write_text(
            "README.md:1 を確認しました。\n", encoding="utf-8"
        )
        ai_question.extract()
        answer = (self.temp_path / "ai-question-answer.md").read_text(encoding="utf-8")
        self.assertIn("README.md:1", answer)
        self.assertIn("`abc123`", answer)

    def test_question_rejects_token_in_answer(self) -> None:
        (self.temp_path / "ai-question-output.txt").write_text(
            "test-secret-token", encoding="utf-8"
        )
        with self.assertRaises(SystemExit):
            ai_question.extract()
        self.assertFalse((self.temp_path / "ai-question-answer.md").exists())

    def test_coding_rejects_github_configuration_changes(self) -> None:
        (self.temp_path / "ai-coding-output.txt").write_text(
            "変更内容: 実装しました。", encoding="utf-8"
        )
        with patch.object(
            ai_coding, "changed_paths", return_value=[Path(".github/workflows/ai-coding.yml")]
        ):
            with self.assertRaises(SystemExit):
                ai_coding.extract()
        self.assertFalse((self.temp_path / "ai-coding-pr-body.md").exists())

    def test_coding_rejects_token_in_summary(self) -> None:
        (self.temp_path / "ai-coding-output.txt").write_text(
            "test-secret-token", encoding="utf-8"
        )
        with self.assertRaises(SystemExit):
            ai_coding.extract()
        self.assertFalse((self.temp_path / "ai-coding-pr-body.md").exists())

    def test_coding_creates_reviewable_pr_body(self) -> None:
        ai_coding.prepare()
        prompt = (self.temp_path / "ai-coding-prompt.txt").read_text(encoding="utf-8")
        self.assertIn('"number": "42"', prompt)

        (self.temp_path / "ai-coding-output.txt").write_text(
            "変更内容: 境界値を修正。\n確認: テスト成功。", encoding="utf-8"
        )
        with patch.object(ai_coding, "changed_paths", return_value=[]):
            ai_coding.extract()
        body = (self.temp_path / "ai-coding-pr-body.md").read_text(encoding="utf-8")
        self.assertIn("対象issue: #42", body)
        self.assertIn("確認: テスト成功。", body)


if __name__ == "__main__":
    unittest.main()
