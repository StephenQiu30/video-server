from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.archive_completed_docs import (
    DocumentArchiveError,
    archive_completed_sets,
    discover_ready_sets,
)


class CompletedDocumentArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.docs = self.root / "docs"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_only_complete_document_sets_are_discovered(self) -> None:
        self._write_set("001", "Accepted")
        self._write_set("002", "Pending")
        self._write_index(("001", "002"))

        ready = discover_ready_sets(self.root)

        self.assertEqual([item.number for item in ready], ["001"])

    def test_special_gated_set_is_never_archived_by_generic_command(self) -> None:
        self._write_set("017", "Accepted")
        self._write_index(("017",))

        self.assertEqual(discover_ready_sets(self.root), ())
        self.assertEqual(archive_completed_sets(self.root), ())
        self.assertTrue((self.docs / "design/017-design.md").is_file())

    def test_archive_moves_set_and_updates_references(self) -> None:
        self._write_set("001", "Accepted")
        self._write_index(("001",))
        note = self.docs / "note.md"
        note.write_text("`docs/design/001-design.md`\n", encoding="utf-8")
        frontend_readme = self.root / "frontend/README.md"
        frontend_readme.parent.mkdir(parents=True)
        frontend_readme.write_text(
            "`../docs/design/001-design.md`\n", encoding="utf-8"
        )

        archived = archive_completed_sets(self.root)

        self.assertEqual(archived, ("001",))
        self.assertTrue((self.docs / "design/archive/001-design.md").is_file())
        self.assertTrue((self.docs / "prd/archive/001-prd.md").is_file())
        self.assertTrue((self.docs / "plans/archive/001-plan.md").is_file())
        self.assertTrue(
            (self.docs / "acceptance/archive/001-acceptance.md").is_file()
        )
        self.assertFalse((self.docs / "design/001-design.md").exists())
        self.assertIn("001 | Topic（已归档）", self._index_text())
        self.assertEqual(
            note.read_text(encoding="utf-8"), "`docs/design/archive/001-design.md`\n"
        )
        self.assertEqual(
            frontend_readme.read_text(encoding="utf-8"),
            "`../docs/design/archive/001-design.md`\n",
        )
        self.assertEqual(archive_completed_sets(self.root), ())

    def test_partial_archive_index_is_rejected(self) -> None:
        self._write_set("001", "Accepted")
        self._write_index(("001",), partial=True)

        with self.assertRaisesRegex(
            DocumentArchiveError, "document_archive_state_invalid:001"
        ):
            discover_ready_sets(self.root)

    def test_centralized_archive_index_is_rejected(self) -> None:
        self._write_set("001", "Accepted")
        self._write_index(("001",))
        index = self._index_text()
        for folder, name in (
            ("design", "design"),
            ("prd", "prd"),
            ("plans", "plan"),
            ("acceptance", "acceptance"),
        ):
            index = index.replace(
                f"{folder}/001-{name}.md", f"archive/001/001-{name}.md"
            )
        (self.docs / "README.md").write_text(index, encoding="utf-8")

        with self.assertRaisesRegex(
            DocumentArchiveError, "document_archive_state_invalid:001"
        ):
            discover_ready_sets(self.root)

    def test_missing_archived_document_is_rejected(self) -> None:
        self._write_set("001", "Accepted")
        self._write_index(("001",))
        archive_completed_sets(self.root)
        (self.docs / "design/archive/001-design.md").unlink()

        with self.assertRaisesRegex(
            DocumentArchiveError, "document_archive_state_invalid:001"
        ):
            discover_ready_sets(self.root)

    def _write_set(self, number: str, acceptance_status: str) -> None:
        statuses = {
            "design": "Accepted",
            "prd": "Accepted",
            "plans": "Completed",
            "acceptance": acceptance_status,
        }
        names = {
            "design": "design",
            "prd": "prd",
            "plans": "plan",
            "acceptance": "acceptance",
        }
        for folder, status in statuses.items():
            path = self.docs / folder / f"{number}-{names[folder]}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# document\n\n- 状态：{status}\n", encoding="utf-8")

    def _write_index(self, numbers: tuple[str, ...], *, partial: bool = False) -> None:
        rows = []
        for number in numbers:
            design = f"design/{number}-design.md"
            if partial:
                design = f"design/archive/{number}-design.md"
            rows.append(
                f"| {number} | Topic | [Design]({design}) | "
                f"[PRD](prd/{number}-prd.md) | [Plan](plans/{number}-plan.md) | "
                f"[Acceptance](acceptance/{number}-acceptance.md) |"
            )
        self.docs.mkdir(parents=True, exist_ok=True)
        (self.docs / "README.md").write_text("\n".join(rows), encoding="utf-8")

    def _index_text(self) -> str:
        return (self.docs / "README.md").read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
