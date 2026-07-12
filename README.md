# AI-Benchmark

Production-grade LLM benchmarking for AI engineering tasks.

## Features

- Plugin-based benchmark engine with provider, benchmark, evaluator, reporter, and strategy plugins.
- Built-in providers: Ollama, NVIDIA, OpenRouter, Hugging Face, Gemini.
- Built-in benchmarks: latency, coding.
- Built-in reporters: JSON, CSV, Markdown.
- Dynamic prompt loading from YAML (`prompts/*.yaml`).
- Configuration via `configs/providers.yaml` and `configs/benchmark.yaml`.
- Environment-based API key resolution with `python-dotenv`.

## Architecture

Config → Engine → Providers → Benchmarks → Reporters

- `aibenchmark/app/config.py` — loads and validates configuration.
- `aibenchmark/app/engine.py` — core pipeline: provider init, prompt loading, execution, scoring, report generation.
- `aibenchmark/interfaces/` — abstract base classes for providers, benchmarks, reporters, evaluators, strategies.
- `aibenchmark/plugins/` — built-in provider, benchmark, and reporter implementations.
- `aibenchmark/cli.py` — Click-based CLI entrypoint.

## Requirements

- Python 3.13+
- Dependencies: httpx, pydantic, pyyaml, rich, click, jinja2, tenacity, python-dotenv

## Installation

```bash
git clone https://github.com/AI-with-Dipesh/AI-Benchmark.git
cd AI-Benchmark
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configuration

Copy `.env.example` to `.env` and set provider API keys:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
OLLAMA_API_KEY=
OPENROUTER_API_KEY=
NVIDIA_API_KEY=
HF_API_KEY=
GEMINI_API_KEY=
```

`configs/providers.yaml` defines provider endpoints, API key environment variables, and defaults.

`configs/benchmark.yaml` defines score weights and prompt mappings.

## Usage

```bash
benchmark --help
benchmark run --help
```

Run the configured default provider and model:

```bash
benchmark run main
```

Run a specific provider and model:

```bash
benchmark run ollama -m llama3.2
```

Run selected benchmarks and write reports:

```bash
benchmark run main --benchmark latency --benchmark coding -o reports
```

List models for a provider:

```bash
benchmark provider list ollama
```

## Example Benchmark

```bash
benchmark run main --benchmark latency --out reports
```

This writes:

- `reports/results.json`
- `reports/results.csv`
- `reports/results.md`

## Example Reports

`results.json`
```json
[
  {
    "model": "llama3.2",
    "provider": "ollama",
    "overall": 0.98,
    "details": { "latency_ms": 120.0, "normalized": 0.976 }
  }
]
```

`results.csv`
```csv
model,provider,overall
llama3.2,ollama,0.98
```

`results.md`
```markdown
# Benchmark Results

| Model | Provider | Overall |
|-------|----------|---------|
| llama3.2 | ollama | 0.98 |
```

## Project Structure

```
AI-Benchmark/
  aibenchmark/
    app/
      config.py
      engine.py
      logging.py
      models.py
      plugin/
        manager.py
        registry.py
      prompts.py
    cli.py
    interfaces/
      benchmark.py
      evaluator.py
      provider.py
      reporter.py
      strategy.py
    plugins/
      benchmarks/
        coding.py
        latency.py
      providers/
        huggingface.py
        nvidia.py
        ollama.py
        openrouter.py
      reporters/
        generator.py
    tests/
  configs/
    benchmark.yaml
    providers.yaml
  prompts/
    coding.yaml
    latency.yaml
    reasoning.yaml
  pyproject.toml
  .env.example
```

## Roadmap

- Sprint 1: core pipeline, providers, benchmarks, reporters, CLI.
- Sprint 2: timeout/retry policies, prompt versioning, additional benchmarks, terminal dashboard.

## License

MIT
