"""Regression checks for ai_question helpers."""

import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import ai_question


class AiQuestionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2])
        self.addCleanup(self.temp.cleanup)
        self.temp_path = Path(self.temp.name)
        self.environment = patch.dict(
            os.environ,
            {
                "RUNNER_TEMP": self.temp.name,
                "GITHUB_WORKSPACE": self.temp.name,
                "ISSUE_TITLE": "境界値を確認",
                "ISSUE_BODY": "0件の場合は？",
                "GITHUB_SHA": "abc123",
                "OPENAI_API_KEY": "test-secret-token",
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_events(self, text: str, reason: str = "completed") -> None:
        events = [
            {"type": "agent_event", "event": {"type": "content_end", "text": "途中経過"}},
            {"type": "agent_event", "event": {"type": "done", "reason": reason, "text": text}},
            {"type": "run_result", "finishReason": reason, "text": text},
        ]
        (self.temp_path / "ai-question-events.ndjson").write_text(
            "\n".join(json.dumps(event, ensure_ascii=False) for event in events),
            encoding="utf-8",
        )

    def test_prepare_passes_issue_and_extract_formats_answer(self) -> None:
        ai_question.prepare()
        prompt = (self.temp_path / "ai-question-prompt.txt").read_text(encoding="utf-8")
        self.assertEqual(
            json.loads(prompt[prompt.index("{") :]),
            {"title": "境界値を確認", "body": "0件の場合は？"},
        )
        self.write_events("README.md:1 を確認しました。")
        ai_question.extract()
        answer = (self.temp_path / "ai-question-answer.md").read_text(encoding="utf-8")
        self.assertIn("README.md:1", answer)
        self.assertNotIn("途中経過", answer)
        self.assertIn("`abc123`", answer)

    def test_extract_rejects_token_in_answer(self) -> None:
        self.write_events("test-secret-token")
        with self.assertRaises(SystemExit):
            ai_question.extract()
        self.assertFalse((self.temp_path / "ai-question-answer.md").exists())

    def test_extract_rejects_incomplete_run(self) -> None:
        self.write_events("下書き", reason="error")
        with self.assertRaises(SystemExit):
            ai_question.extract()
        self.assertFalse((self.temp_path / "ai-question-answer.md").exists())

    def test_guard_tool_blocks_commands_and_outside_reads(self) -> None:
        for event in (
            {"preToolUse": {"toolName": "execute_command", "parameters": {"command": "pwd"}}},
            {"preToolUse": {"toolName": "read_files", "parameters": {"files": [{"path": "/etc/passwd"}]}}},
        ):
            with self.subTest(event=event), patch("sys.stdin", io.StringIO(json.dumps(event))), patch(
                "sys.stdout", new_callable=io.StringIO
            ) as output:
                ai_question.guard_tool()
                self.assertTrue(json.loads(output.getvalue())["cancel"])

    def test_guard_tool_allows_repository_read(self) -> None:
        source = self.temp_path / "README.md"
        source.write_text("test", encoding="utf-8")
        event = {"preToolUse": {"toolName": "read_files", "parameters": {"files": [{"path": str(source)}]}}}
        with patch("sys.stdin", io.StringIO(json.dumps(event))), patch(
            "sys.stdout", new_callable=io.StringIO
        ) as output:
            ai_question.guard_tool()
            self.assertFalse(json.loads(output.getvalue())["cancel"])


if __name__ == "__main__":
    unittest.main()