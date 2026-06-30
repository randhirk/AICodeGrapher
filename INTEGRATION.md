# Integration Guide

How to wire CodeGrapher into AI coding tools so agents navigate your repo with minimal tokens.

## Prerequisites

Install once (from the [AICodeGrapher repo](https://github.com/randhirk/AICodeGrapher)):

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

Verify:

```bash
codegraph --version
# or, if codegraph is not on PATH:
python3 -m codegrapher --version
```

### `zsh: command not found` fixes

**`pip` not found** — macOS often has no `pip` shim. Use:

```bash
python3 -m pip install -e .
```

**`codegraph` not found** — pip installed the script outside your PATH. Either:

1. **Recommended:** use the module (no PATH change):

   ```bash
   python3 -m codegrapher -f cursor -o .codegraph
   python3 -m codegrapher --print compact
   ```

2. **Permanent fix:** add Python’s user `bin` to zsh (adjust `3.9` to your version):

   ```bash
   echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

   Linux:

   ```bash
   echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
   source ~/.zshrc
   ```

3. **No install:** run from a clone:

   ```bash
   cd /path/to/AICodeGrapher
   PYTHONPATH=src python3 -m codegrapher /path/to/your-app
   ```

**`editable mode currently requires a setuptools-based build`** — upgrade pip, then reinstall:

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -e .
```

---

## The idea

1. Run `codegraph` on your repo (locally or in CI).
2. Give the AI the **compact graph** instead of (or before) full file trees.
3. The agent reads only the files it actually needs.

The compact format is ~200–2000 tokens for most repos vs. tens of thousands for a full tree listing.

---

## Cursor

Cursor supports [project rules](https://docs.cursor.com/context/rules) in `.cursor/rules/`.

### Setup

From your **project root** (the repo you want Cursor to map):

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .codegraph
cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

If `codegraph` is not on PATH, prefix with `python3 -m codegrapher` (same flags).

Or write the rule directly into `.cursor/rules/` (no copy step):

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .
```

The rule has `alwaysApply: true` so every Agent chat gets the graph automatically.

### Refresh after big refactors

```bash
mkdir -p .cursor/rules
codegraph -f cursor -o .codegraph && cp .codegraph/.cursor/rules/codegraph.mdc .cursor/rules/
```

### Manual paste

```bash
codegraph --print compact | pbcopy   # macOS
```

Paste at the start of a chat: *"Here is the repo map — use it to navigate."*

---

## Claude Code

Claude Code reads `CLAUDE.md` at the project root for persistent context.

### Setup

From your project root:

```bash
codegraph -f claude -o .codegraph
touch CLAUDE.md   # create if missing
cat .codegraph/CLAUDE.md.graph >> CLAUDE.md
```

---

## OpenAI Codex / AGENTS.md

Agents that follow the AGENTS.md convention can use the same graph.

### Setup

From your project root:

```bash
codegraph -f codex -o .codegraph
touch AGENTS.md   # create if missing
cat .codegraph/AGENTS.md.graph >> AGENTS.md
```

Tell the agent in AGENTS.md:

```markdown
## Navigation
Always consult the Repository map (CodeGrapher) section before opening files.
Prefer targeted reads over broad directory listings.
```

---

## Generic / any LLM

```bash
codegraph --print compact
```

**Prompt template:**

```
You are working on the repository "{repo}".

Below is a Code Graph (CGF/1) — a compact map of modules, exports, and imports.
Use it to decide which files to read. Do not assume file contents beyond what the graph shows.

---
{paste codegraph.txt}
---

Task: {your task}
```

---

## JSON / programmatic

```bash
codegraph -f json -o .codegraph
```

Parse `codegraph.json`:

- `nodes[].id` — file path
- `nodes[].exports` — public API surface
- `edges[]` — `from` imports `to`
- `entrypoints` — start here for execution flow

---

## Token savings (rough guide)

| Repo size | Full tree listing | CodeGrapher compact |
|-----------|-------------------|---------------------|
| Small (20 files) | ~3–8K tokens | ~300–600 tokens |
| Medium (100 files) | ~15–40K tokens | ~800–2K tokens |
| Large (500+ files) | 100K+ tokens | ~2–5K tokens |

---

## Regeneration

Re-run when structure changes significantly:

```bash
# package.json script example
"scripts": {
  "codegraph": "codegraph -q"
}
```
