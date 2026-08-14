from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts import ci


class WorkflowActionPinTests(unittest.TestCase):
    def test_accepts_commit_pinned_and_local_actions(self) -> None:
        contents = """
        - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        - uses: ./actions/project-check
        - uses: docker://alpine@sha256:fixed
        """
        self.assertEqual(ci.unpinned_actions(contents), [])

    def test_rejects_tags_branches_and_missing_revisions(self) -> None:
        contents = """
        - uses: actions/checkout@v7
        - uses: owner/action@main
        - uses: owner/action
        """
        self.assertEqual(
            ci.unpinned_actions(contents),
            ["actions/checkout@v7", "owner/action@main", "owner/action"],
        )


class RepositoryCommandTests(unittest.TestCase):
    @patch("scripts.ci.run")
    def test_script_tests_use_current_python_interpreter(self, run) -> None:
        ci.repository()

        run.assert_any_call(
            "提交规范测试",
            ci.sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "scripts/tests",
            "-v",
        )

    @patch("scripts.ci.shutil.which", return_value=r"D:\Nodejs\npm.CMD")
    def test_npm_executable_resolves_windows_command_shim(self, which) -> None:
        self.assertEqual(ci.npm_executable(), r"D:\Nodejs\npm.CMD")
        which.assert_called_once_with("npm")

    @patch("scripts.ci.shutil.which", return_value=None)
    def test_npm_executable_falls_back_to_command_name(self, which) -> None:
        self.assertEqual(ci.npm_executable(), "npm")
        which.assert_called_once_with("npm")


if __name__ == "__main__":
    unittest.main()
