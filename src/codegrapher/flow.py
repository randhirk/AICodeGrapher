"""Build execution-flow paths from call edges."""

from __future__ import annotations

from collections import deque

from codegrapher.models import CodeGraph, EdgeKind, NodeKind


def build_flow_paths(
    graph: CodeGraph,
    *,
    max_depth: int = 8,
    max_paths: int = 25,
    max_branching: int = 4,
) -> tuple[list[str], list[list[str]]]:
    """Return (flow_roots, flow_paths) from call graph."""
    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges:
        if edge.kind != EdgeKind.CALL:
            continue
        adjacency.setdefault(edge.source, []).append(edge.target)

    roots = list(graph.flow_roots)
    if not roots:
        roots = _guess_roots(graph)

    paths: list[list[str]] = []
    seen_paths: set[tuple[str, ...]] = set()

    for root in roots:
        if root not in {n.id for n in graph.symbol_nodes()}:
            resolved = _resolve_root(graph, root)
            if resolved:
                root = resolved
            else:
                continue

        for path in _walk_paths(root, adjacency, max_depth=max_depth, max_branching=max_branching):
            key = tuple(path)
            if key in seen_paths:
                continue
            seen_paths.add(key)
            paths.append(path)
            if len(paths) >= max_paths:
                return roots, paths

    return roots, paths


def _guess_roots(graph: CodeGraph) -> list[str]:
    roots: list[str] = []
    entry_modules = set(graph.entrypoints)

    for node in graph.symbol_nodes():
        if node.kind != NodeKind.FUNCTION:
            continue
        bare = node.id.split("::")[-1]
        module = node.path or ""
        if bare in {"main", "run", "start", "bootstrap", "handler", "onCreate"}:
            roots.append(node.id)
        elif module in entry_modules and bare in {"default", "init"}:
            roots.append(node.id)

    if not roots:
        for node in graph.symbol_nodes():
            if node.kind == NodeKind.FUNCTION and graph.calls_from(node.id):
                roots.append(node.id)
                if len(roots) >= 5:
                    break

    return list(dict.fromkeys(roots))[:10]


def _resolve_root(graph: CodeGraph, name: str) -> str | None:
    matches = [n.id for n in graph.symbol_nodes() if n.id.endswith(f"::{name}") or n.id == name]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        return matches[0]
    return None


def _walk_paths(
    root: str,
    adjacency: dict[str, list[str]],
    *,
    max_depth: int,
    max_branching: int,
) -> list[list[str]]:
    results: list[list[str]] = []
    queue: deque[tuple[str, list[str]]] = deque([(root, [root])])

    while queue:
        current, path = queue.popleft()
        if len(path) >= 2:
            results.append(path)

        if len(path) >= max_depth:
            continue

        callees = adjacency.get(current, [])[:max_branching]
        for callee in callees:
            if callee in path:
                continue
            queue.append((callee, path + [callee]))

    return results
