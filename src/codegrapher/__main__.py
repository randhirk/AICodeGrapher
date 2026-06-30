"""Allow `python3 -m codegrapher` when the `codegraph` script is not on PATH."""

from codegrapher.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
