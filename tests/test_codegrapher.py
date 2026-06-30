"""Tests for CodeGrapher."""

import subprocess
import sys
from pathlib import Path

from codegrapher.builder import build_graph, sym_id
from codegrapher.models import EdgeKind, NodeKind
from codegrapher.parsers.python import PythonParser
from codegrapher.scanner import scan_repository
from codegrapher.serialize import to_compact, to_json


SAMPLE_PY = '''
import os
from pathlib import Path

from models.user import User

def login(username: str) -> bool:
  user = load_user(username)
  return verify(user)

def load_user(username: str):
  return User(username)

def verify(user) -> bool:
  return check_password(user)

class AuthService:
  def authenticate(self):
    self.validate()
    return login("admin")

  def validate(self):
    pass
'''


FLOW_SAMPLE = '''
def main():
    start_server()

def start_server():
    handle_request()

def handle_request():
    process()
'''


def test_python_parser_extracts_symbols():
    parser = PythonParser()
    result = parser.parse(Path("auth.py"), SAMPLE_PY, "auth.py")
    assert "login" in result.exports
    assert "AuthService" in result.exports
    assert "models.user" in result.imports


def test_python_parser_extracts_calls():
    parser = PythonParser()
    result = parser.parse(Path("auth.py"), SAMPLE_PY, "auth.py")
    callers = {c.caller for c in result.calls}
    assert "login" in callers
    callees = {c.callee for c in result.calls}
    assert "load_user" in callees or "verify" in callees


def test_call_graph_and_flow(tmp_path):
    app = tmp_path / "app.py"
    app.write_text(FLOW_SAMPLE)
    scanned = scan_repository(tmp_path)
    graph = build_graph(tmp_path, scanned)

    call_edges = [e for e in graph.edges if e.kind == EdgeKind.CALL]
    assert len(call_edges) >= 2

    assert any(len(p) >= 2 for p in graph.flow_paths)
    text = to_compact(graph)
    assert "## call graph" in text
    assert "## execution flow" in text


def test_cross_module_call_resolution(tmp_path):
    svc = tmp_path / "service.py"
    svc.write_text("def verify():\n    return True\n")
    app = tmp_path / "app.py"
    app.write_text("from service import verify\n\ndef main():\n    verify()\n")
    graph = build_graph(tmp_path, scan_repository(tmp_path))

    main_id = sym_id("app.py", "main")
    verify_id = sym_id("service.py", "verify")
    assert any(e.source == main_id and e.target == verify_id for e in graph.edges if e.kind == EdgeKind.CALL)


def test_kotlin_parser_calls(tmp_path):
    kt = tmp_path / "Main.kt"
    kt.write_text(
        "class Main {\n"
        "    fun onCreate() {\n"
        "        loadData()\n"
        "    }\n"
        "    fun loadData() {}\n"
        "}\n"
    )
    graph = build_graph(tmp_path, scan_repository(tmp_path))
    call_edges = [e for e in graph.edges if e.kind == EdgeKind.CALL]
    assert len(call_edges) >= 1


def test_scan_self_repo():
    root = Path(__file__).resolve().parents[1]
    scanned = scan_repository(root)
    assert len(scanned) >= 5
    ids = {s.rel_path for s in scanned}
    assert any("cli.py" in p for p in ids)


def test_build_graph_has_edges():
    root = Path(__file__).resolve().parents[1]
    scanned = scan_repository(root)
    graph = build_graph(root, scanned)
    assert graph.stats["files"] >= 5
    assert graph.repo == root.name
    assert any(n.kind == NodeKind.MODULE for n in graph.nodes)
    assert any(e.kind == EdgeKind.CALL for e in graph.edges)


def test_serialize_compact_contains_header():
    root = Path(__file__).resolve().parents[1]
    graph = build_graph(root, scan_repository(root))
    text = to_compact(graph)
    assert text.startswith("# CGF/3")
    assert "## modules" in text
    assert "## call graph" in text


def test_serialize_json_valid():
    root = Path(__file__).resolve().parents[1]
    graph = build_graph(root, scan_repository(root))
    import json
    data = json.loads(to_json(graph))
    assert data["cgf"] == 3
    assert "nodes" in data
    assert "edges" in data
    assert "flow_paths" in data


def test_docs_in_graph(tmp_path):
    arch = tmp_path / "ARCHITECTURE.md"
    arch.write_text(
        "# System Architecture\n\n"
        "- API layer calls service layer\n"
        "- Never access DB from controllers\n"
        "- See `app.py` for entrypoint\n\n"
        "## Best Practices\n\n"
        "- Always write tests\n"
        "- Use type hints\n"
    )
    app = tmp_path / "app.py"
    app.write_text("def main():\n    run()\ndef run():\n    pass\n")
    graph = build_graph(tmp_path, scan_repository(tmp_path))

    assert len(graph.docs) >= 2
    assert any(d.category == "architecture" for d in graph.docs)
    assert any(d.category == "best-practice" for d in graph.docs)
    assert any(
        e.kind == EdgeKind.DOCUMENTS and e.target == "app.py"
        for e in graph.edges
    )
    text = to_compact(graph)
    assert "## architecture & practices" in text


def test_docs_scan_self_repo():
    root = Path(__file__).resolve().parents[1]
    graph = build_graph(root, scan_repository(root))
    assert len(graph.docs) >= 2
    assert any("README" in d.source or "INTEGRATION" in d.source for d in graph.docs)


def test_cli_main(tmp_path):
    sample = tmp_path / "app.py"
    sample.write_text("def main():\n    run()\ndef run():\n    pass\n")
    from codegrapher.cli import main
    code = main([str(tmp_path), "--print", "compact", "-q"])
    assert code == 0


def test_python_m_codegrapher(tmp_path):
    sample = tmp_path / "app.py"
    sample.write_text("def main():\n    pass\n")
    result = subprocess.run(
        [sys.executable, "-m", "codegrapher", str(tmp_path), "--print", "compact", "-q"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("# CGF/")
