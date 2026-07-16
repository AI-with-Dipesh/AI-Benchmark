# Installation

This guide covers installing AI-Benchmark for end-users and setting up a developer environment for contributors.

## Prerequisites

- Python 3.13 or later
- pip or a compatible package manager
- Git

## User Installation

Install from PyPI (once published) or from source:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install aibenchmark
```

Verify installation:

```bash
benchmark --help
```

## Developer Installation

Clone the repository and install in editable mode with development dependencies:

```bash
git clone https://github.com/your-org/AI-Benchmark.git
cd AI-Benchmark
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the test suite:

```bash
pytest aibenchmark/tests/ -q
```

## Optional Extras

Install all optional tooling (security scanning, docs generation):

```bash
pip install -e ".[all]"
```

## Bootstrap Scripts

- Linux / macOS: `scripts/bootstrap.sh`
- Windows: `scripts/bootstrap.bat`

## Environment Variables

Copy `.env.example` to `.env` and fill in the API keys for the providers you plan to use:

```bash
cp .env.example .env
```

## Building Packages

```bash
# Build wheel and source distribution
python -m pip install --upgrade build
python -m build

# Install the local wheel
pip install dist/aibenchmark-1.2.0-py3-none-any.whl
```
