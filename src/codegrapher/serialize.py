"""Serialize CodeGraph to AI-friendly formats."""

from __future__ import annotations

import json
from pathlib import Path

from codegrapher.models import CodeGraph, EdgeKind


def to_json(graph: CodeGraph, *, indent: int | None = 2) -> str:
    return json.dumps(graph.to_dict(), indent=indent, ensure_ascii=False)


def to_compact(graph: CodeGraph) -> str:
    """Ultra-compact text format optimized for LLM context windows."""
    stats = graph.stats
    lines: list[str] = [
        f"# CGF/{graph.CGF_VERSION} {graph.repo} | {stats['files']} files "
        f"| {stats['symbols']} symbols | {stats['edges']} edges "
        f"({stats.get('calls', 0)} calls, {stats.get('flows', 0)} flows, {stats.get('docs', 0)} docs)",
        "",
        "Use this graph as a map of the repository. Read specific files only when needed.",
        "Sections: docs (architecture), modules (imports), call graph, flow paths.",
        "",
    ]

    if graph.docs:
        lines.append("## architecture & practices")
        by_category: dict[str, list] = {}
        for doc in graph.docs:
            by_category.setdefault(doc.category, []).append(doc)

        category_order = [
            "architecture", "design", "best-practice", "convention",
            "integration", "agents", "testing", "security", "guide", "other",
        ]
        shown = 0
        for cat in category_order:
            for doc in by_category.get(cat, []):
                related = ""
                if doc.related_modules:
                    related = f" -> {', '.join(_short_path(m) for m in doc.related_modules[:4])}"
                lines.append(f"[{doc.category}] {doc.source} — {doc.title}{related}")
                lines.append(f"  {doc.content}")
                shown += 1
                if shown >= 25:
                    break
            if shown >= 25:
                break
        lines.append("")

    if graph.entrypoints:
        lines.append("## entrypoints")
        lines.append(", ".join(graph.entrypoints))
        lines.append("")

    if graph.flow_roots:
        lines.append("## flow roots")
        lines.append(", ".join(_short_sym(r) for r in graph.flow_roots[:10]))
        lines.append("")

    if graph.flow_paths:
        lines.append("## execution flow")
        for path in graph.flow_paths[:20]:
            lines.append(" -> ".join(_short_sym(s) for s in path))
        lines.append("")

    lines.append("## modules")
    for node in sorted(graph.module_nodes(), key=lambda n: n.id):
        exports = _format_exports(node)
        imports = graph.imports_of(node.id)
        import_str = ""
        if imports:
            import_str = " -> " + ", ".join(_short_path(t) for t in imports[:8])
            if len(imports) > 8:
                import_str += f" (+{len(imports) - 8})"

        meta = f" [{node.lang}, {node.lines}L]" if node.lines else f" [{node.lang}]"
        lines.append(f"{node.id}{meta}{exports}{import_str}")

    hubs = _hub_modules(graph, top_n=8)
    if hubs:
        lines.append("")
        lines.append("## hubs (most imported)")
        for mod, count in hubs:
            lines.append(f"{mod} ({count} importers)")

    lines.append("")
    lines.append("## import edges")
    seen: set[tuple[str, str]] = set()
    for edge in graph.edges:
        if edge.kind != EdgeKind.IMPORT:
            continue
        key = (edge.source, edge.target)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"{_short_path(edge.source)} -> {_short_path(edge.target)}")

    call_edges = [e for e in graph.edges if e.kind == EdgeKind.CALL]
    if call_edges:
        lines.append("")
        lines.append("## call graph")
        seen_calls: set[tuple[str, str]] = set()
        for edge in call_edges:
            key = (edge.source, edge.target)
            if key in seen_calls:
                continue
            seen_calls.add(key)
            lines.append(f"{_short_sym(edge.source)} -> {_short_sym(edge.target)}")

    return "\n".join(lines) + "\n"


