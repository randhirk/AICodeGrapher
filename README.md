# CodeGrapher

**Compact code graphs for AI coding tools.** Scan any repository and produce a token-efficient map that Cursor, Claude Code, and Codex can use to navigate without reading every file.

## Why

AI assistants burn context reading full repos. A **code graph** gives them:

- Module layout and public exports
- Import / dependency edges
- Entry points and hub modules
- ~10–50× fewer tokens than dumping source trees

## Quick start

```bash
pip install -e .

# Scan current repo, write all formats to .codegraph/
codegraph

# Print compact graph to stdout (paste into any chat)
codegraph --print compact

# Scan another project
codegraph /path/to/your-app -o .codegraph
```

## Output formats

| Format | File | Use case |
|--------|------|----------|
| **compact** | `codegraph.txt` | Paste into any AI chat — smallest token footprint |
| **json** | `codegraph.json` | Tools, CI, custom integrations (CGF v1 schema) |
| **mermaid** | `codegraph.mmd` | Human-readable diagram |
| **cursor** | `.cursor/rules/codegraph.mdc` | Auto-inject in Cursor |
| **claude** | `CLAUDE.md.graph` | Append to `CLAUDE.md` for Claude Code |
| **codex** | `AGENTS.md.graph` | Append to `AGENTS.md` for Codex agents |

## Example compact output

```text
# CGF/1 myapp | 24 files | 87 symbols | 41 edges

## entrypoints
src/main.py, src/api/routes.py

## modules
src/auth/login.py [python, 84L] (login, logout) -> models/user.py, db.py
src/api/routes.py [python, 120L] (UserRouter, PostRouter) -> auth/login.py, models/*
src/models/user.py [python, 45L] (User, UserCreate) -> db.py

## hubs (most imported)
models/user.py (6 importers)
db.py (5 importers)
```

## CGF — Code Graph Format v1

Structured JSON for programmatic use:

```json
{
  "cgf": 1,
  "repo": "myapp",
  "stats": { "files": 24, "symbols": 87, "edges": 41 },
  "entrypoints": ["src/main.py"],
  "nodes": [
    { "id": "src/auth.py", "kind": "module", "lang": "python", "exports": ["login"], "lines": 84 }
  ],
  "edges": [
    { "from": "src/api.py", "to": "src/auth.py", "kind": "import" }
  ]
}
```

## Supported languages

| Language | Extensions | Parser |
|----------|------------|--------|
| Python | `.py` | AST |
| JavaScript / TypeScript | `.js`, `.ts`, `.jsx`, `.tsx` | Regex |
| Go | `.go` | Regex |
| Rust | `.rs` | Regex |
| Java, C#, Ruby, PHP, C/C++, … | various | Generic fallback |

Respects `.gitignore` and skips `node_modules`, `venv`, build artifacts, etc.

## Call graph & execution flow (CGF v3)

CodeGrapher builds a **directional call graph** and **execution flow paths**, and ingests **markdown docs** (architecture, best practices, conventions) into the graph.

### Documentation in the graph

All `.md` files are scanned. Priority is given to:

- `ARCHITECTURE.md`, `docs/**`, `CONTRIBUTING.md`, `AGENTS.md`, `INTEGRATION.md`
- Sections about architecture, design, best practices, conventions, testing, security

```text
## architecture & practices
[architecture] ARCHITECTURE.md — System Design
  API layer -> service layer | Never access DB from controllers

[best-practice] CONTRIBUTING.md — Code Style
  Always write tests | Use type hints
```

Doc sections link to code files when paths are referenced (`src/api/routes.py`).

- **Function-level nodes** — `module.py::login`, `Main.kt::onCreate`
- **Call edges** — `login -> verify -> check_password`
- **Flow paths** — traced from entrypoints (`main`, `onCreate`, `__main__`) via BFS
- **Inheritance** — `extends` / `implements` where detected

```text
## execution flow
cli.py::main -> builder.py::build_graph -> scanner.py::scan_repository

## call graph
auth.py::login -> auth.py::verify
auth.py::login -> auth.py::load_user
```

## CLI reference

```
codegraph [PATH] [options]

  -o, --output DIR     Output directory (default: .codegraph)
  -f, --format FMT     json | compact | mermaid | cursor | claude | codex | all
  --print FMT          Print to stdout instead of writing files
  --ignore GLOB        Extra ignore patterns (repeatable)
  --max-files N        Limit files scanned
  -q, --quiet          Suppress progress
```

## Integration

See [INTEGRATION.md](INTEGRATION.md) for step-by-step setup with **Cursor**, **Claude Code**, and **Codex**.

### Cursor (one-liner)

```bash
codegraph -f cursor && cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

### Claude Code

```bash
codegraph -f claude && cat .codegraph/CLAUDE.md.graph >> CLAUDE.md
```

### Codex / AGENTS.md

```bash
codegraph -f codex && cat .codegraph/AGENTS.md.graph >> AGENTS.md
```

### CI (regenerate on every push)

```yaml
- run: pip install codegrapher && codegraph -f compact -o .codegraph
- uses: actions/upload-artifact@v4
  with:
    name: codegraph
    path: .codegraph/codegraph.txt
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## License

MIT — see [LICENSE](LICENSE).
