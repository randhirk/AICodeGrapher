"""Generic fallback parser for other source files."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import BaseParser, ParseResult

# C/C++, Java, C#, Ruby, PHP patterns
CLASS_PATTERNS = [
    re.compile(r"""(?:public\s+)?class\s+(\w+)"""),
    re.compile(r"""struct\s+(\w+)"""),
]
FUNC_PATTERNS = [
    re.compile(r"""(?:public|private|protected|static|async|def|func)\s+\w*\s*(\w+)\s*\("""),
    re.compile(r"""def\s+(\w+)\s*\("""),
    re.compile(r"""function\s+(\w+)\s*\("""),
]
IMPORT_PATTERNS = [
    re.compile(r"""#include\s*[<"]([^>"]+)[>"]"""),
    re.compile(r"""import\s+([\w.]+)"""),
    re.compile(r"""require\s+['"]([^'"]+)['"]"""),
    re.compile(r"""use\s+([\w\\]+)"""),
]

SOURCE_EXTENSIONS = {
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".cs", ".rb", ".php",
    ".scala", ".clj",
    ".lua", ".r", ".R",
    ".sh", ".bash", ".zsh",
    ".sql",
    ".vue", ".svelte",
}


class GenericParser(BaseParser):
    extensions = SOURCE_EXTENSIONS

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult()

        for pattern in IMPORT_PATTERNS:
            for match in pattern.finditer(content):
                result.imports.append(match.group(1))

        for pattern in CLASS_PATTERNS:
            for match in pattern.finditer(content):
                name = match.group(1)
                if not name.startswith("_"):
                    result.exports.append(name)
                    result.symbols.append(
                        Symbol(
                            name=name,
                            kind=NodeKind.CLASS,
                            line=content[: match.start()].count("\n") + 1,
                        )
                    )

        for pattern in FUNC_PATTERNS:
            for match in pattern.finditer(content):
                name = match.group(1)
                if name not in {"if", "for", "while", "switch", "catch"} and not name.startswith("_"):
                    if name not in result.exports:
                        result.exports.append(name)
                        result.symbols.append(
                            Symbol(
                                name=name,
                                kind=NodeKind.FUNCTION,
                                line=content[: match.start()].count("\n") + 1,
                            )
                        )

        result.exports = list(dict.fromkeys(result.exports))
        result.imports = list(dict.fromkeys(result.imports))
        return result


parser = GenericParser()
