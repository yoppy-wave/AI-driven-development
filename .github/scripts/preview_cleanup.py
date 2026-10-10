#!/usr/bin/env python3
"""Persist and recover the immutable cleanup target for a PR preview environment."""

import argparse
import json
import re
import sys
from typing import Any


MARKER = "<!-- cicd-preview-cleanup:v1 "
BOT_LOGIN = "github-actions[bot]"
REQUIRED_FIELDS = ("work_directory", "stack_name", "worker_name", "backend_url")
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    raise ValueError(message)


def metadata(
    pull_request: int,
    work_directory: str,
    stack_name: str,
    worker_name: str,
    backend_url: str,
    source_ref: str,
) -> dict[str, str]:
    if pull_request < 1:
        fail("pull request number must be positive")
    values = {
        "work_directory": work_directory,
        "stack_name": stack_name,
        "worker_name": worker_name,
        "backend_url": backend_url,
        "source_ref": source_ref,
    }
    for field in REQUIRED_FIELDS:
        if not isinstance(values[field], str) or (field != "backend_url" and not values[field]):
            fail(f"{field} must be a non-empty string")
    if work_directory.startswith("/") or ".." in work_directory.split("/"):
        fail("work_directory must be a repository-relative path without parent traversal")
    suffix = f"-pr-{pull_request}"
    if not stack_name.endswith(suffix) or not worker_name.endswith(suffix):
        fail("preview stack and worker names must end with the pull request suffix")
    if not isinstance(source_ref, str) or not COMMIT_SHA_PATTERN.fullmatch(source_ref):
        fail("source_ref must be a full commit SHA")
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
            values.get("stack_name"),
            values.get("worker_name"),
            values.get("backend_url"),
            values.get("source_ref"),
        )
    except ValueError:
        return None


def latest_metadata(comments: list[dict[str, Any]], pull_request: int) -> dict[str, str] | None:
    for comment in reversed(comments):
        values = metadata_from_comment(comment.get("body"), comment.get("user", {}).get("login"), pull_request)
        if values is not None:
            return values
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


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    record = commands.add_parser("record-body")
    extract = commands.add_parser("github-output")
    for command in (record, extract):
        command.add_argument("--pull-request", required=True, type=int)
    for argument in ("work-directory", "stack-name", "worker-name", "backend-url", "source-ref"):
        record.add_argument(f"--{argument}", required=True)
    args = parser.parse_args()

    if args.command == "record-body":
        print(
            comment_body(
                metadata(
                    args.pull_request,
                    args.work_directory,
                    args.stack_name,
                    args.worker_name,
                    args.backend_url,
                    args.source_ref,
                )
            )
        )
        return

    comments = comment_pages(json.load(sys.stdin))
    values = latest_metadata(comments, args.pull_request)
    if values is None:
        print("found=false")
        return
    print("found=true")
    for field, value in values.items():
        print(f"{field}={value}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as error:
        raise SystemExit(str(error)) from None