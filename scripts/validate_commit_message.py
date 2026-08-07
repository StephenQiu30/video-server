#!/usr/bin/env python3
"""校验仓库提交信息是否符合中文 Conventional Commits 规范。"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


ALLOWED_TYPES = (
    "feat",
    "fix",
    "refactor",
    "docs",
    "test",
    "perf",
    "build",
    "ci",
    "chore",
    "style",
    "revert",
)
HEADER_PATTERN = re.compile(
    rf"^(?P<type>{'|'.join(ALLOWED_TYPES)})"
    r"(?:\((?P<scope>[a-z][a-z0-9-]*)\))?"
    r"(?P<breaking>!)?: (?P<subject>\S.*)$"
)
CHINESE_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
BREAKING_PATTERN = re.compile(
    r"^BREAKING CHANGE: (?P<description>.+)$",
    re.MULTILINE,
)
TRAILING_PUNCTUATION = ("。", ".", "！", "!", "？", "?", "；", ";")


def validate_message(message: str) -> list[str]:
    """返回提交信息中的所有规范错误。"""
    lines = message.splitlines()
    if not lines or not lines[0].strip():
        return ["提交标题不能为空"]

    title = lines[0]
    errors: list[str] = []
    if title != title.strip():
        errors.append("提交标题前后不能包含空格")
    if len(title) > 72:
        errors.append("提交标题不能超过 72 个字符")

    match = HEADER_PATTERN.fullmatch(title)
    if match is None:
        errors.append(
            "标题格式应为 <type>(<scope>): <中文描述>，作用域可省略且不能使用空括号"
        )
        return errors

    subject = match.group("subject")
    if CHINESE_PATTERN.search(subject) is None:
        errors.append("冒号后的描述必须包含中文")
    if subject.endswith(TRAILING_PUNCTUATION):
        errors.append("提交标题末尾不要添加标点")
    if len(lines) > 1 and lines[1].strip():
        errors.append("提交标题与正文之间必须保留一个空行")

    breaking_footer = BREAKING_PATTERN.search(message)
    is_breaking = match.group("breaking") is not None
    if is_breaking and breaking_footer is None:
        errors.append("破坏性变更必须在正文中提供 BREAKING CHANGE: <中文说明>")
    if breaking_footer is not None:
        if not is_breaking:
            errors.append("包含 BREAKING CHANGE 时，提交标题必须添加 ! 标记")
        if CHINESE_PATTERN.search(breaking_footer.group("description")) is None:
            errors.append("BREAKING CHANGE 说明必须包含中文")

    return errors


def read_commit_message(commit: str) -> str:
    result = subprocess.run(
        ["git", "show", "-s", "--format=%B", commit],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def commits_in_range(revision_range: str) -> list[str]:
    result = subprocess.run(
        ["git", "rev-list", "--reverse", revision_range],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return [commit for commit in result.stdout.splitlines() if commit]


def report(label: str, message: str) -> bool:
    errors = validate_message(message)
    if not errors:
        print(f"通过：{label} · {message.splitlines()[0]}")
        return True

    print(
        f"不通过：{label} · {message.splitlines()[0] if message.splitlines() else '(空标题)'}"
    )
    for error in errors:
        print(f"  - {error}")
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--message", help="直接校验一条提交信息")
    source.add_argument("--message-file", type=Path, help="校验提交信息文件")
    source.add_argument("--commit", help="校验指定提交")
    source.add_argument("--range", dest="revision_range", help="校验 Git 提交范围")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.message is not None:
            return 0 if report("提交信息", args.message) else 1
        if args.message_file is not None:
            message = args.message_file.read_text(encoding="utf-8")
            return 0 if report(str(args.message_file), message) else 1
        if args.commit is not None:
            return 0 if report(args.commit, read_commit_message(args.commit)) else 1

        revision_range = args.revision_range
        if revision_range is None:
            raise ValueError("必须提供待校验的提交范围")
        commits = commits_in_range(revision_range)
        if not commits:
            print(f"提交范围内没有待校验提交：{revision_range}")
            return 0
        results = [
            report(commit[:12], read_commit_message(commit)) for commit in commits
        ]
        return 0 if all(results) else 1
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        print(f"提交信息校验执行失败：{error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
