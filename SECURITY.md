# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a vulnerability

If you discover a security issue, please **do not** open a public GitHub issue.

Instead, report it privately to the maintainer via [GitHub Security Advisories](https://github.com/randhirk/AICodeGrapher/security/advisories/new) or by opening a minimal description issue and asking for a private channel.

We will acknowledge your report and work on a fix as quickly as possible.

## Scope

AICodeGrapher scans local filesystem paths and reads source/markdown files. It does not execute scanned code. Report issues related to:

- Path traversal or unsafe file handling
- Unexpected code execution
- Sensitive data leakage in generated graph output
