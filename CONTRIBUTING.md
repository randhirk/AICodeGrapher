# Contributing to AICodeGrapher

Thank you for your interest in contributing! **AICodeGrapher** (package name: `codegrapher`) is open source under the [MIT License](LICENSE). Everyone is welcome to report bugs, suggest features, improve docs, and submit code.

## Ways to contribute

- **Report bugs** — [Open a bug report](https://github.com/randhirk/AICodeGrapher/issues/new?template=bug_report.md)
- **Request features** — [Open a feature request](https://github.com/randhirk/AICodeGrapher/issues/new?template=feature_request.md)
- **Improve parsers** — Better support for Kotlin, Swift, Java, JS/TS, etc.
- **Docs** — README, INTEGRATION.md, examples
- **Tests** — Especially edge cases in call-graph and markdown ingestion

## Getting started

```bash
git clone https://github.com/randhirk/AICodeGrapher.git
cd AICodeGrapher
pip install -e ".[dev]"
pytest
ruff check src tests
```

Run the CLI on this repo to verify your changes:

```bash
codegraph . --print compact
```

## Pull request process

1. **Fork** the repo and create a branch from `main`:
   ```bash
   git checkout -b feat/my-improvement
   ```
2. **Make focused changes** — one feature or fix per PR when possible.
3. **Add or update tests** in `tests/` for behavior you change.
4. **Run the test suite** — all tests must pass.
5. **Open a PR** against `main` with:
   - What changed and why
   - How you tested it
   - Any follow-ups

We review PRs as soon as we can. Be patient and responsive to feedback.

## Code guidelines

- Match existing style (see `ruff` config in `pyproject.toml`)
- Keep changes minimal and purposeful
- Prefer extending existing parsers over large new abstractions
- New language support: add a parser in `src/codegrapher/parsers/` and register it in `base.py`
- Document user-facing behavior in `README.md` when relevant

## Project structure

```
src/codegrapher/
  cli.py          # CLI entry point
  scanner.py      # File discovery
  builder.py      # Graph construction
  flow.py         # Execution-flow paths
  docs.py         # Markdown architecture ingestion
  parsers/        # Per-language parsers
  serialize.py    # Output formats (CGF v3)
tests/
```

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating, you agree to uphold a welcoming, respectful community.

## Questions?

Open a [GitHub Discussion](https://github.com/randhirk/AICodeGrapher/discussions) or an issue labeled `question`.
