"""Default ignore patterns for repository scanning."""

from __future__ import annotations

import fnmatch
from pathlib import Path

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
    "coverage",
    ".coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    ".cursor",
    "vendor",
    "Pods",
    ".gradle",
    ".terraform",
}

DEFAULT_IGNORE_GLOBS = [
    "*.pyc",
    "*.pyo",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "*.generated.*",
    "*.g.dart",
]

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z",
    ".exe", ".dll", ".so", ".dylib", ".o", ".a",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".db", ".sqlite", ".sqlite3",
}


def load_gitignore(root: Path) -> list[str]:
    patterns: list[str] = []
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return patterns
    for line in gitignore.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        patterns.append(line)
    return patterns


def should_ignore(
    path: Path,
    root: Path,
    extra_globs: list[str] | None = None,
    gitignore_patterns: list[str] | None = None,
) -> bool:
    rel = path.relative_to(root)
    parts = rel.parts

    for part in parts:
        if part in DEFAULT_IGNORE_DIRS:
            return True

    rel_str = str(rel).replace("\\", "/")

    for glob in DEFAULT_IGNORE_GLOBS:
        if fnmatch.fnmatch(rel.name, glob) or fnmatch.fnmatch(rel_str, glob):
            return True

    if extra_globs:
        for glob in extra_globs:
            if fnmatch.fnmatch(rel.name, glob) or fnmatch.fnmatch(rel_str, glob):
                return True

    if gitignore_patterns:
        for pattern in gitignore_patterns:
            if _matches_gitignore(rel_str, pattern):
                return True

    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True

    return False


def _matches_gitignore(rel_path: str, pattern: str) -> bool:
    pattern = pattern.strip()
    if not pattern:
        return False
    if pattern.startswith("!"):
        return False
    if pattern.startswith("/"):
        pattern = pattern[1:]
    if pattern.endswith("/"):
        pattern = pattern[:-1]
        return pattern in rel_path.split("/")
    return fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(
        rel_path.split("/")[-1], pattern
    )