def to_mermaid(graph: CodeGraph, *, max_nodes: int = 40) -> str:
    """Mermaid flowchart for human preview."""
    modules = graph.module_nodes()
    if len(modules) > max_nodes:
        ranked = sorted(
            modules,
            key=lambda n: len(graph.imported_by(n.id)) + len(graph.imports_of(n.id)),
            reverse=True,
        )
        modules = ranked[:max_nodes]

    allowed = {n.id for n in modules}
    lines = ["```mermaid", "flowchart LR"]

    for node in modules:
        label = Path(node.id).name
        if node.exports:
            label += f"<br/>{', '.join(node.exports[:3])}"
        safe_id = _mermaid_id(node.id)
        lines.append(f'  {safe_id}["{label}"]')

    for edge in graph.edges:
        if edge.kind != EdgeKind.IMPORT:
            continue
        if edge.source in allowed and edge.target in allowed:
            lines.append(f"  {_mermaid_id(edge.source)} --> {_mermaid_id(edge.target)}")

    lines.append("```")
    return "\n".join(lines) + "\n"


def to_cursor_rule(graph: CodeGraph) -> str:
    """Snippet for .cursor/rules or AGENTS.md."""
    compact = to_compact(graph)
    return (
        "---\n"
        "description: Repository code graph for navigation — generated by CodeGrapher\n"
        "alwaysApply: true\n"
        "---\n\n"
        "Before exploring this codebase, use this graph to understand structure. "
        "Prefer reading only the files relevant to the task.\n\n"
        f"{compact}"
    )


def to_claude_md(graph: CodeGraph) -> str:
    """CLAUDE.md appendix with graph context."""
    return (
        "# Codebase Graph\n\n"
        "This section was generated by [CodeGrapher](https://github.com/codegrapher/codegrapher). "
        "Use it to navigate the repo without reading every file.\n\n"
        f"```\n{to_compact(graph)}```\n"
    )


def to_codex_agents(graph: CodeGraph) -> str:
    """AGENTS.md section for OpenAI Codex / similar agents."""
    return (
        "## Repository map (CodeGrapher)\n\n"
        "Token-saving navigation graph. Consult before opening files.\n\n"
        f"```text\n{to_compact(graph)}```\n"
    )


def write_outputs(
    graph: CodeGraph,
    out_dir: Path,
    *,
    formats: set[str] | None = None,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = formats or {"json", "compact", "mermaid", "cursor", "claude", "codex"}
    written: dict[str, Path] = {}

    mapping = {
        "json": ("codegraph.json", lambda: to_json(graph)),
        "compact": ("codegraph.txt", lambda: to_compact(graph)),
        "mermaid": ("codegraph.mmd", lambda: to_mermaid(graph)),
        "cursor": (".cursor/rules/codegraph.mdc", lambda: to_cursor_rule(graph)),
        "claude": ("CLAUDE.md.graph", lambda: to_claude_md(graph)),
        "codex": ("AGENTS.md.graph", lambda: to_codex_agents(graph)),
    }

    for fmt in formats:
        if fmt not in mapping:
            continue
        rel_path, serializer = mapping[fmt]
        path = out_dir / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serializer(), encoding="utf-8")
        written[fmt] = path

    return written


def _format_exports(node) -> str:
    names = node.exports or [s.name for s in node.symbols[:5]]
    if not names:
        return ""
    shown = names[:6]
    suffix = f" (+{len(names) - 6})" if len(names) > 6 else ""
    return f" ({', '.join(shown)}{suffix})"


def _short_path(path: str) -> str:
    parts = path.split("/")
    return parts[-1] if len(parts) <= 2 else "/".join(parts[-2:])


def _short_sym(symbol_id: str) -> str:
    if "::" not in symbol_id:
        return _short_path(symbol_id)
    module, name = symbol_id.rsplit("::", 1)
    return f"{_short_path(module)}::{name}"


def _hub_modules(graph: CodeGraph, top_n: int = 8) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for edge in graph.edges:
        if edge.kind == EdgeKind.IMPORT:
            counts[edge.target] = counts.get(edge.target, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:top_n]


def _mermaid_id(path: str) -> str:
    return "n_" + path.replace("/", "_").replace(".", "_").replace("-", "_")
