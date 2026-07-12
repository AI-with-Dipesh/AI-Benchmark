# AI-Benchmark

Production-grade LLM benchmarking for AI engineering tasks.

## Features

Sprint 2: Multi-category evaluation engine with automatic scoring and reporting.

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
- Evaluation engine with objective scoring and normalization.
- Configurable weights per benchmark category.
- Reports in JSON, CSV, and Markdown with category scores, weighted scores, and evaluation summaries.
- Prompt versioning via YAML prompt files.
- Extensible via `pyproject.toml` entry points.
- CLI: `benchmark run main` executes all configured benchmarks automatically.

## Architecture

```
aibenchmark/
  app/
    engine.py        - BenchEngine: provider init, prompt loading, benchmark orchestration
    config.py        - AppConfig: providers, weights, defaults
    prompts.py       - PromptLoader: YAML prompt discovery + metadata
    evaluation/      - Reusable evaluators per category
    plugin/
      registry.py    - Decorator registration
      manager.py     - PluginManager: discovery, registration, lookup
  plugins/
    benchmarks/      - Benchmark plugins (one category per module)
    providers/       - Provider plugins
    reporters/       - JSON, Markdown, CSV reporters
    evaluators/      - Optional external evaluator plugins
    strategies/      - Optional execution strategies
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
- Dev: pytest, mypy, ruff

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

## CLI Commands

- `benchmark run <provider> -m <model>` Run selected or all benchmarks.
- `benchmark run main` Run all benchmarks from `configs/benchmark.yaml` defaults.

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
    "evaluation": "...",
    "recommendations": ["..."],
    "metadata": {},
    "details": {}
  }
]
```

## Project Structure

```
.
├── aibenchmark/
│   ├── app/
│   │   ├── engine.py
│   │   ├── config.py
│   │   ├── models.py
│   │   ├── prompts.py
│   │   ├── logging.py
│   │   ├── evaluation/
│   │   └── plugin/
│   ├── plugins/
│   │   ├── benchmarks/
│   │   ├── providers/
│   │   ├── reporters/
│   │   ├── evaluators/
│   │   └── strategies/
│   ├── cli.py
│   └── tests/
├── configs/
│   ├── benchmark.yaml
│   └── providers.yaml
├── .env.example
├── prompts/
│   ├── coding.yaml
│   ├── debugging.yaml
│   ├── general.yaml
│   ├── json.yaml
│   ├── instruction.yaml
│   ├── latency.yaml
│   ├── reasoning.yaml
│   ├── research.yaml
│   └── code_review.yaml
├── docs/
│   ├── sprint-1.md
│   └── sprints/
│       └── sprint-2.md
├── pyproject.toml
├── README.md
├── LICENSE
└── CHANGELOG.md
```

## Roadmap

- Sprint 1: Core engine + latency benchmark
- Sprint 2: Multi-category benchmarks + evaluation engine + weighted scoring + rich reports
- Sprint 3: History, trend analysis, leaderboard
- Sprint 4: Dashboard, async execution, scheduling, LiteLLM automation

## License

MIT

## Contributing

PRs welcome. Run `pytest` and `ruff`/`mypy` before submitting.
