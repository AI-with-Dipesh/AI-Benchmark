# AI-Benchmark

Production-grade LLM benchmarking for AI engineering tasks.

## Features

- Plugin-based benchmark engine with provider, benchmark, evaluator, reporter plugins.
- Built-in providers: Ollama, NVIDIA, OpenRouter, Hugging Face.
- Built-in benchmarks:
  - General Intelligence
  - Coding
  - Debugging
  - Code Review
  - Research
  - Reasoning
  - JSON
  - Instruction Following
  - Latency
- Objective evaluation engine with normalization and weighted scoring.
- Configurable weights per benchmark category via `configs/benchmark.yaml`.
- Reports in JSON, CSV, and Markdown with category scores, evaluation summaries, recommendations, and trade-offs.
- Prompt versioning via YAML prompt files under `prompts/`.
- Extensible via `pyproject.toml` entry points.
- SQLite history with persistence across runs.
- Sprint 3 Analytics:
  - Historical leaderboards.
  - Model recommendations with confidence labels and trade-offs.
  - Trend analysis across runs.
  - AI Engineering Team assembly recommendations.
  - Run comparison reports.
- CLI:
  - `benchmark run main` executes all configured benchmarks.
  - `benchmark leaderboard generate` builds historical leaderboards.
  - `benchmark recommend` recommends best model per category.
  - `benchmark team` assembles an AI engineering team from history.
  - `benchmark compare` compares latest run against a previous run.
  - `benchmark trends` shows trend analysis across runs.
  - `benchmark explain` prints human-readable recommendation explanations.

## Architecture

```
aibenchmark/
  app/
    engine.py        - BenchEngine: provider init, prompt loading, benchmark orchestration
    config.py        - AppConfig: providers, weights, defaults
    models.py        - Dataclasses: BenchmarkResult, Score, ProviderType, BenchmarkName
    prompts.py       - PromptLoader: YAML prompt discovery + metadata
    analytics.py     - Analytics engine: leaderboard, trends, recommendations, team builder
    history.py       - SQLite persistence: init_db, save_run, load_latest, load_run
    logging.py       - Logging setup
    evaluation/
      __init__.py    - Evaluator implementations per category
    plugin/
      registry.py    - Decorator registration
      manager.py     - PluginManager: discovery, registration, lookup
  plugins/
    benchmarks/      - Benchmark plugins (one category per module)
    providers/       - Provider plugins
    reporters/       - JSON, Markdown, CSV reporters
      analytics.py   - Sprint 3 analytics reporters: recommendations, team, trends, compare
    evaluators/      - Optional external evaluator plugins
    strategies/      - Optional execution strategies
  cli.py             - Click CLI: run, provider, leaderboard, recommend, team, compare, trends, explain
  tests/             - pytest suite
  prompts/           - YAML prompt files per benchmark
  configs/           - benchmark.yaml, providers.yaml
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Requirements

- Python 3.13+
- Dependencies: httpx, pydantic, pyyaml, rich, click, jinja2, tenacity, python-dotenv
- Dev: pytest, mypy, ruff, pytest-cov

## Usage

Configure environment variables from `.env.example`:

```bash
cp .env.example .env
# fill provider API keys, e.g. OLLAMA_API_KEY, NVIDIA_API_KEY
```

Run all benchmarks for the configured default provider and model:

```bash
benchmark run main
```

Run specific benchmarks:

```bash
benchmark run ollama -m llama3 --benchmark coding --benchmark reasoning
```

### Analytics Commands

```bash
# Show leaderboard from latest run
benchmark leaderboard generate --runs 1 --out history

# Recommend best model per category
benchmark recommend --runs 1 --out history

# Assemble AI engineering team
benchmark team --runs 1 --out history

# Compare latest run against an earlier run
benchmark compare --against 2 --out history

# Show trends across latest N runs
benchmark trends --runs 5 --out history

