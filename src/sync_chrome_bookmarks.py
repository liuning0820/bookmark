#!/usr/bin/env python3
"""Synchronize Chrome AccountBookmarks into a managed Markdown block."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import parse_qsl, quote, urlsplit

START_MARKER = "<!-- BEGIN CHROME ACCOUNTBOOKMARKS AUTO-SYNC -->"
END_MARKER = "<!-- END CHROME ACCOUNTBOOKMARKS AUTO-SYNC -->"
DEFAULT_ROOT = "bookmark_bar"


class SyncError(Exception):
    """Raised when bookmark data or managed Markdown is invalid."""


@dataclass(frozen=True)
class Bookmark:
    """A bookmark collected from the selected Chrome tree."""

    name: str
    url: str
    folders: tuple[str, ...]

    @property
    def markdown_name(self) -> str:
        return escape_markdown(self.name)

    @property
    def markdown_url(self) -> str:
        return quote(self.url, safe=":/?#[]@!$&'()*+,;=%")


@dataclass(frozen=True)
class PreviousBookmark:
    """A bookmark parsed from the previous generated block."""

    name: str
    url: str


@dataclass(frozen=True)
class SyncReport:
    """The changes between the previous and newly generated blocks."""

    changed: bool
    total: int
    added: tuple[Bookmark, ...]
    removed: tuple[PreviousBookmark, ...]
    renamed: tuple[tuple[str, Bookmark], ...]


@dataclass(frozen=True)
class MarkdownDocument:
    """Decoded Markdown and the details needed to preserve its format."""

    text: str
    newline: str
    has_bom: bool


def default_source_path(profile: str = "Default") -> Path:
    """Return the AccountBookmarks path for a local Chrome profile."""

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / "Google" / "Chrome" / "User Data" / profile / "AccountBookmarks"


def default_markdown_path() -> Path:
    """Return the repository's primary bookmark Markdown path."""

    return Path(__file__).resolve().parents[1] / "docs" / "bookmark.md"


def load_account_bookmarks(path: Path) -> dict[str, Any]:
    """Load and minimally validate a Chrome AccountBookmarks file."""

    if not path.is_file():
        raise SyncError(f"Chrome AccountBookmarks file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SyncError(f"Cannot read Chrome AccountBookmarks file {path}: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("roots"), dict):
        raise SyncError(f"Chrome AccountBookmarks file has no valid 'roots' object: {path}")
    return data


def _folder_children(node: dict[str, Any]) -> list[dict[str, Any]]:
    children = node.get("children", [])
    if not isinstance(children, list):
        raise SyncError(f"Folder {node.get('name', '<unnamed>')!r} has invalid children")
    return [child for child in children if isinstance(child, dict)]


def select_nodes(
    data: dict[str, Any], root_name: str, folder_paths: Sequence[str]
) -> list[dict[str, Any]]:
    """Select a Chrome root or specific slash-delimited folders below it."""

    root = data["roots"].get(root_name)
    if not isinstance(root, dict) or root.get("type") != "folder":
        available = ", ".join(sorted(data["roots"]))
        raise SyncError(f"Chrome root {root_name!r} not found. Available roots: {available}")

    if not folder_paths:
        return [root]

    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for folder_path in folder_paths:
        parts = [part.strip() for part in folder_path.split("/") if part.strip()]
        if not parts:
            raise SyncError("Folder paths must contain at least one folder name")

        node = root
        traversed: list[str] = []
        for part in parts:
            traversed.append(part)
            matches = [
                child
                for child in _folder_children(node)
                if child.get("type") == "folder" and child.get("name") == part
            ]
            if not matches:
                raise SyncError(
                    f"Chrome folder {'/'.join(traversed)!r} not found under root {root_name!r}"
                )
            node = matches[0]

        identity = id(node)
        if identity not in seen:
            selected.append(node)
            seen.add(identity)
    return selected


def clean_name(value: Any, fallback: str) -> str:
    """Normalize a Chrome name for one-line Markdown rendering."""

    if not isinstance(value, str):
        return fallback
    normalized = " ".join(value.split())
    return normalized or fallback


