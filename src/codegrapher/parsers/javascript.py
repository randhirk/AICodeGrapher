"""JavaScript / TypeScript parser (regex-based, fast, no deps)."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import BaseParser, ParseResult
from codegrapher.parsers.calls import extract_calls_line_based

IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w*{}\s,]+\s+from\s+)?|import\s*\(|require\s*\()\s*['"]([^'"]+)['"]""",
    re.MULTILINE,
)
EXPORT_NAMED_RE = re.compile(
    r"""export\s+(?:async\s+)?(?:function|class|const|let|var|enum|interface|type)\s+(\w+)""",
    re.MULTILINE,
)
EXPORT_LIST_RE = re.compile(r"""export\s*\{\s*([^}]+)\s*\}""", re.MULTILINE)
EXPORT_DEFAULT_RE = re.compile(
    r"""export\s+default\s+(?:async\s+)?(?:function|class)\s+(\w+)""",
    re.MULTILINE,
)
FUNC_RE = re.compile(
    r"""(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)""",
    re.MULTILINE,
)
CLASS_RE = re.compile(r"""(?:export\s+)?class\s+(\w+)""", re.MULTILINE)
INTERFACE_RE = re.compile(r"""(?:export\s+)?interface\s+(\w+)""", re.MULTILINE)
TYPE_RE = re.compile(r"""(?:export\s+)?type\s+(\w+)\s*=""", re.MULTILINE)
ARROW_EXPORT_RE = re.compile(
    r"""export\s+(?:const|let)\s+(\w+)\s*=\s*(?:async\s*)?\(""",
    re.MULTILINE,
)

METHOD_RE = re.compile(r"""(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{""", re.MULTILINE)

ENTRYPOINT_NAMES = {
    "index.ts", "index.tsx", "index.js", "index.jsx",
    "main.ts", "main.js", "app.ts", "app.tsx", "server.ts", "server.js",
}


class JavaScriptParser(BaseParser):
    extensions = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)

        for match in IMPORT_RE.finditer(content):
            imp = match.group(1)
            if not imp.startswith("."):
                result.imports.append(_pkg_root(imp))
            else:
                result.imports.append(imp)

        for match in EXPORT_NAMED_RE.finditer(content):
            result.exports.append(match.group(1))

        for match in EXPORT_LIST_RE.finditer(content):
            names = [n.strip().split(" as ")[0].strip() for n in match.group(1).split(",")]
            result.exports.extend(n for n in names if n and n != "default")

        for match in EXPORT_DEFAULT_RE.finditer(content):
            result.exports.append(match.group(1))

        for match in FUNC_RE.finditer(content):
            name = match.group(1)
            if not name.startswith("_"):
                result.symbols.append(
                    Symbol(
                        name=name,
                        kind=NodeKind.FUNCTION,
                        line=content[: match.start()].count("\n") + 1,
                        signature=f"function {name}({match.group(2)})",
                    )
                )

        for match in CLASS_RE.finditer(content):
            name = match.group(1)
            result.symbols.append(
                Symbol(name=name, kind=NodeKind.CLASS, line=content[: match.start()].count("\n") + 1)
            )

        for match in INTERFACE_RE.finditer(content):
            name = match.group(1)
            result.symbols.append(
                Symbol(name=name, kind=NodeKind.INTERFACE, line=content[: match.start()].count("\n") + 1)
            )

        for match in TYPE_RE.finditer(content):
            name = match.group(1)
            result.symbols.append(
                Symbol(name=name, kind=NodeKind.TYPE, line=content[: match.start()].count("\n") + 1)
            )

        for match in ARROW_EXPORT_RE.finditer(content):
            name = match.group(1)
            if name not in result.exports:
                result.exports.append(name)

        extra_symbols, calls, _ = extract_calls_line_based(
            content,
            func_patterns=[FUNC_RE, METHOD_RE],
            class_patterns=[CLASS_RE, INTERFACE_RE],
        )
        for sym in extra_symbols:
            if not any(s.name == sym.name for s in result.symbols):
                result.symbols.append(sym)
        result.calls = calls

        if "main(" in content or "bootstrap(" in content:
            result.flow_roots.append("main")

        result.exports = list(dict.fromkeys(result.exports))
        return result


def _pkg_root(imp: str) -> str:
    if imp.startswith("@"):
        parts = imp.split("/")
        return "/".join(parts[:2]) if len(parts) >= 2 else imp
    return imp.split("/")[0]


parser = JavaScriptParser()
