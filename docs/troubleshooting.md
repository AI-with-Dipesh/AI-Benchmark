# Troubleshooting

This document covers common issues and their solutions when running AI-Benchmark.

## `benchmark: command not found`

The `benchmark` CLI entry point is not on your PATH.

**Fix:** Ensure your virtual environment is activated before running the command:

```bash
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows
```

If you installed with `pip install -e .` outside a virtual environment, you may need to restart your shell.

## Provider API key missing

```
benchmark run ollama -m llama3
# Missing API key for provider 'ollama'. Set OLLAMA_API_KEY.
```

**Fix:** Create a `.env` file from `.env.example` and fill in the required keys. Or export the environment variable directly:

```bash
export OLLAMA_API_KEY="your-key-here"
```

## `ModuleNotFoundError: No module named 'aibenchmark'`

**Fix:** Install the package in the active environment:

```bash
pip install -e .
```

## Outdated prompt files

If benchmark prompts change, update any cached prompt versions or re-run with fresh config.

**Fix:** Regenerate prompt cache or re-run without cached artifacts.

## Tests fail on Python != 3.13

The project targets Python 3.13 as the official baseline.

**Fix:** Use `pyenv` or your system package manager to install Python 3.13:

```bash
pyenv install 3.13
pyenv local 3.13
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Windows: `Permission denied` on `bootstrap.sh`

The bootstrap script is intended for bash-compatible shells (Git Bash, WSL).

**Fix:** Use `scripts/bootstrap.bat` on Windows CMD / PowerShell, or run inside WSL.

## Provider `Connection refused` or `502 Bad Gateway`

The provider service may not be running or reachable.

**Fix:** Start the local provider server (e.g., Ollama) and verify connectivity:

```bash
ollama serve
```

## Firewall / proxy blocking outbound requests

Configure `HTTPS_PROXY` / `HTTP_PROXY` environment variables for your network.

**Fix:**

```bash
export HTTPS_PROXY="http://proxy:port"
export HTTP_PROXY="http://proxy:port"
```

## Getting help

Open an issue at the project repository with:
- AI-Benchmark version (`benchmark --version` or check `pyproject.toml`)
- Python version (`python --version`)
- Full error traceback
