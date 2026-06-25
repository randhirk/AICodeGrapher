"""Data models for the Code Graph Format (CGF)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from codegrapher.docs import DocSection


class NodeKind(str, Enum):
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    INTERFACE = "interface"
    TYPE = "type"
    DIRECTORY = "directory"
    DOCUMENT = "document"


class EdgeKind(str, Enum):
    IMPORT = "import"
    CALL = "call"
    EXTENDS = "extends"
    IMPLEMENTS = "implements"
    CONTAINS = "contains"
    DOCUMENTS = "documents"


@dataclass
class Symbol:
    name: str
    kind: NodeKind
    line: int | None = None
    signature: str | None = None


@dataclass
class GraphNode:
    id: str
    kind: NodeKind
    lang: str | None = None
    path: str | None = None
    exports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    lines: int | None = None
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "kind": self.kind.value}
        if self.lang:
            d["lang"] = self.lang
        if self.path:
            d["path"] = self.path
        if self.exports:
            d["exports"] = self.exports
        if self.symbols:
            d["symbols"] = [
                {
                    "name": s.name,
                    "kind": s.kind.value,
                    **({"line": s.line} if s.line else {}),
                    **({"sig": s.signature} if s.signature else {}),
                }
                for s in self.symbols
            ]
        if self.lines is not None:
            d["lines"] = self.lines
        if self.summary:
            d["summary"] = self.summary
        return d


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: EdgeKind
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"from": self.source, "to": self.target, "kind": self.kind.value}
        if self.label:
            d["label"] = self.label
        return d


@dataclass
class CodeGraph:
    """Root graph document — CGF v3 (adds docs, call flow)."""

    CGF_VERSION = 3

    repo: str
    root: str
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)
    entrypoints: list[str] = field(default_factory=list)
    flow_roots: list[str] = field(default_factory=list)
    flow_paths: list[list[str]] = field(default_factory=list)
    docs: list[DocSection] = field(default_factory=list)
    ignore_patterns: list[str] = field(default_factory=list)

    @property
    def stats(self) -> dict[str, int]:
        modules = sum(1 for n in self.nodes if n.kind == NodeKind.MODULE)
        code_symbols = sum(
            1 for n in self.nodes if n.kind not in (NodeKind.MODULE, NodeKind.DOCUMENT)
        )
        symbols = code_symbols or sum(
            len(n.symbols) + len(n.exports) for n in self.module_nodes()
        )
        import_edges = sum(1 for e in self.edges if e.kind == EdgeKind.IMPORT)
        call_edges = sum(1 for e in self.edges if e.kind == EdgeKind.CALL)
        doc_edges = sum(1 for e in self.edges if e.kind == EdgeKind.DOCUMENTS)
        return {
            "files": modules,
            "nodes": len(self.nodes),
            "symbols": symbols,
            "edges": len(self.edges),
            "imports": import_edges,
            "calls": call_edges,
            "flows": len(self.flow_paths),
            "docs": len(self.docs),
            "doc_links": doc_edges,
        }

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "cgf": self.CGF_VERSION,
            "repo": self.repo,
            "root": self.root,
            "stats": self.stats,
            "entrypoints": self.entrypoints,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }
        if self.flow_roots:
            data["flow_roots"] = self.flow_roots
        if self.flow_paths:
            data["flow_paths"] = self.flow_paths
        if self.docs:
            data["docs"] = [d.to_dict() for d in self.docs]
        return data

    def node_by_id(self, node_id: str) -> GraphNode | None:
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def module_nodes(self) -> list[GraphNode]:
        return [n for n in self.nodes if n.kind == NodeKind.MODULE]

    def symbol_nodes(self) -> list[GraphNode]:
        return [n for n in self.nodes if n.kind not in (NodeKind.MODULE, NodeKind.DOCUMENT)]

    def doc_nodes(self) -> list[GraphNode]:
        return [n for n in self.nodes if n.kind == NodeKind.DOCUMENT]

    def imports_of(self, module_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == module_id and e.kind == EdgeKind.IMPORT]

    def imported_by(self, module_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == module_id and e.kind == EdgeKind.IMPORT]

    def calls_from(self, symbol_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == symbol_id and e.kind == EdgeKind.CALL]

    def calls_to(self, symbol_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == symbol_id and e.kind == EdgeKind.CALL]
