# Contributing to AI-Benchmark

Thank you for your interest in improving AI-Benchmark. This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork and clone the repository.
2. Create a virtual environment: `python -m venv .venv && source .venv/bin/activate`
3. Install dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest aibenchmark/tests/ -q`
5. Run linting: `ruff check aibenchmark/`
6. Run type checking: `mypy aibenchmark/`

## Testing Requirements

- All new code must include tests.
- Coverage must remain at or above 90%.
- All existing tests must pass.

## Commit Conventions

- Use Conventional Commits: `feat(scope): description`, `fix(scope): description`, `docs(scope): description`
- Keep commits atomic and focused.
- Reference issue numbers when applicable.

## Pull Request Process

1. Update documentation for any changed behavior.
2. Ensure CI passes.
3. Request review from maintainers.

## Reporting Issues

Use the bug report or feature request templates in `.github/ISSUE_TEMPLATE/`.

Thank you for contributing.
