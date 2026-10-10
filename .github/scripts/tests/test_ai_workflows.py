"""Regression checks for the issue workflow helpers."""

import io
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
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[3])
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.environment = patch.dict(
            os.environ,
            {
                "RUNNER_TEMP": self.temp.name,
                "GITHUB_WORKSPACE": self.temp.name,
                "ISSUE_NUMBER": "42",
                "ISSUE_TITLE": "境界値を確認",
                "ISSUE_BODY": "0件の場合は？",
                "GITHUB_SHA": "abc123",
                "OPENAI_API_KEY": "test-secret-token",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_events(self, workflow: str, text: str, reason: str = "completed") -> None:
        events = [
            {"type": "agent_event", "event": {"type": "content_end", "text": "途中経過"}},
            {"type": "agent_event", "event": {"type": "done", "reason": reason, "text": text}},
            {"type": "run_result", "finishReason": reason, "text": text},
        ]
        (self.temp_path / f"{workflow}-events.ndjson").write_text(
            "\n".join(json.dumps(event, ensure_ascii=False) for event in events),
            encoding="utf-8",
        )

    def test_question_passes_issue_and_formats_answer(self) -> None:
        ai_question.prepare()
        prompt = (self.temp_path / "ai-question-prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(
            json.loads(prompt[prompt.index("{") :]),
            {"title": "境界値を確認", "body": "0件の場合は？"},
        )
        self.write_events("ai-question", "README.md:1 を確認しました。")
        ai_question.extract()
        answer = (self.temp_path / "ai-question-answer.md").read_text(encoding="utf-8")
        self.assertIn("README.md:1", answer)
        self.assertNotIn("途中経過", answer)
        self.assertIn("`abc123`", answer)

    def test_question_rejects_token_in_answer(self) -> None:
        self.write_events("ai-question", "test-secret-token")
        with self.assertRaises(SystemExit):
            ai_question.extract()
        self.assertFalse((self.temp_path / "ai-question-answer.md").exists())

    def test_question_rejects_incomplete_run(self) -> None:
        self.write_events("ai-question", "下書き", reason="error")
        with self.assertRaises(SystemExit):
            ai_question.extract()
        self.assertFalse((self.temp_path / "ai-question-answer.md").exists())

    def test_hook_blocks_commands_and_outside_reads(self) -> None:
        for event in (
            {"preToolUse": {"toolName": "execute_command", "parameters": {"command": "pwd"}}},
            {"preToolUse": {"toolName": "read_files", "parameters": {"files": [{"path": "/etc/passwd"}]}}},
        ):
            with self.subTest(event=event), patch("sys.stdin", io.StringIO(json.dumps(event))), patch(
                "sys.stdout", new_callable=io.StringIO
            ) as output:
                ai_question.guard_tool()
                self.assertTrue(json.loads(output.getvalue())["cancel"])

    def test_hook_allows_repository_read(self) -> None:
        source = self.temp_path / "README.md"
        source.write_text("test", encoding="utf-8")
        event = {"preToolUse": {"toolName": "read_files", "parameters": {"files": [{"path": str(source)}]}}}
        with patch("sys.stdin", io.StringIO(json.dumps(event))), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ai_question.guard_tool()
            self.assertFalse(json.loads(output.getvalue())["cancel"])

    def test_coding_rejects_github_configuration_changes(self) -> None:
        self.write_events("ai-coding", "変更内容: 実装しました。")
        with patch.object(
            ai_coding, "changed_paths", return_value=[Path(".github/workflows/ai-coding.yml")]
        ):
            with self.assertRaises(SystemExit):
                ai_coding.extract()
        self.assertFalse((self.temp_path / "ai-coding-pr-body.md").exists())

    def test_coding_rejects_token_in_summary(self) -> None:
        self.write_events("ai-coding", "test-secret-token")
        with self.assertRaises(SystemExit):
            ai_coding.extract()
        self.assertFalse((self.temp_path / "ai-coding-pr-body.md").exists())

    def test_coding_creates_reviewable_pr_body(self) -> None:
        ai_coding.prepare()
        prompt = (self.temp_path / "ai-coding-prompt.txt").read_text(encoding="utf-8")
        self.assertIn('"number": "42"', prompt)
        self.assertIn("プルリクエスト本文へそのまま掲載", prompt)
        self.assertIn("日本語で記述してください", prompt)
        self.write_events("ai-coding", "変更内容: 境界値を修正。\n確認: テスト成功。")
        with patch.object(ai_coding, "changed_paths", return_value=[]):
            ai_coding.extract()
        body = (self.temp_path / "ai-coding-pr-body.md").read_text(encoding="utf-8")
        self.assertIn("対象issue: #42", body)
        self.assertIn("確認: テスト成功。", body)


if __name__ == "__main__":
    unittest.main()
