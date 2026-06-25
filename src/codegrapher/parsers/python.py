"""Python AST parser with call-graph extraction."""

from __future__ import annotations

import ast
from pathlib import Path

from codegrapher.models import NodeKind, Symbol
from codegrapher.parsers.base import BaseParser, CallSite, InheritanceSite, ParseResult

ENTRYPOINT_NAMES = {"main.py", "__main__.py", "app.py", "wsgi.py", "asgi.py", "manage.py"}


class PythonParser(BaseParser):
    extensions = {".py", ".pyw"}

    def parse(self, path: Path, content: str, rel_path: str) -> ParseResult:
        result = ParseResult(is_entrypoint=path.name in ENTRYPOINT_NAMES)
        try:
            tree = ast.parse(content, filename=rel_path)
        except SyntaxError:
            return result

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result.imports.append(node.module)

        symbols, calls, extends, flow_roots = _collect_symbols_calls(tree)
        result.symbols = symbols
        result.calls = calls
        result.extends = extends
        result.flow_roots = flow_roots

        for sym in symbols:
            top = sym.name.split(".")[0]
            if not top.startswith("_") and top not in result.exports:
                if sym.kind == NodeKind.CLASS or "." not in sym.name:
                    result.exports.append(top if sym.kind == NodeKind.CLASS else sym.name)

        if path.name == "__init__.py":
            result.exports = [s.name.split(".")[0] for s in symbols if not s.name.startswith("_")]

        result.exports = list(dict.fromkeys(result.exports))
        return result


def _collect_symbols_calls(tree: ast.Module) -> tuple[list[Symbol], list[CallSite], list[InheritanceSite], list[str]]:
    symbols: list[Symbol] = []
    calls: list[CallSite] = []
    extends: list[InheritanceSite] = []
    flow_roots: list[str] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            symbols.append(Symbol(name=node.name, kind=NodeKind.CLASS, line=node.lineno))
            for base in node.bases:
                parent = _name_from_expr(base)
                if parent:
                    extends.append(InheritanceSite(child=node.name, parent=parent))
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    qname = f"{node.name}.{item.name}"
                    symbols.append(
                        Symbol(
                            name=qname,
                            kind=NodeKind.FUNCTION,
                            line=item.lineno,
                            signature=_func_sig(item),
                        )
                    )
                    calls.extend(_calls_in_function(item, qname, class_name=node.name))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                Symbol(
                    name=node.name,
                    kind=NodeKind.FUNCTION,
                    line=node.lineno,
                    signature=_func_sig(node),
                )
            )
            calls.extend(_calls_in_function(node, node.name))
        elif isinstance(node, ast.If) and _is_main_guard(node):
            for sub in node.body:
                if isinstance(sub, ast.Expr) and isinstance(sub.value, ast.Call):
                    root = _callee_name(sub.value.func)
                    if root:
                        flow_roots.append(root)

    if not flow_roots:
        for sym in symbols:
            if sym.name == "main" or sym.name.endswith(".main"):
                flow_roots.append(sym.name)

    return symbols, calls, extends, flow_roots


def _calls_in_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    caller: str,
    *,
    class_name: str | None = None,
) -> list[CallSite]:
    sites: list[CallSite] = []
    for child in ast.walk(node):
        if child is node:
            continue
        if isinstance(child, ast.Call):
            callee = _callee_name(child.func, class_name=class_name)
            if callee:
                sites.append(CallSite(caller=caller, callee=callee, line=getattr(child, "lineno", None)))
    return sites


def _callee_name(node: ast.AST, *, class_name: str | None = None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "self" and class_name:
            return f"{class_name}.{node.attr}"
        return None
    return None


def _name_from_expr(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if not isinstance(test, ast.Compare):
        return False
    if not isinstance(test.left, ast.Name) or test.left.id != "__name__":
        return False
    for op, comparator in zip(test.ops, test.comparators):
        if isinstance(op, ast.Eq) and isinstance(comparator, ast.Constant):
            return comparator.value == "__main__"
    return False


def _func_sig(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = [a.arg for a in node.args.args if a.arg != "self"]
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{prefix} {node.name}({', '.join(args)})"


parser = PythonParser()
