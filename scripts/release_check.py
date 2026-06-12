#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run local checks before tagging or publishing a LingCe release."""

import argparse
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = {
    "data/user_data.json",
    "data/settings.json",
    "data/exam_history.db",
}
GENERATED_QUESTION_BANK_PATTERN = re.compile(r"^question_banks/(?!题库\.json$).+\.json$")
EXCLUDED_TEXT_FILES = RUNTIME_FILES | {"scripts/release_check.py"}
MOJIBAKE_MARKERS = ("鐏", "搴", "棰", "鑰", "缁", "閿", "馃", "鈥", "鈹", "\ufffd")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".toml", ".json", ".yml", ".yaml"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tests", action="store_true", help="skip compileall and pytest")
    args = parser.parse_args()

    checks = [
        ("version consistency", check_versions),
        ("runtime files are not staged", check_runtime_files_not_staged),
        ("tracked file size", check_tracked_file_sizes),
        ("mojibake scan", check_mojibake),
    ]

    failures = []
    for name, check in checks:
        try:
            check()
            print(f"[OK] {name}")
        except CheckFailure as exc:
            failures.append(f"[FAIL] {name}: {exc}")
            print(failures[-1])

    if not args.skip_tests:
        try:
            run(["python", "-m", "compileall", "-q", "."])
            pytest_output = run(["pytest", "-q"])
            print("[OK] compileall")
            print("[OK] pytest")
            check_readme_test_badge(pytest_output)
            print("[OK] README test badge")
        except CheckFailure as exc:
            failures.append(f"[FAIL] tests: {exc}")
            print(failures[-1])

    if failures:
        print("\nRelease check failed.")
        return 1

    print("\nRelease check passed.")
    return 0


class CheckFailure(RuntimeError):
    """A release check failed."""


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_match(pattern: str, text: str, label: str) -> str:
    match = re.search(pattern, text)
    if not match:
        raise CheckFailure(f"missing {label}")
    return match.group(1)


def check_versions():
    app_version = require_match(
        r'APP_VERSION\s*=\s*"V(\d+\.\d+\.\d+)"',
        read_text("core/config.py"),
        "APP_VERSION",
    )
    pyproject_version = require_match(
        r'(?m)^version\s*=\s*"(\d+\.\d+\.\d+)"',
        read_text("pyproject.toml"),
        "pyproject version",
    )
    requirements_version = require_match(
        r"V(\d+\.\d+\.\d+)",
        read_text("requirements.txt").splitlines()[0],
        "requirements version",
    )
    settings_version = require_match(
        r'"version"\s*:\s*"(\d+\.\d+\.\d+)"',
        read_text("core/default_settings.py"),
        "default settings version",
    )

    versions = {
        app_version,
        pyproject_version,
        requirements_version,
        settings_version,
    }
    if len(versions) != 1:
        raise CheckFailure(f"version mismatch: {sorted(versions)}")


def check_runtime_files_not_staged():
    staged = run(["git", "diff", "--cached", "--name-status"]).splitlines()
    bad = []
    for line in staged:
        status, _, name = line.partition("\t")
        if name in RUNTIME_FILES and status != "D":
            bad.append(name)
        if GENERATED_QUESTION_BANK_PATTERN.match(name) and status != "D":
            bad.append(name)
    if bad:
        raise CheckFailure("runtime files are staged: " + ", ".join(bad))


def check_tracked_file_sizes():
    tracked = run(["git", "ls-files"]).splitlines()
    large_files = []
    for name in tracked:
        path = ROOT / name
        if path.exists() and path.stat().st_size > 5 * 1024 * 1024:
            large_files.append(f"{name} ({path.stat().st_size / 1024 / 1024:.1f} MB)")
    if large_files:
        raise CheckFailure("large tracked files: " + ", ".join(large_files))


def check_mojibake():
    offenders = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in EXCLUDED_TEXT_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(marker in text for marker in MOJIBAKE_MARKERS):
            offenders.append(rel)
    if offenders:
        raise CheckFailure("possible mojibake in " + ", ".join(offenders[:10]))


def check_readme_test_badge(pytest_output: str):
    passed = require_match(r"(\d+)\s+passed", pytest_output, "pytest pass count")
    readme = read_text("README.md")
    expected = f"Tests-{passed}%20passed"
    if expected not in readme:
        raise CheckFailure(f"README badge should contain {expected}")


def run(command):
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise CheckFailure(completed.stdout.strip())
    return completed.stdout


if __name__ == "__main__":
    sys.exit(main())