def escape_markdown(value: str) -> str:
    """Escape characters that can alter Markdown link or emphasis syntax."""

    return re.sub(r"([\\`*_{\[\]<>])", r"\\\1", value)


_SENSITIVE_QUERY_KEYS = re.compile(
    r"(^|[_-])(access[_-]?token|id[_-]?token|token|authorization|auth|"
    r"api[_-]?key|secret|password|passwd|signature|session|credential|code)($|[_-])",
    re.IGNORECASE,
)
_CLOUD_ACCOUNT_ID = re.compile(r"(?<!\d)\d{12}(?!\d)")


def bookmark_security_issues(bookmark: Bookmark) -> tuple[str, ...]:
    """Return reasons a bookmark URL may expose local or credential data."""

    try:
        parsed = urlsplit(bookmark.url)
    except ValueError:
        return ("invalid URL",)

    issues: list[str] = []
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        issues.append("non-public URL scheme")
    if parsed.username or parsed.password:
        issues.append("credentials embedded in URL")

    hostname = parsed.hostname or ""
    if hostname.lower() == "localhost" or hostname.lower().endswith(".local"):
        issues.append("local hostname")
    elif hostname:
        try:
            address = ipaddress.ip_address(hostname)
        except ValueError:
            address = None
        if address and not address.is_global:
            issues.append("private or local IP address")
        elif "." not in hostname:
            issues.append("internal hostname")

    query_keys = [key for key, _ in parse_qsl(parsed.query, keep_blank_values=True)]
    if any(_SENSITIVE_QUERY_KEYS.search(key) for key in query_keys):
        issues.append("credential-like query parameter")
    if _CLOUD_ACCOUNT_ID.search(parsed.netloc + parsed.path):
        issues.append("possible cloud account identifier")
    return tuple(dict.fromkeys(issues))


def validate_bookmark_security(bookmarks: Sequence[Bookmark]) -> None:
    """Reject potentially sensitive URLs without echoing their values."""

    issue_counts: dict[str, int] = {}
    affected = 0
    for bookmark in bookmarks:
        issues = bookmark_security_issues(bookmark)
        if issues:
            affected += 1
        for issue in issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    if not issue_counts:
        return

    summary = ", ".join(
        f"{issue}={count}" for issue, count in sorted(issue_counts.items())
    )
    raise SyncError(
        f"Refusing to sync {affected} potentially sensitive bookmark(s) ({summary}). "
        "Review the source locally, narrow --folder, or pass --allow-sensitive "
        "only when the target repository is appropriate."
    )


def iter_bookmarks(
    node: dict[str, Any], folders: tuple[str, ...] = ()
) -> Iterable[Bookmark]:
    """Yield bookmarks from a Chrome node in browser order."""

    node_type = node.get("type")
    if node_type == "url":
        url = node.get("url")
        if isinstance(url, str) and url:
            yield Bookmark(clean_name(node.get("name"), url), url, folders)
        return

    if node_type != "folder":
        return

    folder_name = clean_name(node.get("name"), "Untitled folder")
    child_folders = folders + (folder_name,)
    for child in _folder_children(node):
        yield from iter_bookmarks(child, child_folders)


def _render_node(node: dict[str, Any], depth: int = 0) -> list[str]:
    indent = "  " * depth
    node_type = node.get("type")

    if node_type == "url":
        url = node.get("url")
        if not isinstance(url, str) or not url:
            return []
        name = escape_markdown(clean_name(node.get("name"), url))
        destination = quote(url, safe=":/?#[]@!$&'()*+,;=%")
        return [f"{indent}- [{name}](<{destination}>)"]

    if node_type != "folder":
        return []

    child_lines: list[str] = []
    for child in _folder_children(node):
        child_lines.extend(_render_node(child, depth + 1))
    if not child_lines:
        return []

    name = escape_markdown(clean_name(node.get("name"), "Untitled folder"))
    return [f"{indent}- **{name}**", *child_lines]


