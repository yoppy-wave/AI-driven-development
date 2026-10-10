#!/usr/bin/env python3
"""Validate and expose the repository CI/CD configuration."""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".github" / "cicd" / "application.json"
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def fail(message: str) -> None:
    raise ValueError(message)


def required_object(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        fail(f"{name} must be an object")
    return value


def required_string(section: dict[str, object], key: str, name: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value:
        fail(f"{name}.{key} must be a non-empty string")
    return value


def required_bool(section: dict[str, object], key: str, name: str) -> bool:
    value = section.get(key)
    if not isinstance(value, bool):
        fail(f"{name}.{key} must be a boolean")
    return value


def load(path: Path = CONFIG_PATH) -> dict[str, object]:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"CI/CD configuration is missing: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as error:
        fail(f"CI/CD configuration is not valid JSON: {error.msg}")
    return validate(required_object(config, "configuration"), path.parents[2])


def validate(config: dict[str, object], root: Path = ROOT) -> dict[str, object]:
    if config.get("version") != 1:
        fail("version must be 1")

    application = required_object(config.get("application"), "application")
    name = required_string(application, "name", "application")
    worker_prefix = required_string(application, "workerPrefix", "application")
    for field, value in (("application.name", name), ("application.workerPrefix", worker_prefix)):
        if not NAME_PATTERN.fullmatch(value):
            fail(f"{field} must use lowercase letters, digits, and hyphens, start with a letter, and be at most 63 characters")

    ci = required_object(config.get("ci"), "ci")
    required_bool(ci, "enabled", "ci")

    pulumi = required_object(config.get("pulumi"), "pulumi")
    enabled = required_bool(pulumi, "enabled", "pulumi")
    work_directory = required_string(pulumi, "workDirectory", "pulumi")
    backend_url = pulumi.get("backendUrl")
    if not isinstance(backend_url, str):
        fail("pulumi.backendUrl must be a string")
    stack_prefix = required_string(pulumi, "stackPrefix", "pulumi")
    preview_enabled = required_bool(pulumi, "previewEnvironmentEnabled", "pulumi")
    if not NAME_PATTERN.fullmatch(stack_prefix):
        fail("pulumi.stackPrefix must use lowercase letters, digits, and hyphens, start with a letter, and be at most 63 characters")
    if preview_enabled and not enabled:
        fail("pulumi.previewEnvironmentEnabled requires pulumi.enabled to be true")
    if enabled and not (root / work_directory / "Pulumi.yaml").is_file():
        fail("pulumi.workDirectory must contain Pulumi.yaml when pulumi.enabled is true")

    deployments = required_object(config.get("deployments"), "deployments")
    for environment in ("development", "staging", "production"):
        required_bool(deployments, environment, "deployments")
    if any(deployments.values()) and not enabled:
        fail("enabled deployments require pulumi.enabled to be true")

    return config


def values(config: dict[str, object], pull_request: int | None = None) -> dict[str, str]:
    application = required_object(config["application"], "application")
    ci = required_object(config["ci"], "ci")
    pulumi = required_object(config["pulumi"], "pulumi")
    deployments = required_object(config["deployments"], "deployments")
    result = {
        "application_name": str(application["name"]),
        "worker_prefix": str(application["workerPrefix"]),
        "ci_enabled": str(ci["enabled"]).lower(),
        "pulumi_enabled": str(pulumi["enabled"]).lower(),
        "pulumi_work_directory": str(pulumi["workDirectory"]),
        "pulumi_backend_url": str(pulumi["backendUrl"]),
        "stack_prefix": str(pulumi["stackPrefix"]),
        "preview_environment_enabled": str(pulumi["previewEnvironmentEnabled"]).lower(),
        "development_enabled": str(deployments["development"]).lower(),
        "staging_enabled": str(deployments["staging"]).lower(),
        "production_enabled": str(deployments["production"]).lower(),
    }
    if pull_request is not None:
        if pull_request < 1:
            fail("pull request number must be positive")
        result["preview_stack"] = f"{result['stack_prefix']}-pr-{pull_request}"
        result["preview_worker_name"] = f"{result['worker_prefix']}-pr-{pull_request}"
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "github-output", "json"))
    parser.add_argument("--pull-request", type=int)
    args = parser.parse_args()
    config = load()
    output = values(config, args.pull_request)
    if args.command == "validate":
        print("CI/CD configuration is valid.")
    elif args.command == "github-output":
        for key, value in output.items():
            print(f"{key}={value}")
    else:
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error)) from None