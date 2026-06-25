"""Java parser with call-flow extraction."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.parsers.base import BaseParser, InheritanceSite, ParseResult
from codegrapher.parsers.calls import extract_calls_line_based

IMPORT_RE = re.compile(r"""^import\s+(?:static\s+)?([\w.]+)""")
CLASS_RE = re.compile(r"""(?:public\s+)?(?:abstract\s+)?class\s+(\w+)""")
INTERFACE_RE = re.compile(r"""(?:public\s+)?interface\s+(\w+)""")
METHOD_RE = re.compile(
    r"""(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\("""
)
EXTENDS_RE = re.compile(r"""class\s+(\w+)\s+extends\s+(\w+)""")
IMPLEMENTS_RE = re.compile(r"""class\s+(\w+)\s+implements\s+([\w,\s]+)""")

ENTRYPOINT_NAMES = {"Main.java", "Application.java", "App.java"}


class JavaParser(BaseParser):
    extensions = {".java"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)

        for line in content.splitlines():
            m = IMPORT_RE.match(line.strip())
            if m:
                result.imports.append(m.group(1))

        symbols, calls, extends = extract_calls_line_based(
            content,
            func_patterns=[METHOD_RE],
            class_patterns=[CLASS_RE, INTERFACE_RE],
            extends_patterns=[EXTENDS_RE],
        )

        for m in IMPLEMENTS_RE.finditer(content):
            child = m.group(1)
            for parent in m.group(2).split(","):
                parent = parent.strip()
                if parent:
                    extends.append(InheritanceSite(child=child, parent=parent))

        result.symbols = symbols
        result.calls = calls
        result.extends = extends
        result.exports = list(dict.fromkeys(s.name.split(".")[0] for s in symbols))

        if "public static void main" in content:
            result.flow_roots.append("main")

        return result


parser = JavaParser()
