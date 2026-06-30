# AICodeGrapher

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
[![Open Source](https://img.shields.io/badge/Open%20Source-Yes-blue.svg)](https://github.com/randhirk/AICodeGrapher)

**Open source · MIT licensed · contributions welcome**

Compact code graphs for AI coding tools. Scan any repository and produce a token-efficient map that Cursor, Claude Code, and Codex can use to navigate without reading every file.

> **Repository:** [github.com/randhirk/AICodeGrapher](https://github.com/randhirk/AICodeGrapher)  
> **Guide:** [Medium article](https://medium.com/@randhirkr_34313/how-to-give-cursor-claude-and-codex-a-map-of-your-codebase-without-burning-tokens-97f54ad78b2f) · source: [docs/medium-article.md](docs/medium-article.md)  
> **Contributing:** see [CONTRIBUTING.md](CONTRIBUTING.md) · **Conduct:** [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## Why

AI assistants burn context reading full repos. A **code graph** gives them:

- Module layout and public exports
- Import / dependency edges
- Entry points and hub modules
- Call graph and execution flow paths
- Architecture docs compressed from your markdown
- ~10–50× fewer tokens than dumping source trees

## Quick start

### 1. Install

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher

# macOS ships an old pip — upgrade first so editable install works
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

If `pip` is not found, always use `python3 -m pip` instead of `pip`.

Verify:

```bash
codegraph --version
# or, if codegraph is not on PATH:
python3 -m codegrapher --version
```

### 2. Scan your project

```bash
# From the repo you want to map (writes to .codegraph/)
codegraph

# Or scan any other directory
codegraph /path/to/your-app -o .codegraph

# Preview without writing files (paste into any AI chat)
codegraph --print compact
```

If `codegraph` is not found after install, use the module form (works the same):

```bash
python3 -m codegrapher
python3 -m codegrapher /path/to/your-app -o .codegraph
python3 -m codegrapher --print compact
```

### Troubleshooting (`zsh: command not found`)

| Error | Fix |
|-------|-----|
| `zsh: command not found: pip` | Use `python3 -m pip` instead of `pip`. |
| `zsh: command not found: codegraph` | Run `python3 -m codegrapher` (same flags), or add Python’s script directory to PATH (below). |
| `editable mode currently requires a setuptools-based build` | Upgrade pip: `python3 -m pip install --upgrade pip`, then retry `python3 -m pip install -e .` |
| `python3: command not found` | Install Python 3.9+ from [python.org](https://www.python.org/downloads/) or Homebrew: `brew install python` |

**Add `codegraph` to PATH (zsh, one-time):**

```bash
# macOS — replace 3.9 with your Python version (python3 --version)
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

On Linux the path is often `~/.local/bin`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Run without installing to PATH:**

```bash
cd AICodeGrapher
PYTHONPATH=src python3 -m codegrapher /path/to/your-app --print compact
```

After `python3 -m pip install -e .`, `python3 -m codegrapher` works from any directory.

See [INTEGRATION.md](INTEGRATION.md) for full setup with Cursor, Claude Code, and Codex.

## Output formats

| Format | File | Use case |
|--------|------|----------|
| **compact** | `codegraph.txt` | Paste into any AI chat — smallest token footprint |
| **json** | `codegraph.json` | Tools, CI, custom integrations (CGF schema) |
| **mermaid** | `codegraph.mmd` | Human-readable diagram |
| **cursor** | `.cursor/rules/codegraph.mdc` | Auto-inject in Cursor |
| **claude** | `CLAUDE.md.graph` | Append to `CLAUDE.md` for Claude Code |
| **codex** | `AGENTS.md.graph` | Append to `AGENTS.md` for Codex agents |

## Example compact output

```text
# CGF/3 myapp | 24 files | 87 symbols | 120 edges (45 calls, 8 flows, 12 docs)

## architecture & practices
[architecture] ARCHITECTURE.md — System Design
  API layer -> service layer | Never access DB from controllers

## entrypoints
src/main.py, src/api/routes.py

## execution flow
cli.py::main -> builder.py::build_graph -> scanner.py::scan_repository

## modules
src/auth/login.py [python, 84L] (login, logout) -> models/user.py, db.py
src/api/routes.py [python, 120L] (UserRouter, PostRouter) -> auth/login.py, models/*
src/models/user.py [python, 45L] (User, UserCreate) -> db.py

## call graph
auth.py::login -> auth.py::verify
auth.py::login -> auth.py::load_user

## hubs (most imported)
models/user.py (6 importers)
db.py (5 importers)
```

## CGF — Code Graph Format

Structured JSON for programmatic use:

```json
{
  "cgf": 3,
  "repo": "myapp",
  "stats": { "files": 24, "symbols": 87, "edges": 120 },
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

## CLI reference

```
codegraph [PATH] [options]

  -o, --output DIR     Output directory (default: .codegraph)
  -f, --format FMT     json | compact | mermaid | cursor | claude | codex | all
  --print FMT          Print to stdout instead of writing files
  --ignore GLOB        Extra ignore patterns (repeatable)
  --max-files N        Limit files scanned
  --no-docs            Skip markdown architecture/docs ingestion
  -q, --quiet          Suppress progress
```

Use `python3 -m codegrapher` anywhere `codegraph` is shown if the command is not on PATH.

## Integration

See [INTEGRATION.md](INTEGRATION.md) for step-by-step setup with **Cursor**, **Claude Code**, and **Codex**.

### Cursor

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .codegraph
cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

### Claude Code

```bash
codegraph -f claude -o .codegraph
touch CLAUDE.md
cat .codegraph/CLAUDE.md.graph >> CLAUDE.md
```

### Codex / AGENTS.md

```bash
codegraph -f codex -o .codegraph
touch AGENTS.md
cat .codegraph/AGENTS.md.graph >> AGENTS.md
```

### CI (regenerate on every push)

```yaml
- run: pip install git+https://github.com/randhirk/AICodeGrapher.git && codegraph -f compact -o .codegraph
- uses: actions/upload-artifact@v4
  with:
    name: codegraph
    path: .codegraph/codegraph.txt
```

## Development

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher
python3 -m pip install --upgrade pip
python3 -m pip install -e ".[dev]"
pytest
ruff check src tests
```

## Contributing

We welcome contributions from everyone! Whether you fix a parser bug, add language support, improve docs, or report issues — thank you.

1. Read [CONTRIBUTING.md](CONTRIBUTING.md)
2. Fork the repo and open a PR against `main`
3. Follow the [Code of Conduct](CODE_OF_CONDUCT.md)

**Good first contributions:**

- Improve Kotlin / Swift / Java call-graph accuracy
- Add examples under `examples/`
- Fix false positives in call or doc extraction
- Improve README and integration guides

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and distribute with attribution.
