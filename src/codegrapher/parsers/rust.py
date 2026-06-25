"""Rust parser (regex-based)."""

from __future__ import annotations

import re
from pathlib import Path

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import BaseParser, ParseResult

USE_RE = re.compile(r"""use\s+([\w:]+)(?:::|;|\s*\{)""")
MOD_RE = re.compile(r"""mod\s+(\w+)\s*;""")
PUB_FN_RE = re.compile(r"""pub\s+(?:async\s+)?fn\s+(\w+)""")
PUB_STRUCT_RE = re.compile(r"""pub\s+struct\s+(\w+)""")
PUB_ENUM_RE = re.compile(r"""pub\s+enum\s+(\w+)""")
PUB_TRAIT_RE = re.compile(r"""pub\s+trait\s+(\w+)""")


class RustParser(BaseParser):
    extensions = {".rs"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name == "main.rs" or path.name == "lib.rs")

        for match in USE_RE.finditer(content):
            result.imports.append(match.group(1).split("::")[0])

        for match in MOD_RE.finditer(content):
            result.imports.append(match.group(1))

        for pattern, kind in (
            (PUB_FN_RE, NodeKind.FUNCTION),
            (PUB_STRUCT_RE, NodeKind.CLASS),
            (PUB_ENUM_RE, NodeKind.TYPE),
            (PUB_TRAIT_RE, NodeKind.INTERFACE),
        ):
            for match in pattern.finditer(content):
                name = match.group(1)
                result.exports.append(name)
                result.symbols.append(
                    Symbol(name=name, kind=kind, line=content[: match.start()].count("\n") + 1)
                )

        result.exports = list(dict.fromkeys(result.exports))
        return result


parser = RustParser()