def render_managed_block(nodes: Sequence[dict[str, Any]]) -> str:
    """Render selected Chrome nodes as the complete managed Markdown block."""

    tree_lines: list[str] = []
    for node in nodes:
        tree_lines.extend(_render_node(node))
    if not tree_lines:
        tree_lines.append("No bookmarks are present in the selected Chrome folders.")

    lines = [
        START_MARKER,
        '<section class="bookmark-card" markdown>',
        "",
        "## Chrome 自动同步",
        "",
        "此区块由 `src/sync_chrome_bookmarks.py` 从 Chrome 自动生成。",
        "不要手动编辑标记之间的内容。",
        "",
        *tree_lines,
        "",
        "</section>",
        END_MARKER,
    ]
    return "\n".join(lines)


def read_markdown(path: Path) -> MarkdownDocument:
    """Read Markdown while preserving its BOM and dominant newline style."""

    if not path.is_file():
        raise SyncError(f"Markdown target not found: {path}")
    try:
        raw = path.read_bytes()
        has_bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise SyncError(f"Cannot read Markdown target {path}: {error}") from error

    newline = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") / 2 else "\n"
    return MarkdownDocument(text=text, newline=newline, has_bom=has_bom)


def _managed_span(markdown: str) -> tuple[int, int] | None:
    start_count = markdown.count(START_MARKER)
    end_count = markdown.count(END_MARKER)
    if start_count == 0 and end_count == 0:
        return None
    if start_count != 1 or end_count != 1:
        raise SyncError("Markdown must contain either zero or one complete Chrome sync block")

    start = markdown.index(START_MARKER)
    end = markdown.index(END_MARKER)
    if end < start:
        raise SyncError("Chrome sync block end marker appears before its start marker")
    return start, end + len(END_MARKER)


def merge_managed_block(markdown: str, block: str) -> tuple[str, str]:
    """Replace the managed block or insert it before the bookmark grid closes."""

    span = _managed_span(markdown)
    if span is not None:
        start, end = span
        previous = markdown[start:end]
        merged = markdown[:start].rstrip() + "\n\n" + block + "\n\n" + markdown[end:].lstrip()
        return merged, previous

    closing_grid = markdown.rfind("</div>")
    if closing_grid >= 0:
        merged = (
            markdown[:closing_grid].rstrip()
            + "\n\n"
            + block
            + "\n\n"
            + markdown[closing_grid:].lstrip()
        )
    else:
        merged = markdown.rstrip() + "\n\n" + block + "\n"
    return merged, ""


_LINK_PATTERN = re.compile(r"^\s*-\s+\[(.*)\]\(<(.*)>\)\s*$", re.MULTILINE)


def parse_generated_links(block: str) -> tuple[PreviousBookmark, ...]:
    """Parse links emitted by this tool from a managed block."""

    return tuple(PreviousBookmark(name, url) for name, url in _LINK_PATTERN.findall(block))


def create_report(
    previous_block: str, new_block: str, bookmarks: Sequence[Bookmark]
) -> SyncReport:
    """Compare old and new managed blocks and describe URL-level changes."""

    previous = parse_generated_links(previous_block)
    old_by_url = {bookmark.url: bookmark for bookmark in previous}
    new_by_url = {bookmark.markdown_url: bookmark for bookmark in bookmarks}

    added = tuple(new_by_url[url] for url in new_by_url.keys() - old_by_url.keys())
    removed = tuple(old_by_url[url] for url in old_by_url.keys() - new_by_url.keys())
    renamed = tuple(
        (old_by_url[url].name, new_by_url[url])
        for url in old_by_url.keys() & new_by_url.keys()
        if old_by_url[url].name != new_by_url[url].markdown_name
    )
    normalized_previous = previous_block.replace("\r\n", "\n").replace("\r", "\n")
    normalized_new = new_block.replace("\r\n", "\n").replace("\r", "\n")
    return SyncReport(
        changed=normalized_previous != normalized_new,
        total=len(bookmarks),
        added=tuple(sorted(added, key=lambda item: (item.folders, item.name, item.url))),
        removed=tuple(sorted(removed, key=lambda item: (item.name, item.url))),
        renamed=tuple(sorted(renamed, key=lambda item: item[1].url)),
    )


