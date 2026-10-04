from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

import sync_chrome_bookmarks as sync  # noqa: E402


def url(name: str, destination: str) -> dict[str, str]:
    return {"type": "url", "name": name, "url": destination}


def folder(name: str, children: list[dict[str, object]]) -> dict[str, object]:
    return {"type": "folder", "name": name, "children": children}


class SyncChromeBookmarksTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.source = self.directory / "AccountBookmarks"
        self.markdown = self.directory / "bookmark.md"
        self.markdown.write_text(
            "# Bookmarks\n\n<div class=\"bookmark-grid\" markdown>\n\n"
            "Manual content.\n\n</div>\n",
            encoding="utf-8",
        )

    def write_source(self, children: list[dict[str, object]]) -> None:
        data = {
            "roots": {
                "bookmark_bar": folder("Bookmarks bar", children),
                "other": folder("Other bookmarks", []),
            },
            "version": 1,
        }
        self.source.write_text(json.dumps(data), encoding="utf-8")

    def test_inserts_managed_block_and_is_idempotent(self) -> None:
        self.write_source(
            [
                folder(
                    "AI",
                    [
                        url("Assistant", "https://assistant.example/app"),
                        folder(
                            "Research",
                            [url("Paper", "https://research.example/paper(1)")],
                        ),
                    ],
                )
            ]
        )

        first = sync.sync_bookmarks(
            self.source, self.markdown, folder_paths=("AI",)
        )

        self.assertTrue(first.changed)
        self.assertEqual(first.total, 2)
        self.assertEqual(len(first.added), 2)
        generated = self.markdown.read_text(encoding="utf-8")
        self.assertLess(generated.index(sync.START_MARKER), generated.index("</div>"))
        self.assertIn("- **AI**", generated)
        self.assertIn("  - **Research**", generated)
        self.assertIn(
            "[Paper](<https://research.example/paper(1)>)", generated
        )

        second = sync.sync_bookmarks(
            self.source, self.markdown, folder_paths=("AI",)
        )
        self.assertFalse(second.changed)
        self.assertEqual(len(second.added), 0)
        self.assertEqual(len(second.removed), 0)
        self.assertEqual(len(second.renamed), 0)

    def test_reports_add_remove_and_rename_before_updating(self) -> None:
        self.write_source(
            [
                folder(
                    "AI",
                    [
                        url("Old title", "https://one.example"),
                        url("Removed", "https://two.example"),
                    ],
                )
            ]
        )
        sync.sync_bookmarks(self.source, self.markdown, folder_paths=("AI",))
        original = self.markdown.read_bytes()

        self.write_source(
            [
                folder(
                    "AI",
                    [
                        url("New title", "https://one.example"),
                        url("Added", "https://three.example"),
                    ],
                )
            ]
        )
        report = sync.sync_bookmarks(
            self.source, self.markdown, folder_paths=("AI",), write=False
        )

        self.assertTrue(report.changed)
        self.assertEqual([item.url for item in report.added], ["https://three.example"])
        self.assertEqual(
            [item.url for item in report.removed], ["https://two.example"]
        )
        self.assertEqual(len(report.renamed), 1)
        self.assertEqual(report.renamed[0][0], "Old title")
        self.assertEqual(report.renamed[0][1].name, "New title")
        self.assertEqual(self.markdown.read_bytes(), original)

    def test_rejects_sensitive_urls_unless_explicitly_allowed(self) -> None:
        self.write_source(
            [
                folder(
                    "AI",
                    [
                        url("Private", "http://127.0.0.1/admin"),
                        url("Token", "https://example.test/path?access_token=secret"),
                        url(
                            "Cloud account",
                            "https://console.example/account/123456789012/home",
                        ),
                    ],
                )
            ]
        )

        with self.assertRaisesRegex(sync.SyncError, "potentially sensitive") as error:
            sync.sync_bookmarks(self.source, self.markdown, folder_paths=("AI",))
        self.assertNotIn("secret", str(error.exception))
        self.assertNotIn("123456789012", str(error.exception))
        self.assertNotIn(sync.START_MARKER, self.markdown.read_text(encoding="utf-8"))

        report = sync.sync_bookmarks(
            self.source,
            self.markdown,
            folder_paths=("AI",),
            allow_sensitive=True,
        )
        self.assertTrue(report.changed)
        self.assertEqual(report.total, 3)

    def test_rejects_missing_or_damaged_managed_markers(self) -> None:
        self.write_source([folder("AI", [url("A", "https://a.example")])])
        self.markdown.write_text(
            f"# Bookmarks\n\n{sync.START_MARKER}\n", encoding="utf-8"
        )

        with self.assertRaisesRegex(sync.SyncError, "complete Chrome sync block"):
            sync.sync_bookmarks(self.source, self.markdown, folder_paths=("AI",))

    def test_selects_nested_and_multiple_folders(self) -> None:
        self.write_source(
            [
                folder(
                    "Development",
                    [folder("Python", [url("Docs", "https://python.example")])],
                ),
                folder("AI", [url("Chat", "https://chat.example")]),
            ]
        )
        data = sync.load_account_bookmarks(self.source)

        nodes = sync.select_nodes(data, "bookmark_bar", ("Development/Python", "AI"))
        bookmarks = [bookmark for node in nodes for bookmark in sync.iter_bookmarks(node)]

        self.assertEqual([node["name"] for node in nodes], ["Python", "AI"])
        self.assertEqual(
            [bookmark.url for bookmark in bookmarks],
            ["https://python.example", "https://chat.example"],
        )

    def test_check_mode_returns_one_without_writing(self) -> None:
        self.write_source([folder("AI", [url("A", "https://a.example")])])
        output = StringIO()
        errors = StringIO()

        with redirect_stdout(output), redirect_stderr(errors):
            result = sync.main(
                [
                    "--source",
                    str(self.source),
                    "--markdown",
                    str(self.markdown),
                    "--folder",
                    "AI",
                    "--check",
                ]
            )

        self.assertEqual(result, 1)
        self.assertIn("Status: out of date", output.getvalue())
        self.assertEqual(errors.getvalue(), "")
        self.assertNotIn(sync.START_MARKER, self.markdown.read_text(encoding="utf-8"))

    def test_cli_requires_explicit_sync_scope(self) -> None:
        errors = StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as exit_error:
            sync.parse_args([])

        self.assertEqual(exit_error.exception.code, 2)
        self.assertIn("one of the arguments --folder --all is required", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
