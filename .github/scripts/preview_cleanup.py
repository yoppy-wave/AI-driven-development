#!/usr/bin/env python3
"""Persist and recover immutable, stateful AWS preview cleanup records."""

import argparse
import json
import re
import sys
from typing import Any

MARKER = "<!-- cicd-preview-cleanup:v2 "
BOT_LOGIN = "github-actions[bot]"
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
ACCOUNT_ID_PATTERN = re.compile(r"^[0-9]{12}$")
STATUSES = ("pending", "active", "destroying", "destroyed")


def fail(message: str) -> None:
    raise ValueError(message)


def metadata(
    pull_request: int,
    stack_name: str,
    region: str,
    source_ref: str,
    workflow_ref: str,
    account_id: str = "",
    status: str = "pending",
) -> dict[str, str]:
    if pull_request < 1:
        fail("pull request number must be positive")
    if stack_name != f"app-pr-{pull_request}":
        fail("preview stack name must exactly match the pull request stack name")
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-[0-9]+", region):
        fail("region must be an AWS region identifier")
    for field, value in (("source_ref", source_ref), ("workflow_ref", workflow_ref)):
        if not isinstance(value, str) or not COMMIT_SHA_PATTERN.fullmatch(value):
            fail(f"{field} must be a full commit SHA")
    if account_id and not ACCOUNT_ID_PATTERN.fullmatch(account_id):
        fail("account_id must be a 12-digit AWS account ID when present")
    if status not in STATUSES:
        fail(f"status must be one of: {', '.join(STATUSES)}")
    return {
        "stack_name": stack_name,
        "region": region,
        "source_ref": source_ref,
        "workflow_ref": workflow_ref,
        "account_id": account_id,
        "status": status,
    }


def comment_body(values: dict[str, str]) -> str:
    return f"{MARKER}{json.dumps(values, separators=(',', ':'), sort_keys=True)} -->"


def metadata_from_comment(body: object, login: object, pull_request: int) -> dict[str, str] | None:
    if login != BOT_LOGIN or not isinstance(body, str) or not body.startswith(MARKER) or not body.endswith(" -->"):
        return None
    try:
        values = json.loads(body[len(MARKER) : -4])
    except json.JSONDecodeError:
        return None
    if not isinstance(values, dict):
        return None
    try:
        return metadata(
            pull_request,
            values.get("stack_name"),
            values.get("region"),
            values.get("source_ref"),
            values.get("workflow_ref"),
            values.get("account_id", ""),
            values.get("status", "pending"),
        )
    except ValueError:
        return None


def latest_target(comments: list[dict[str, Any]], pull_request: int) -> dict[str, str] | None:
    for comment in reversed(comments):
        values = metadata_from_comment(comment.get("body"), comment.get("user", {}).get("login"), pull_request)
        comment_id = comment.get("id")
        if values is not None and isinstance(comment_id, int):
            if values["status"] == "destroyed":
                return None
            return {**values, "comment_id": str(comment_id)}
    return None


def comment_pages(response: object) -> list[dict[str, Any]]:
    if not isinstance(response, list):
        fail("GitHub comments response must be an array")
    if all(isinstance(item, dict) for item in response):
        return response
    comments: list[dict[str, Any]] = []
    for page in response:
        if not isinstance(page, list) or not all(isinstance(item, dict) for item in page):
            fail("GitHub comment pages must be arrays of objects")
        comments.extend(page)
    return comments


def add_metadata_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument("--pull-request", required=True, type=int)
    command.add_argument("--stack-name", required=True)
    command.add_argument("--region", required=True)
    command.add_argument("--source-ref", required=True)
    command.add_argument("--workflow-ref", required=True)
    command.add_argument("--account-id", default="")
    command.add_argument("--status", required=True, choices=STATUSES)


def values_from_args(args: argparse.Namespace) -> dict[str, str]:
    return metadata(args.pull_request, args.stack_name, args.region, args.source_ref, args.workflow_ref, args.account_id, args.status)


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record-body")
    update = commands.add_parser("update-body")
    extract = commands.add_parser("github-output")
    add_metadata_arguments(record)
    add_metadata_arguments(update)
    extract.add_argument("--pull-request", required=True, type=int)
    args = parser.parse_args()
    if args.command in ("record-body", "update-body"):
        print(comment_body(values_from_args(args)))
        return
    target = latest_target(comment_pages(json.load(sys.stdin)), args.pull_request)
    if target is None:
        print("found=false")
        return
    print("found=true")
    for field, value in target.items():
        print(f"{field}={value}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from None