from __future__ import annotations

import unittest

from scripts.ci import unpinned_actions


class WorkflowActionPinTests(unittest.TestCase):
    def test_accepts_commit_pinned_and_local_actions(self) -> None:
        contents = """
        - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        - uses: ./actions/project-check
        - uses: docker://alpine@sha256:fixed
        """
        self.assertEqual(unpinned_actions(contents), [])

    def test_rejects_tags_branches_and_missing_revisions(self) -> None:
        contents = """
        - uses: actions/checkout@v7
        - uses: owner/action@main
        - uses: owner/action
        """
        self.assertEqual(
            unpinned_actions(contents),
            ["actions/checkout@v7", "owner/action@main", "owner/action"],
        )


if __name__ == "__main__":
    unittest.main()
