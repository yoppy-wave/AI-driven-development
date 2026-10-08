"""Check Cline's local Codex login without printing credential or model output."""

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


PROMPT = (
    "次のREADME本文を読み、プロジェクトの目的を日本語で3行に要約してください。"
    "ファイル変更、コマンド実行、外部サイト参照は不要です。\n\n"
)


def inspect() -> None:
    settings = Path(os.environ.get("CLINE_DATA_DIR", Path.home() / ".cline" / "data"))
    path = Path(os.environ.get("CLINE_PROVIDER_SETTINGS_PATH", settings / "settings" / "providers.json"))
    if not path.is_file():
        print("cline_settings=absent")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    providers = data.get("providers", {})
    entry = providers.get("openai-codex", {}) if isinstance(providers, dict) else {}
    provider_settings = entry.get("settings", entry) if isinstance(entry, dict) else {}
    auth = provider_settings.get("auth", {}) if isinstance(provider_settings, dict) else {}
    if not isinstance(auth, dict):
        auth = {}
    print("cline_settings=present")
    print(f"openai_codex_provider={'present' if entry else 'absent'}")
    print(f"access_token={'present' if auth.get('accessToken') else 'absent'}")
    print(f"refresh_token={'present' if auth.get('refreshToken') else 'absent'}")
    print(f"expiry_metadata={'present' if auth.get('expiresAt') else 'absent'}")


def run(cli: str, readme: Path) -> None:
    if not readme.is_file():
        raise SystemExit("README not found")
    if not shutil.which(cli) and not Path(cli).is_file():
        raise SystemExit("Cline CLI not found")

    env = os.environ.copy()
    for name in ("OPENAI_API_KEY", "CLINE_API_KEY", "AZURE_OPENAI_API_KEY"):
        env.pop(name, None)

    with tempfile.TemporaryDirectory(prefix="cline-poc-") as directory:
        try:
            result = subprocess.run(
                [
                    cli,
                    "--provider",
                    "openai-codex",
                    "--json",
                    "--auto-approve",
                    "false",
                    PROMPT + readme.read_text(encoding="utf-8"),
                ],
                cwd=directory,
                env=env,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise SystemExit("Cline did not finish within five minutes; raw output was suppressed") from None

    event_count = 0
    has_response = False
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        event_count += 1
        if event.get("type") == "agent_event" and isinstance(event.get("event"), dict):
            has_response |= bool(event["event"].get("text"))
        elif event.get("type") == "say":
            has_response |= bool(event.get("text"))

    passed = result.returncode == 0 and event_count > 0 and has_response
    print(f"process_exit_success={str(result.returncode == 0).lower()}")
    print(f"json_event_count={event_count}")
    print(f"response_text_present={str(has_response).lower()}")
    if not passed:
        print("The run was not verified; raw CLI output was intentionally suppressed.")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "run"))
    parser.add_argument("--cli", default="cline")
    parser.add_argument("--readme", type=Path, default=Path("README.md"))
    args = parser.parse_args()
    if args.action == "inspect":
        inspect()
    else:
        run(args.cli, args.readme)


if __name__ == "__main__":
    main()
