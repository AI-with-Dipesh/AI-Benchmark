# Quickstart

Get AI-Benchmark up and running in under 5 minutes.

## 1. Install

```bash
pip install -e .
# or with dev extras:
pip install -e ".[dev]"
```

## 2. Configure providers

Edit `configs/providers.yaml` to add your provider API keys, or set the corresponding environment variables:

```bash
cp .env.example .env
# Edit .env with your keys
```

## 3. Run your first benchmark

Use `benchmark run main` to execute all benchmarks for the configured default provider and model:

```bash
benchmark run main
```

Run a specific benchmark for a specific model:

```bash
benchmark run ollama -m llama3 --benchmark coding --benchmark reasoning
```

## 4. View reports

Reports are written to the `history/` directory by default:

```bash
benchmark explain --runs 1
```

## 5. Discover available plugins

```bash
benchmark discover
benchmark providers
```

## Next Steps

- Read the [CLI Reference](cli-reference.md) for all available commands.
- See [Troubleshooting](troubleshooting.md) for common issues.
- Read [Plugin SDK](plugins/sdk.md) to write custom plugins.
