"""Build a CodeGraph from scanned files."""

from __future__ import annotations

from pathlib import Path

from codegrapher.docs import scan_markdown_docs
from codegrapher.flow import build_flow_paths
from codegrapher.models import CodeGraph, EdgeKind, GraphEdge, GraphNode, NodeKind
from codegrapher.scanner import ScannedFile


def sym_id(module: str, name: str) -> str:
    return f"{module}::{name}"


def build_graph(
    root: Path,
    scanned: list[ScannedFile],
    *,
    include_docs: bool = True,
    extra_ignore: list[str] | None = None,
) -> CodeGraph:
    root = root.resolve()
    repo_name = root.name
    graph = CodeGraph(repo=repo_name, root=str(root))

    module_index, package_index, dotted_index = _build_indexes(scanned)

    for sf in scanned:
        graph.nodes.append(
            GraphNode(
                id=sf.rel_path,
                kind=NodeKind.MODULE,
                lang=sf.lang,
                path=sf.rel_path,
                exports=sf.parse_result.exports[:20],
                symbols=sf.parse_result.symbols[:30],
                lines=sf.lines,
            )
        )
        if sf.parse_result.is_entrypoint:
            graph.entrypoints.append(sf.rel_path)

    import_map: dict[str, list[str]] = {}
    for sf in scanned:
        targets: list[str] = []
        for raw_import in sf.parse_result.imports:
            target = _resolve_import(raw_import, sf, module_index, package_index, dotted_index)
            if target and target != sf.rel_path:
                targets.append(target)
                graph.edges.append(
                    GraphEdge(source=sf.rel_path, target=target, kind=EdgeKind.IMPORT)
                )
        import_map[sf.rel_path] = list(dict.fromkeys(targets))

    resolver = _CallResolver(scanned, import_map)
    seen_edges: set[tuple[str, str, str]] = set()

    for sf in scanned:
        module = sf.rel_path
        for sym in sf.parse_result.symbols:
            sid = sym_id(module, sym.name)
            graph.nodes.append(
                GraphNode(
                    id=sid,
                    kind=sym.kind,
                    lang=sf.lang,
                    path=module,
                    summary=sym.signature,
                )
            )
            key = (module, sid, EdgeKind.CONTAINS.value)
            if key not in seen_edges:
                seen_edges.add(key)
                graph.edges.append(
                    GraphEdge(source=module, target=sid, kind=EdgeKind.CONTAINS)
                )

        for site in sf.parse_result.extends:
            child_id = sym_id(module, site.child)
            parent_id = resolver.resolve(module, site.child, site.parent) or sym_id(module, site.parent)
            edge_key = (child_id, parent_id, EdgeKind.EXTENDS.value)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                graph.edges.append(
                    GraphEdge(source=child_id, target=parent_id, kind=EdgeKind.EXTENDS)
                )

        for site in sf.parse_result.calls:
            source_id = sym_id(module, site.caller)
            target_id = resolver.resolve(module, site.caller, site.callee)
            if not target_id or target_id == source_id:
                continue
            edge_key = (source_id, target_id, EdgeKind.CALL.value)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                graph.edges.append(
                    GraphEdge(source=source_id, target=target_id, kind=EdgeKind.CALL)
                )

        for root_name in sf.parse_result.flow_roots:
            rid = resolver.resolve(module, root_name, root_name) or sym_id(module, root_name)
            if graph.node_by_id(rid):
                graph.flow_roots.append(rid)

    graph.entrypoints = list(dict.fromkeys(graph.entrypoints))
    if not graph.entrypoints:
        graph.entrypoints = _guess_entrypoints(scanned)

    roots, paths = build_flow_paths(graph)
    if roots:
        graph.flow_roots = list(dict.fromkeys(roots))
    graph.flow_paths = paths

    if include_docs:
        _attach_docs(graph, root, scanned, extra_ignore)

    return graph


def _attach_docs(
    graph: CodeGraph,
    root: Path,
    scanned: list[ScannedFile],
    extra_ignore: list[str] | None,
) -> None:
    module_paths = {sf.rel_path for sf in scanned}
    sections = scan_markdown_docs(root, module_paths, extra_ignore=extra_ignore)
    graph.docs = sections
    seen_edges: set[tuple[str, str, str]] = set()

    for section in sections:
        graph.nodes.append(
            GraphNode(
                id=section.id,
                kind=NodeKind.DOCUMENT,
                path=section.source,
                lang=section.category,
                summary=section.content,
            )
        )
        key = (section.source, section.id, EdgeKind.CONTAINS.value)
        if key not in seen_edges:
            seen_edges.add(key)
            graph.edges.append(
                GraphEdge(
                    source=section.source,
                    target=section.id,
                    kind=EdgeKind.CONTAINS,
                    label=section.title,
                )
            )
        for mod in section.related_modules:
            edge_key = (section.id, mod, EdgeKind.DOCUMENTS.value)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                graph.edges.append(
                    GraphEdge(
                        source=section.id,
                        target=mod,
                        kind=EdgeKind.DOCUMENTS,
                        label=section.category,
                    )
                )


