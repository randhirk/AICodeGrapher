"""Parser interface and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from codegrapher.models import Symbol


@dataclass
class CallSite:
    caller: str
    callee: str
    line: int | None = None


@dataclass
class InheritanceSite:
    child: str
    parent: str


@dataclass
class ParseResult:
    exports: list[str] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    calls: list[CallSite] = field(default_factory=list)
    extends: list[InheritanceSite] = field(default_factory=list)
    flow_roots: list[str] = field(default_factory=list)
    is_entrypoint: bool = False


class BaseParser(ABC):
    extensions: set[str] = set()

    @abstractmethod
    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        ...


_PARSERS: dict[str, BaseParser] = {}


def register_parser(parser: BaseParser) -> None:
    for ext in parser.extensions:
        _PARSERS[ext] = parser


def get_parser(path: Path) -> BaseParser | None:
    return _PARSERS.get(path.suffix.lower())


# Register built-in parsers on import
def _register_builtin() -> None:
    from codegrapher.parsers import generic, go, java, javascript, kotlin, python, rust, swift

    for mod in (python, javascript, go, rust, kotlin, java, swift, generic):
        register_parser(mod.parser)


_register_builtin()
