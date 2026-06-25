"""CLI entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from codegrapher import __version__
from codegrapher.builder import build_graph
from codegrapher.scanner import scan_repository
from codegrapher.serialize import to_compact, to_json, to_mermaid, write_outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="codegraph",
        description="Generate compact code graphs for AI coding tools (Cursor, Claude, Codex).",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Repository root to scan (default: current directory)",
    )
    parser.add_argument(
        "-o", "--output",
        default=".codegraph",
        help="Output directory (default: .codegraph)",
    )
    parser.add_argument(
        "-f", "--format",
        action="append",
        choices=["json", "compact", "mermaid", "cursor", "claude", "codex", "all"],
        help="Output format (repeatable). Default: all",
    )
    parser.add_argument(
        "--print",
        dest="print_fmt",
        choices=["compact", "json", "mermaid"],
        help="Print format to stdout instead of writing files",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="Extra glob patterns to ignore",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Limit number of files scanned",
    )
    parser.add_argument(
        "--no-docs",
        action="store_true",
        help="Skip scanning markdown architecture/docs files",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"codegrapher {__version__}",
    )

    args = parser.parse_args(argv)
    root = Path(args.path).resolve()

    if not root.is_dir():
        print(f"error: not a directory: {root}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(f"Scanning {root}...", file=sys.stderr)

    scanned = scan_repository(root, extra_ignore=args.ignore, max_files=args.max_files)
    if not scanned:
        print("warning: no source files found", file=sys.stderr)
        return 1

    graph = build_graph(root, scanned, include_docs=not args.no_docs, extra_ignore=args.ignore)

    if not args.quiet:
        s = graph.stats
        print(
            f"Built graph: {s['files']} files, {s['symbols']} symbols, {s['edges']} edges, "
            f"{s.get('docs', 0)} doc sections",
            file=sys.stderr,
        )

    if args.print_fmt:
        if args.print_fmt == "compact":
            print(to_compact(graph), end="")
        elif args.print_fmt == "json":
            print(to_json(graph), end="")
        elif args.print_fmt == "mermaid":
            print(to_mermaid(graph), end="")
        return 0

    formats = set(args.format or ["all"])
    if "all" in formats:
        formats = {"json", "compact", "mermaid", "cursor", "claude", "codex"}

    out_dir = Path(args.output)
    if not out_dir.is_absolute():
        out_dir = root / out_dir

    written = write_outputs(graph, out_dir, formats=formats)

    if not args.quiet:
        for fmt, path in sorted(written.items()):
            rel = path.relative_to(root) if path.is_relative_to(root) else path
            print(f"  wrote {fmt}: {rel}", file=sys.stderr)

        print(file=sys.stderr)
        print("Tip: paste .codegraph/codegraph.txt into any AI chat to save tokens.", file=sys.stderr)
        print("     Or use the generated Cursor/Claude/Codex rule files for auto-context.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