class _CallResolver:
    def __init__(self, scanned: list[ScannedFile], import_map: dict[str, list[str]]):
        self.local_symbols: dict[str, dict[str, str]] = {}
        self.global_index: dict[str, list[str]] = {}
        self.import_map = import_map

        for sf in scanned:
            module = sf.rel_path
            local: dict[str, str] = {}
            for sym in sf.parse_result.symbols:
                sid = sym_id(module, sym.name)
                local[sym.name] = sid
                bare = sym.name.split(".")[-1]
                self.global_index.setdefault(bare, []).append(sid)
            self.local_symbols[module] = local

    def resolve(self, source_module: str, caller: str, callee: str) -> str | None:
        local = self.local_symbols.get(source_module, {})

        if callee in local:
            return local[callee]

        if "." in caller:
            cls = caller.rsplit(".", 1)[0]
            qualified = f"{cls}.{callee.split('.')[-1]}"
            if qualified in local:
                return local[qualified]

        bare = callee.split(".")[-1]
        if bare in local:
            return local[bare]

        candidates: list[str] = []
        for mod in self.import_map.get(source_module, []):
            mod_local = self.local_symbols.get(mod, {})
            if callee in mod_local:
                candidates.append(mod_local[callee])
            elif bare in mod_local:
                candidates.append(mod_local[bare])
            else:
                for name, sid in mod_local.items():
                    if name == bare or name.endswith(f".{bare}"):
                        candidates.append(sid)

        candidates = list(dict.fromkeys(candidates))
        if len(candidates) == 1:
            return candidates[0]

        global_matches = self.global_index.get(bare, [])
        if len(global_matches) == 1:
            return global_matches[0]

        return None


def _build_indexes(scanned: list[ScannedFile]) -> tuple[dict[str, str], dict[str, list[str]], dict[str, str]]:
    module_index: dict[str, str] = {}
    package_index: dict[str, list[str]] = {}
    dotted_index: dict[str, str] = {}

    for sf in scanned:
        module_index[sf.rel_path] = sf.rel_path
        stem = Path(sf.rel_path).stem
        package_index.setdefault(stem, []).append(sf.rel_path)
        parent = str(Path(sf.rel_path).parent)
        if parent != ".":
            package_index.setdefault(parent.replace("\\", "/"), []).append(sf.rel_path)
        for dotted in _dotted_names(sf.rel_path):
            dotted_index[dotted] = sf.rel_path

    return module_index, package_index, dotted_index


def _resolve_import(
    raw: str,
    source: ScannedFile,
    module_index: dict[str, str],
    package_index: dict[str, list[str]],
    dotted_index: dict[str, str],
) -> str | None:
    raw = raw.strip().strip('"').strip("'")

    if raw in module_index:
        return raw
    if raw in dotted_index:
        return dotted_index[raw]

    if raw.startswith("."):
        base = Path(source.rel_path).parent
        candidates = [
            str((base / raw).with_suffix("")).replace("\\", "/"),
            str((base / raw)).replace("\\", "/"),
            str((base / raw / "index")).replace("\\", "/"),
        ]
        for ext in ("", ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".kt", ".java", ".swift"):
            for cand in candidates:
                path = cand + ext if ext else cand
                if path in module_index:
                    return path
                index = f"{cand}/index{ext}" if ext else f"{cand}/index"
                if index in module_index:
                    return index

    stem = Path(raw).stem
    if stem in package_index:
        matches = package_index[stem]
        if len(matches) == 1:
            return matches[0]
        same_dir = [
            m for m in matches
            if str(Path(m).parent) == str(Path(source.rel_path).parent)
        ]
        if len(same_dir) == 1:
            return same_dir[0]

    py_path = raw.replace(".", "/") + ".py"
    if py_path in module_index:
        return py_path

    py_init = raw.replace(".", "/") + "/__init__.py"
    if py_init in module_index:
        return py_init

    partial = [
        m for m in module_index
        if m.endswith(f"/{stem}.py") or m.endswith(f"/{stem}.ts") or m.endswith(f"/{stem}.kt")
    ]
    if len(partial) == 1:
        return partial[0]

    return None


def _dotted_names(rel_path: str) -> list[str]:
    path = Path(rel_path)
    if path.name == "__init__.py":
        base = str(path.parent).replace("\\", "/")
        names = [base.replace("/", ".")] if base != "." else []
    else:
        base = str(path.with_suffix("")).replace("\\", "/")
        names = [base.replace("/", ".")]

    extra: list[str] = []
    for name in names:
        if name.startswith("src."):
            extra.append(name[4:])
    return names + extra


def _guess_entrypoints(scanned: list[ScannedFile]) -> list[str]:
    names = {
        "main.py", "__main__.py", "app.py", "index.ts", "index.js",
        "main.go", "main.rs", "lib.rs", "server.ts", "manage.py",
        "MainActivity.kt", "Main.java", "App.swift",
    }
    return [sf.rel_path for sf in scanned if Path(sf.rel_path).name in names][:5]
