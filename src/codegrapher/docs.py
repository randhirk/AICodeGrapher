"""Scan and parse markdown docs for architecture & best practices."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from codegrapher.ignore import load_gitignore, should_ignore

# Filename / path signals (higher = more important for the graph)
FILE_SCORES: dict[str, int] = {
    "architecture": 120,
    "architectural": 120,
    "design": 100,
    "adr": 95,
    "contributing": 90,
    "conventions": 85,
    "best-practices": 85,
    "best_practices": 85,
    "standards": 80,
    "agents": 75,
    "claude": 70,
    "integration": 65,
    "development": 60,
    "docs/": 50,
    "readme": 35,
}

SKIP_DOC_NAMES = {
    "changelog", "license", "code_of_conduct", "security",
    "pull_request_template", "issue_template",
}

CATEGORY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("architecture", re.compile(r"architect|system\s+design|overview|structure|component|layer|module", re.I)),
    ("best-practice", re.compile(r"best\s*practices?|guideline|standard|principle|recommend", re.I)),
    ("convention", re.compile(r"convention|style\s+guide|naming|formatting|lint", re.I)),
    ("design", re.compile(r"design\s+decision|\badr\b|rfc|pattern", re.I)),
    ("integration", re.compile(r"integrat|getting\s+started|setup|workflow|development", re.I)),
    ("agents", re.compile(r"\bagents?\b|cursor|claude|codex|\bllm\b|ai\s+tool", re.I)),
    ("testing", re.compile(r"testing|test\s+plan|qa\b|coverage", re.I)),
    ("security", re.compile(r"security|auth|permission|threat", re.I)),
]

PATH_REF_RE = re.compile(
    r"""[`'"]?([\w./-]+(?:\.\w+)?)[`'"]?""",
)
CODE_PATH_RE = re.compile(
    r"""(?:^|[\s(])([\w][\w./-]*\.(?:py|js|ts|tsx|jsx|go|rs|kt|java|swift|cs|rb|php|vue|svelte))(?:[\s):,]|$)""",
    re.MULTILINE,
)

MAX_SECTION_CHARS = 600
MAX_SECTIONS = 40
MAX_BULLETS = 8


@dataclass
class DocSection:
    id: str
    source: str
    title: str
    category: str
    content: str
    line_start: int | None = None
    score: int = 0
    related_modules: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "category": self.category,
            "content": self.content,
        }
        if self.line_start is not None:
            d["line"] = self.line_start
        if self.related_modules:
            d["related"] = self.related_modules
        return d


def scan_markdown_docs(
    root: Path,
    module_paths: set[str],
    *,
    extra_ignore: list[str] | None = None,
) -> list[DocSection]:
    root = root.resolve()
    gitignore = load_gitignore(root)
    candidates: list[tuple[int, str, str]] = []

    for path in sorted(root.rglob("*.md")):
        if not path.is_file():
            continue
        if should_ignore(path, root, extra_ignore, gitignore):
            continue
        rel = str(path.relative_to(root)).replace("\\", "/")
        if _should_skip_doc(rel):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        file_score = _file_score(rel)
        candidates.append((file_score, rel, content))

    candidates.sort(key=lambda x: -x[0])

    sections: list[DocSection] = []
    seen_ids: set[str] = set()

    for file_score, rel, content in candidates:
        for section in _parse_markdown(rel, content, file_score):
            section.related_modules = _find_related_modules(section.content, module_paths)
            if section.id in seen_ids:
                continue
            seen_ids.add(section.id)
            sections.append(section)
            if len(sections) >= MAX_SECTIONS:
                return _rank_sections(sections)

    return _rank_sections(sections)


def _should_skip_doc(rel_path: str) -> bool:
    name = Path(rel_path).stem.lower()
    if name in SKIP_DOC_NAMES:
        return True
    lower = rel_path.lower()
    return any(skip in lower for skip in ("/node_modules/", "/vendor/", "/.github/issu"))


def _file_score(rel_path: str) -> int:
    lower = rel_path.lower()
    score = 10
    for key, pts in FILE_SCORES.items():
        if key in lower:
            score = max(score, pts)
    return score


