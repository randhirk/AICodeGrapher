"""Shared call-site extraction helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import CallSite, InheritanceSite


@dataclass
class _Scope:
    name: str
    kind: str  # "function" | "class"
    start_line: int
    end_line: int


def extract_calls_line_based(
    content: str,
    *,
    func_patterns: list[re.Pattern[str]],
    class_patterns: list[re.Pattern[str]],
    extends_patterns: list[re.Pattern[str]] | None = None,
    call_pattern: re.Pattern[str] | None = None,
) -> tuple[list[Symbol], list[CallSite], list[InheritanceSite]]:
    """Extract symbols and calls using line-scoped heuristics."""
    lines = content.splitlines()
    symbols: list[Symbol] = []
    calls: list[CallSite] = []
    extends: list[InheritanceSite] = []
    scopes: list[_Scope] = []

    call_re = call_pattern or re.compile(r"""\b([A-Za-z_][\w]*)\s*\(""")

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*"):
            continue

        for pat in class_patterns:
            m = pat.search(line)
            if m:
                name = m.group(1)
                symbols.append(Symbol(name=name, kind=NodeKind.CLASS, line=i))
                scopes.append(_Scope(name, "class", i, len(lines)))
                break

        for pat in func_patterns:
            m = pat.search(line)
            if m:
                name = m.group(1)
                class_prefix = _current_class(scopes, i)
                qname = f"{class_prefix}.{name}" if class_prefix else name
                symbols.append(Symbol(name=qname, kind=NodeKind.FUNCTION, line=i))
                scopes.append(_Scope(qname, "function", i, len(lines)))
                break

        if extends_patterns:
            for pat in extends_patterns:
                m = pat.search(line)
                if m:
                    extends.append(InheritanceSite(child=m.group(1), parent=m.group(2)))

    scopes.sort(key=lambda s: s.start_line)
    for i, line in enumerate(lines, start=1):
        scope = _innermost_scope(scopes, i)
        if not scope or scope.kind != "function":
            continue
        for m in call_re.finditer(line):
            callee = m.group(1)
            if callee in _SKIP_CALLEES:
                continue
            calls.append(CallSite(caller=scope.name, callee=callee, line=i))

    return symbols, calls, extends


def _current_class(scopes: list[_Scope], line: int) -> str | None:
    cls = None
    for s in scopes:
        if s.kind == "class" and s.start_line <= line:
            cls = s.name
    return cls


def _innermost_scope(scopes: list[_Scope], line: int) -> _Scope | None:
    matches = [s for s in scopes if s.start_line <= line]
    return matches[-1] if matches else None


_SKIP_CALLEES = {
    "if", "for", "while", "switch", "catch", "return", "new", "typeof", "instanceof",
    "print", "println", "console", "require", "import", "export", "class", "fun",
    "def", "function", "async", "await", "try", "except", "raise", "pass", "len",
    "str", "int", "float", "bool", "list", "dict", "set", "tuple", "super",
    "self", "this", "null", "true", "false", "nil", "Some", "Ok", "Err",
    "resolve", "join", "append", "extend", "format", "strip", "split", "replace",
    "get", "set", "add", "put", "run", "open", "close", "read", "write",
}
