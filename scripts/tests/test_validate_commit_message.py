from __future__ import annotations

import unittest

from scripts.validate_commit_message import validate_message


class ValidateCommitMessageTests(unittest.TestCase):
    def assert_valid(self, message: str) -> None:
        self.assertEqual(validate_message(message), [])

    def assert_invalid(self, message: str, expected: str) -> None:
        self.assertTrue(
            any(expected in error for error in validate_message(message)),
            msg=f"未找到预期错误：{expected}",
        )

    def test_accepts_chinese_subject_with_scope(self) -> None:
        self.assert_valid("feat(frontend): 优化视频下载页面")

    def test_accepts_chinese_subject_without_scope(self) -> None:
        self.assert_valid("docs: 完善提交规范")

    def test_accepts_breaking_change_with_chinese_footer(self) -> None:
        self.assert_valid(
            "feat(api)!: 移除旧下载接口\n\n"
            "BREAKING CHANGE: 客户端需要迁移到新版下载接口"
        )

    def test_rejects_automatic_merge_commit(self) -> None:
        self.assert_invalid(
            "Merge pull request #12 from example/topic",
            "标题格式",
        )

    def test_rejects_english_only_subject(self) -> None:
        self.assert_invalid(
            "feat(frontend): improve download page",
            "必须包含中文",
        )

    def test_rejects_empty_scope(self) -> None:
        self.assert_invalid("feat(): 增加功能", "标题格式")

    def test_rejects_trailing_punctuation(self) -> None:
        self.assert_invalid("fix(api): 修复参数校验。", "末尾不要添加标点")

    def test_requires_blank_line_before_body(self) -> None:
        self.assert_invalid(
            "refactor(worker): 调整任务结构\n正文紧跟标题",
            "必须保留一个空行",
        )

    def test_requires_breaking_change_footer(self) -> None:
        self.assert_invalid(
            "feat(api)!: 移除旧下载接口",
            "必须在正文中提供",
        )


if __name__ == "__main__":
    unittest.main()
