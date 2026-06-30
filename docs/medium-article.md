# How to Give Cursor, Claude, and Codex a Map of Your Codebase — Without Burning Tokens

> **Source for the [Medium post](https://medium.com/@randhirkr_34313/how-to-give-cursor-claude-and-codex-a-map-of-your-codebase-without-burning-tokens-97f54ad78b2f).**  
> Copy sections into the Medium editor to update the live article.

A practical guide to [AICodeGrapher](https://github.com/randhirk/AICodeGrapher), the open-source tool that turns any repository into a compact code graph AI assistants can actually use.

If you've used Cursor, Claude Code, or Codex on a real project, you've probably hit the same wall:

You ask the AI to fix a bug in authentication. It starts reading files. Then more files. Then it re-reads half the repo. Your context window fills up. The answer gets slower, vaguer, and more expensive.

The problem isn't the model. It's navigation.

AI coding tools are powerful — but they're blind until they open a file. On a 200-file codebase, that's like exploring a city without a map.

AICodeGrapher fixes that. It scans your repository once and produces a compact code graph: modules, imports, call flow, architecture docs, and entry points — all in a format any LLM can understand in a few hundred to a few thousand tokens.

It's open source, MIT licensed, and built for developers who want smarter AI — not bigger bills.

---

## The idea in 30 seconds

Instead of dumping your entire project into an AI chat, you give it a map:

```
api/routes.py (UserRouter) → auth/login.py → models/user.py
main() → start_server() → handle_request() → login()
```

The AI knows where to look before it reads a single line of source code.

That's the whole philosophy behind **CGF (Code Graph Format)** — a structured, token-efficient representation of your repo.

---

## What AICodeGrapher actually builds

AICodeGrapher doesn't replace reading code. It makes reading code targeted.

For any repository, it generates four layers:

### 1. Structure graph (imports & modules)

Which files exist, what they export, and who imports whom.

```
src/api/routes.py [python, 120L] (UserRouter, PostRouter) -> auth/login.py, models/user.py
src/auth/login.py [python, 84L] (login, logout) -> models/user.py, db.py
```

### 2. Call graph (execution flow)

Function-level edges: who calls whom.

```
auth.py::login -> auth.py::verify
auth.py::login -> auth.py::load_user
```

### 3. Flow paths (from entrypoints)

Traced execution routes starting at `main`, `onCreate`, or `if __name__ == "__main__"`:

```
cli.py::main -> builder.py::build_graph -> scanner.py::scan_repository
```

### 4. Architecture & best practices (from markdown)

It reads your `ARCHITECTURE.md`, `CONTRIBUTING.md`, `docs/`, and other `.md` files — then compresses the important parts into the graph:

```
[architecture] ARCHITECTURE.md — System Design
  API layer -> service layer | Never access DB from controllers

[best-practice] CONTRIBUTING.md — Code Style
  Always write tests | Use type hints
```

So the AI gets your team's rules, not just your file tree.

---

## Why this saves tokens (and money)

| Approach | Typical token cost |
|----------|-------------------|
| Full directory tree + file listings | 15,000–100,000+ |
| AICodeGrapher compact graph | 300–3,000 |

For most teams, that's a **10–50× reduction** in context used just for navigation.

Less context on maps = more context for the actual problem.

---

## Quick start (5 minutes)

### Install

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher

# macOS ships an old pip — upgrade first so editable install works
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

> **Tip:** If `pip` is not found, use `python3 -m pip` instead of `pip`.

### Scan your project

```bash
# From the repo you want to map (writes to .codegraph/)
codegraph

# Or scan any other directory
codegraph /path/to/your-app -o .codegraph
```

If `codegraph` is not found after install, use:

```bash
python3 -m codegrapher
python3 -m codegrapher /path/to/your-app -o .codegraph
```

### Preview the graph

```bash
codegraph --print compact
# or: python3 -m codegrapher --print compact
```

You'll see something like:

```
# CGF/3 myapp | 24 files | 87 symbols | 120 edges (45 calls, 8 flows, 12 docs)

## architecture & practices
[architecture] ARCHITECTURE.md — System Design
  API layer -> service layer | Controllers never touch DB directly

## entrypoints
src/main.py

## execution flow
main.py::main -> server.py::start -> routes.py::handle_request

## modules
src/auth/login.py [python, 84L] (login, logout) -> models/user.py...
```

Copy that into any AI chat. Or wire it in permanently (see below).

---

## Troubleshooting: `zsh: command not found`

These are the most common setup issues on macOS with zsh.

### `pip` not found

Use the Python module form:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

### `codegraph` not found

After install, pip may put the script outside your PATH. Two options:

**Option A — use the module (no PATH change):**

```bash
python3 -m codegrapher --print compact
```

**Option B — add Python's script directory to PATH (one-time):**

```bash
# macOS (replace 3.9 with your python3 --version)
echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

On Linux, the path is usually `~/.local/bin`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### `editable mode currently requires a setuptools-based build`

Upgrade pip, then reinstall:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

---

## Integration with AI coding tools

### Cursor

Cursor supports project rules in `.cursor/rules/`. Generate and install the graph as an always-on rule:

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .codegraph
cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

Every Agent session now starts with your repo map. No manual paste needed.

Refresh after big refactors:

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .codegraph && cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

### Claude Code

Claude reads `CLAUDE.md` at the project root. Append the graph:

```bash
codegraph -f claude -o .codegraph
touch CLAUDE.md   # create if missing
cat .codegraph/CLAUDE.md.graph >> CLAUDE.md
```

Claude Code will treat the graph as persistent project context.

### OpenAI Codex / AGENTS.md

For agents that follow the AGENTS.md convention:

```bash
codegraph -f codex -o .codegraph
touch AGENTS.md   # create if missing
cat .codegraph/AGENTS.md.graph >> AGENTS.md
```

Add a line in AGENTS.md:

```markdown
## Navigation
Always consult the Repository map (CodeGrapher) section before opening files.
```

### Any LLM (ChatGPT, Gemini, etc.)

Paste this prompt template:

```
You are working on the repository "myapp".

Below is a Code Graph (CGF/3) — a compact map of modules, exports, imports,
call flow, and architecture docs. Use it to decide which files to read.
Do not assume file contents beyond what the graph shows.

---
[paste codegraph.txt here]
---

Task: Fix the login bug when session tokens expire.
```

The model navigates first, reads second.

---

## Output formats

| Format | File | Best for |
|--------|------|----------|
| compact | `codegraph.txt` | Pasting into any AI chat |
| json | `codegraph.json` | CI, tooling, custom integrations |
| mermaid | `codegraph.mmd` | Human-readable diagrams |
| cursor | `codegraph.mdc` | Cursor rules |
| claude | `CLAUDE.md.graph` | Claude Code |
| codex | `AGENTS.md.graph` | Codex agents |

Generate only what you need:

```bash
codegraph -f compact -o .codegraph
codegraph -f json --print json
codegraph --no-docs .    # skip markdown ingestion
```

---

## Language support

| Language | Support level |
|----------|---------------|
| Python | Full (AST-based) |
| JavaScript / TypeScript | Good |
| Kotlin, Java, Swift | Good (call flow + classes) |
| Go, Rust | Good |
| C#, Ruby, PHP, C/C++ | Basic |

AICodeGrapher respects `.gitignore` and skips `node_modules`, `venv`, `build/`, and other noise automatically.

---

## Real-world workflow

Here's how I recommend using it on a team:

1. Add `ARCHITECTURE.md` — document layers, rules, and conventions.
2. Run `codegraph` in CI on every push — keep the graph fresh.
3. Wire into Cursor / Claude / Codex — one-time setup per repo.
4. Regenerate after major refactors — new modules, renamed packages, new entry points.

---

## CI example (GitHub Actions)

```yaml
- name: Generate code graph
  run: |
    pip install git+https://github.com/randhirk/AICodeGrapher.git
    codegraph -f compact -o .codegraph

- uses: actions/upload-artifact@v4
  with:
    name: codegraph
    path: .codegraph/codegraph.txt
```

---

## What it's not

Being honest about limits:

- **Static analysis only** — it won't catch runtime dependency injection, reflection, or dynamic imports perfectly.
- **Best-effort call graph** — great for navigation, not a replacement for a full profiler.
- **Markdown ingestion is summarized** — it compresses docs for tokens, not a full doc dump.

Think of it as a GPS for your codebase, not a satellite image of every street.

---

## Open source — contribute

AICodeGrapher is MIT licensed and lives at:

**https://github.com/randhirk/AICodeGrapher**

Contributions welcome:

- Improve Kotlin / Swift / Java parsers
- Add new output formats
- Fix false positives in call-graph extraction
- Write examples and docs

Read [CONTRIBUTING.md](https://github.com/randhirk/AICodeGrapher/blob/main/CONTRIBUTING.md) and open a PR.

---

## The bottom line

AI coding tools don't need your entire repository in context.

They need a map.

AICodeGrapher builds that map — structure, flow, architecture, and best practices — in a format Cursor, Claude, Codex, and any LLM can use in seconds.

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher
python3 -m pip install --upgrade pip
python3 -m pip install -e .
codegraph .
```

Give your AI a map. Save your tokens. Ship faster.
