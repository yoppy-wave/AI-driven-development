#!/usr/bin/env python3
"""Persist and recover immutable cleanup locators for PR preview environments."""

import argparse
import json
import re
import sys
from typing import Any


MARKER = "<!-- cicd-preview-cleanup:v1 "
BOT_LOGIN = "github-actions[bot]"
FIXED_FIELDS = ("work_directory", "project_name", "stack_name", "worker_name", "backend_url")
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
STATUSES = ("pending", "active", "destroyed")


def fail(message: str) -> None:
    raise ValueError(message)


def metadata(
    pull_request: int,
    work_directory: str,
    project_name: str,
    stack_name: str,
    worker_name: str,
    backend_url: str,
    source_ref: str,
    status: str = "pending",
) -> dict[str, str]:
    if pull_request < 1:
        fail("pull request number must be positive")
    values = {
        "work_directory": work_directory,
        "project_name": project_name,
        "stack_name": stack_name,
        "worker_name": worker_name,
        "backend_url": backend_url,
        "source_ref": source_ref,
        "status": status,
    }
    for field in FIXED_FIELDS:
        if not isinstance(values[field], str) or (field != "backend_url" and not values[field]):
            fail(f"{field} must be a non-empty string")
    if work_directory.startswith("/") or ".." in work_directory.split("/"):
        fail("work_directory must be a repository-relative path without parent traversal")
    suffix = f"-pr-{pull_request}"
    if not stack_name.endswith(suffix) or not worker_name.endswith(suffix):
        fail("preview stack and worker names must end with the pull request suffix")
    if not isinstance(source_ref, str) or not COMMIT_SHA_PATTERN.fullmatch(source_ref):
        fail("source_ref must be a full commit SHA")
    if status not in STATUSES:
        fail(f"status must be one of: {', '.join(STATUSES)}")
    return values


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
            values.get("work_directory"),
            values.get("project_name", "legacy-project"),
            values.get("stack_name"),
            values.get("worker_name"),
            values.get("backend_url"),
            values.get("source_ref"),
            values.get("status", "pending"),
        )
    except ValueError:
        return None


def latest_target(comments: list[dict[str, Any]], pull_request: int) -> dict[str, str] | None:
    for comment in reversed(comments):
        values = metadata_from_comment(comment.get("body"), comment.get("user", {}).get("login"), pull_request)
        comment_id = comment.get("id")
        if values is not None and values["status"] != "destroyed" and isinstance(comment_id, int):
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


def add_metadata_arguments(command: argparse.ArgumentParser, *, status: bool = True) -> None:
    command.add_argument("--pull-request", required=True, type=int)
    for argument in ("work-directory", "project-name", "stack-name", "worker-name", "backend-url", "source-ref"):
        command.add_argument(f"--{argument}", required=True)
    if status:
        command.add_argument("--status", required=True, choices=STATUSES)


def metadata_from_args(args: argparse.Namespace) -> dict[str, str]:
    return metadata(
        args.pull_request, args.work_directory, args.project_name, args.stack_name, args.worker_name,
        args.backend_url, args.source_ref, args.status,
    )


def emit_target(target: dict[str, str] | None) -> None:
    if target is None:
        print("found=false")
        return
    print("found=true")
    for field, value in target.items():
        print(f"{field}={value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record-body")
    update = commands.add_parser("update-body")
    extract = commands.add_parser("github-output")
    add_metadata_arguments(record)
    add_metadata_arguments(update)
    extract.add_argument("--pull-request", required=True, type=int)
    extract.add_argument("--work-directory")
    extract.add_argument("--project-name")
    extract.add_argument("--stack-name")
    extract.add_argument("--worker-name")
    extract.add_argument("--backend-url")
    args = parser.parse_args()

    if args.command in ("record-body", "update-body"):
        print(comment_body(metadata_from_args(args)))
        return

    target = latest_target(comment_pages(json.load(sys.stdin)), args.pull_request)
    if target is not None:
        expected = {
            "work_directory": args.work_directory,
            "project_name": args.project_name,
            "stack_name": args.stack_name,
            "worker_name": args.worker_name,
            "backend_url": args.backend_url,
        }
        supplied = {field: value for field, value in expected.items() if value is not None}
        drift = [field for field, value in supplied.items() if target[field] != value]
        if drift:
            fail("preview cleanup locator differs from current configuration: " + ", ".join(drift))
    emit_target(target)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from None
