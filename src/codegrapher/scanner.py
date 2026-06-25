"""Repository scanner — walks files and extracts module metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from codegrapher.ignore import load_gitignore, should_ignore
from codegrapher.parsers import get_parser
from codegrapher.parsers.base import ParseResult


@dataclass
class ScannedFile:
    rel_path: str
    abs_path: Path
    lang: str
    lines: int
    parse_result: ParseResult = field(default_factory=ParseResult)


LANG_MAP = {
    ".py": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".hpp": "cpp",
    ".swift": "swift",
    ".vue": "vue", ".svelte": "svelte",
    ".sql": "sql",
    ".sh": "shell", ".bash": "shell",
}


def scan_repository(
    root: Path,
    *,
    extra_ignore: list[str] | None = None,
    max_files: int | None = None,
) -> list[ScannedFile]:
    root = root.resolve()
    gitignore = load_gitignore(root)
    results: list[ScannedFile] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if should_ignore(path, root, extra_ignore, gitignore):
            continue

        parser = get_parser(path)
        if parser is None:
            continue

        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
        lang = LANG_MAP.get(path.suffix.lower(), path.suffix.lstrip(".") or "unknown")
        parsed = parser.parse(path, content, rel)

        results.append(
            ScannedFile(
                rel_path=rel,
                abs_path=path,
                lang=lang,
                lines=line_count,
                parse_result=parsed,
            )
        )

        if max_files and len(results) >= max_files:
            break

    return results