def _parse_markdown(rel_path: str, content: str, file_score: int) -> list[DocSection]:
    sections: list[DocSection] = []
    chunks = _split_sections(content)

    for title, body, line_start in chunks:
        category = _categorize(title, body, rel_path)
        if category == "other" and file_score < 40:
            continue
        if category == "other" and not _looks_like_guidance(body):
            continue
        if _is_readme(rel_path) and category in ("other", "integration") and file_score < 60:
            continue

        compressed = _compress_body(body)
        if not compressed or compressed.strip() == "[code example]":
            continue
        if compressed.count("[code example]") >= 2 and len(compressed) < 80:
            continue

        section_id = f"doc:{rel_path}#{_slug(title)}"
        score = file_score + _section_score(title, category)
        sections.append(
            DocSection(
                id=section_id,
                source=rel_path,
                title=title,
                category=category,
                content=compressed,
                line_start=line_start,
                score=score,
            )
        )

    if not sections and file_score >= 50:
        compressed = _compress_body(content)
        if compressed:
            title = Path(rel_path).stem.replace("_", " ").replace("-", " ").title()
            category = _categorize(title, content, rel_path)
            sections.append(
                DocSection(
                    id=f"doc:{rel_path}#root",
                    source=rel_path,
                    title=title,
                    category=category if category != "other" else "guide",
                    content=compressed[:MAX_SECTION_CHARS],
                    line_start=1,
                    score=file_score,
                )
            )

    return sections


def _split_sections(content: str) -> list[tuple[str, str, int]]:
    lines = content.splitlines()
    chunks: list[tuple[str, str, int]] = []
    current_title = "Introduction"
    current_lines: list[str] = []
    current_start = 1

    for i, line in enumerate(lines, start=1):
        heading = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if heading:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    chunks.append((current_title, body, current_start))
            current_title = heading.group(2).strip()
            current_start = i
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append((current_title, body, current_start))

    return chunks


def _categorize(title: str, body: str, rel_path: str) -> str:
    text = f"{title} {body[:500]}"
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(text):
            return category
    lower_path = rel_path.lower()
    if "architecture" in lower_path or "adr" in lower_path:
        return "architecture"
    if "contributing" in lower_path or "convention" in lower_path:
        return "convention"
    return "other"


def _looks_like_guidance(body: str) -> bool:
    lower = body.lower()
    signals = ("must", "should", "always", "never", "prefer", "avoid", "use ", "do not", "pattern")
    bullets = body.count("\n- ") + body.count("\n* ")
    return bullets >= 2 or any(s in lower for s in signals)


def _compress_body(body: str) -> str:
    lines: list[str] = []
    in_code = False
    code_lines = 0

    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if in_code:
                code_lines = 0
            continue
        if in_code:
            code_lines += 1
            if code_lines == 1:
                lines.append("[code example]")
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(("-", "*", "1.", "2.", "3.")):
            lines.append(stripped.lstrip("-* ").strip() if stripped[0] in "-*" else stripped)
        elif len(lines) < 3 and not stripped.startswith("|"):
            lines.append(stripped)

    text = " | ".join(lines[:MAX_BULLETS])
    if len(text) > MAX_SECTION_CHARS:
        text = text[: MAX_SECTION_CHARS - 3] + "..."
    return text


def _section_score(title: str, category: str) -> int:
    cat_scores = {
        "architecture": 50,
        "best-practice": 45,
        "convention": 40,
        "design": 40,
        "agents": 35,
        "integration": 30,
        "testing": 25,
        "security": 25,
        "guide": 15,
        "other": 5,
    }
    return cat_scores.get(category, 5) + (10 if len(title) < 40 else 0)


def _rank_sections(sections: list[DocSection]) -> list[DocSection]:
    return sorted(sections, key=lambda s: -s.score)[:MAX_SECTIONS]


def _is_readme(rel_path: str) -> bool:
    return Path(rel_path).name.lower() in {"readme.md", "readme.mdx"}


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    return re.sub(r"[\s_]+", "-", slug).strip("-") or "section"


def _find_related_modules(content: str, module_paths: set[str]) -> list[str]:
    found: list[str] = []
    normalized_modules = {m.replace("\\", "/") for m in module_paths}

    for match in CODE_PATH_RE.finditer(content):
        ref = match.group(1).replace("\\", "/")
        if ref in normalized_modules:
            found.append(ref)
            continue
        for mod in normalized_modules:
            if mod.endswith(ref) or ref.endswith(mod):
                found.append(mod)

    for match in PATH_REF_RE.finditer(content):
        ref = match.group(1).replace("\\", "/")
        if ref in normalized_modules:
            found.append(ref)

    return list(dict.fromkeys(found))[:10]
