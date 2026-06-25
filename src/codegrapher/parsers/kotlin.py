"""Kotlin parser with call-flow extraction."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.parsers.base import BaseParser, ParseResult
from codegrapher.parsers.calls import extract_calls_line_based

IMPORT_RE = re.compile(r"""^import\s+([\w.]+)""")
CLASS_RE = re.compile(r"""(?:data\s+)?class\s+(\w+)""")
FUN_RE = re.compile(r"""fun\s+(?:<[^>]+>\s+)?(\w+)\s*\(""")
EXTENDS_RE = re.compile(r"""class\s+(\w+)\s*:\s*([\w.]+)""")
INTERFACE_RE = re.compile(r"""interface\s+(\w+)""")

ENTRYPOINT_NAMES = {
    "MainActivity.kt", "Application.kt", "App.kt",
    "Main.kt", "MainViewModel.kt",
}


class KotlinParser(BaseParser):
    extensions = {".kt", ".kts"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)

        for line in content.splitlines():
            m = IMPORT_RE.match(line.strip())
            if m:
                result.imports.append(m.group(1))

        symbols, calls, extends = extract_calls_line_based(
            content,
            func_patterns=[FUN_RE],
            class_patterns=[CLASS_RE, INTERFACE_RE],
            extends_patterns=[EXTENDS_RE],
        )
        result.symbols = symbols
        result.calls = calls
        result.extends = extends
        result.exports = list(dict.fromkeys(
            s.name.split(".")[0] for s in symbols if not s.name.split(".")[-1].startswith("_")
        ))

        for sym in symbols:
            bare = sym.name.split(".")[-1]
            if bare in {"onCreate", "main", "run", "invoke"}:
                result.flow_roots.append(sym.name)

        return result


parser = KotlinParser()
