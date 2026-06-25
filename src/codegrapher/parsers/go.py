"""Go parser (regex-based)."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import BaseParser, ParseResult

IMPORT_RE = re.compile(r"""import\s+(?:\(\s*([\s\S]*?)\s*\)|"([^"]+)")""")
IMPORT_LINE_RE = re.compile(r"""["']([^"']+)["']""")
FUNC_RE = re.compile(r"""func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(""")
TYPE_RE = re.compile(r"""type\s+(\w+)\s+(?:struct|interface)""")

ENTRYPOINT_NAMES = {"main.go"}


class GoParser(BaseParser):
    extensions = {".go"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)

        for match in IMPORT_RE.finditer(content):
            block = match.group(1) or match.group(2) or ""
            for imp in IMPORT_LINE_RE.findall(block):
                pkg = imp.rsplit("/", 1)[-1]
                result.imports.append(pkg if not imp.startswith(".") else imp)

        for match in FUNC_RE.finditer(content):
            name = match.group(1)
            if name[0].isupper():
                result.exports.append(name)
                result.symbols.append(
                    Symbol(
                        name=name,
                        kind=NodeKind.FUNCTION,
                        line=content[: match.start()].count("\n") + 1,
                    )
                )

        for match in TYPE_RE.finditer(content):
            name = match.group(1)
            if name[0].isupper():
                result.exports.append(name)
                result.symbols.append(
                    Symbol(
                        name=name,
                        kind=NodeKind.CLASS,
                        line=content[: match.start()].count("\n") + 1,
                    )
                )

        result.exports = list(dict.fromkeys(result.exports))
        return result


parser = GoParser()