# Explain recommendations
benchmark explain --runs 1
```

## CLI Commands

- `benchmark run <provider> -m <model> [-b <benchmark>...]` Run selected or all benchmarks.
- `benchmark run main` Run all benchmarks from `configs/benchmark.yaml` defaults.
- `benchmark provider list <provider_name>` List available models.
- `benchmark leaderboard generate` Generate leaderboard report from persisted history.
- `benchmark recommend` Recommend best model per category based on history.
- `benchmark team` Build an AI engineering team from latest history.
- `benchmark compare` Compare latest run against N-th latest run.
- `benchmark trends` Show trends across the latest N runs.
- `benchmark explain` Print human-readable recommendation explanation to stdout.

## Configuration

`configs/benchmark.yaml`

- `weights:` category weights for final score computation.
- `default_prompts:` prompt file mapping.

`configs/providers.yaml`

- Provider-specific settings: name, api_key, api_key_env, base_url, models, default.

## Example Benchmark Output

```json
[
  {
    "model": "llama3",
    "provider": "ollama",
    "overall": 0.82,
    "scores": [
      {
        "benchmark": "coding",
        "raw": 0.9,
        "normalized": 0.9,
        "weight": 25,
        "weighted": 22.5
      }
    ],
    "metadata": {
      "timestamp": "2026-07-12T00:00:00+00:00",
      "status": "success"
    },
    "details": {}
  }
]
```

## Reports

- JSON: raw machine-readable results.
- CSV: category breakdown.
- Markdown: human-readable summary.
- Leaderboard.md: historical top models.
- recommendations.md: per-category recommendations with confidence and trade-offs.
- team.md: AI engineering team assembly with roles.
- trends.md: trend analysis across runs.
- compare.md: run-to-run comparison.

## Project Structure

```
.
├── aibenchmark/
│   ├── app/
│   │   ├── engine.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   ├── analytics.py
│   │   ├── history.py
│   │   ├── logging.py
│   │   ├── evaluation/
│   │   │   └── __init__.py
│   │   └── plugin/
│   │       ├── registry.py
│   │       └── manager.py
│   ├── plugins/
│   │   ├── benchmarks/
│   │   │   ├── __init__.py
│   │   │   ├── code_review.py
│   │   │   ├── coding.py
│   │   │   ├── debugging.py
│   │   │   ├── general.py
│   │   │   ├── instruction.py
│   │   │   ├── json.py
│   │   │   ├── latency.py
│   │   │   ├── reasoning.py
│   │   │   └── research.py
│   │   ├── providers/
│   │   │   ├── huggingface.py
│   │   │   ├── nvidia.py
│   │   │   ├── ollama.py
│   │   │   └── openrouter.py
│   │   ├── reporters/
│   │   │   ├── analytics.py
│   │   │   ├── generator.py
│   │   │   └── ...
│   │   ├── evaluators/
│   │   └── strategies/
│   ├── cli.py
│   └── tests/
│       ├── test_analytics.py
│       ├── test_benchmarks.py
│       ├── test_config.py
│       ├── test_coverage_boost.py
│       ├── test_evaluators.py
│       ├── test_integration.py
│       ├── test_model_differentiation.py
│       ├── test_plugins.py
│       ├── test_prompts.py
│       ├── test_providers.py
│       ├── test_reports.py
│       └── test_scoring.py
├── configs/
│   ├── benchmark.yaml
│   └── providers.yaml
├── .env.example
├── prompts/
│   ├── code_review.yaml
│   ├── coding.yaml
│   ├── debugging.yaml
│   ├── general.yaml
│   ├── instruction.yaml
│   ├── json.yaml
│   ├── latency.yaml
│   ├── reasoning.yaml
│   └── research.yaml
├── docs/
│   ├── sprint-1.md
│   └── sprints/
│       ├── sprint-2.md
│       └── sprint-3.md
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## Roadmap

- Sprint 1: Core engine + latency benchmark
- Sprint 2: Multi-category benchmarks + evaluation engine + weighted scoring + rich reports
- Sprint 3: History, trend analysis, leaderboard, recommendations, confidence engine, AI engineering team builder
- Sprint 4: Dashboard, async execution, scheduling, LiteLLM automation

## Version

Current version: `0.3.0`

## Sprint History

- **Sprint 1**: Core plugin engine, latency benchmark, basic reporters.
- **Sprint 2**: Multi-category benchmarks, objective evaluation, weighted scoring, prompt versioning, CSV/Markdown/JSON reports.
- **Sprint 3**: SQLite history, analytics engine, trend analysis, historical leaderboards, model recommendations with confidence, AI engineering team assembly, run comparison.

## License

MIT

## Contributing

PRs welcome. Run `pytest` and ensure coverage remains >=90% before submitting.
