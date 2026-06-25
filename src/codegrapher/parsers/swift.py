"""Swift parser with call-flow extraction."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.parsers.base import BaseParser, InheritanceSite, ParseResult
from codegrapher.parsers.calls import extract_calls_line_based

IMPORT_RE = re.compile(r"""^import\s+([\w.]+)""")
CLASS_RE = re.compile(r"""(?:class|struct|actor)\s+(\w+)""")
PROTOCOL_RE = re.compile(r"""protocol\s+(\w+)""")
FUN_RE = re.compile(r"""func\s+(\w+)\s*\(""")
EXTENDS_RE = re.compile(r"""(?:class|struct)\s+(\w+)\s*:\s*([\w,\s]+)""")

ENTRYPOINT_NAMES = {"App.swift", "main.swift", "AppDelegate.swift", "SceneDelegate.swift"}


class SwiftParser(BaseParser):
    extensions = {".swift"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)

        for line in content.splitlines():
            m = IMPORT_RE.match(line.strip())
            if m:
                result.imports.append(m.group(1))

        symbols, calls, extends = extract_calls_line_based(
            content,
            func_patterns=[FUN_RE],
            class_patterns=[CLASS_RE, PROTOCOL_RE],
        )

        for m in EXTENDS_RE.finditer(content):
            child = m.group(1)
            for parent in m.group(2).split(","):
                parent = parent.strip()
                if parent:
                    extends.append(InheritanceSite(child=child, parent=parent))

        result.symbols = symbols
        result.calls = calls
        result.extends = extends
        result.exports = list(dict.fromkeys(s.name.split(".")[0] for s in symbols))

        for sym in symbols:
            if sym.name in {"main", "application", "body"} or sym.name.endswith(".body"):
                result.flow_roots.append(sym.name)

        if "@main" in content:
            for sym in symbols:
                if sym.name.endswith(".body") or sym.kind.value == "class":
                    result.flow_roots.append(sym.name)
                    break

        return result


parser = SwiftParser()