def atomic_write(path: Path, document: MarkdownDocument, text: str) -> None:
    """Atomically replace a Markdown file without changing its text format."""

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if document.newline != "\n":
        normalized = normalized.replace("\n", document.newline)
    payload = normalized.encode("utf-8")
    if document.has_bom:
        payload = b"\xef\xbb\xbf" + payload

    temporary_name: str | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except OSError as error:
        raise SyncError(f"Cannot update Markdown target {path}: {error}") from error
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def sync_bookmarks(
    source: Path,
    markdown_path: Path,
    *,
    root_name: str = DEFAULT_ROOT,
    folder_paths: Sequence[str] = (),
    allow_sensitive: bool = False,
    write: bool = True,
) -> SyncReport:
    """Synchronize selected Chrome bookmarks into the managed Markdown block."""

    data = load_account_bookmarks(source)
    nodes = select_nodes(data, root_name, folder_paths)
    bookmarks = tuple(bookmark for node in nodes for bookmark in iter_bookmarks(node))
    if not allow_sensitive:
        validate_bookmark_security(bookmarks)
    new_block = render_managed_block(nodes)

    document = read_markdown(markdown_path)
    merged, previous_block = merge_managed_block(document.text, new_block)
    report = create_report(previous_block, new_block, bookmarks)
    if report.changed and write:
        atomic_write(markdown_path, document, merged)
    return report


def print_report(
    report: SyncReport, source: Path, markdown_path: Path, verbose: bool
) -> None:
    """Print a compact sync summary and optional item-level changes."""

    status = "out of date" if report.changed else "up to date"
    print(f"Source: {source}")
    print(f"Target: {markdown_path}")
    print(
        f"Status: {status}; bookmarks={report.total}, added={len(report.added)}, "
        f"removed={len(report.removed)}, renamed={len(report.renamed)}"
    )
    if not verbose:
        return

    for bookmark in report.added:
        print(f"+ {'/'.join(bookmark.folders)} :: {bookmark.name} :: {bookmark.url}")
    for bookmark in report.removed:
        print(f"- {bookmark.name} :: {bookmark.url}")
    for previous_name, bookmark in report.renamed:
        print(f"~ {previous_name} -> {bookmark.name} :: {bookmark.url}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""

    parser = argparse.ArgumentParser(
        description=(
            "Synchronize Chrome AccountBookmarks into the managed block in "
            "docs/bookmark.md."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="AccountBookmarks file (defaults to the selected local Chrome profile)",
    )
    parser.add_argument(
        "--profile",
        default="Default",
        help="Chrome profile directory used when --source is omitted (default: Default)",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=default_markdown_path(),
        help="Markdown target (default: docs/bookmark.md in this repository)",
    )
    parser.add_argument(
        "--root",
        default=DEFAULT_ROOT,
        help="Chrome root to synchronize (default: bookmark_bar)",
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument(
        "--folder",
        action="append",
        help=(
            "Slash-delimited folder below the root; repeat to select multiple "
            "folders"
        ),
    )
    scope.add_argument(
        "--all",
        action="store_true",
        help="Explicitly synchronize the complete selected Chrome root",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="Report differences without writing"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Do not write and exit 1 when the generated block is out of date",
    )
    parser.add_argument(
        "--allow-sensitive",
        action="store_true",
        help=(
            "Allow URLs flagged as potentially sensitive; use only after reviewing "
            "the selected folders and repository visibility"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="List changed bookmark names and URLs (may expose sensitive data)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line synchronizer."""

    args = parse_args(argv)
    source = args.source or default_source_path(args.profile)
    try:
        report = sync_bookmarks(
            source,
            args.markdown,
            root_name=args.root,
            folder_paths=args.folder or (),
            allow_sensitive=args.allow_sensitive,
            write=not (args.dry_run or args.check),
        )
    except SyncError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print_report(report, source, args.markdown, args.verbose)
    if args.check and report.changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
