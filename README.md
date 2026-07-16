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
- Sprint 4 Validation & Reliability:
  - Benchmark validation and auto-validation.
  - Calibration engine with discriminative power and bias detection.
  - Reliability metrics: success/failure/timeout/retry rates, P95/P99 latency.
  - Token accounting and cost estimation.
  - Retry/timeout policies.
  - Reproducibility metadata on every result.
- Sprint 5 Universal Provider Platform:
  - Universal Provider Interface (22-method contract).
  - Dynamic provider plugin system with load/unload/enable/disable/priority/aliases.
  - Provider Registry with automatic discovery and capability detection.
  - Health monitoring with rolling-window latency and failure tracking.
  - Authentication layer supporting env vars, .env, and config files.
  - Rate limit detection with retry recommendations.
  - Cross-provider benchmarking and deterministic ranking.
  - Provider certification (platinum/gold/silver/bronze).
  - Provider comparison reports (capabilities, latency, reliability, cost, token efficiency).
  - CLI commands: `providers`, `provider info`, `provider health`, `provider compare`, `models`, `capabilities`, `auth`, `discover`, `provider validate`, `provider certify`.
- Sprint 6: Intelligent Routing & Automatic Model Selection
  - Strategy plugin framework operational via `PluginCategory.STRATEGY`.
  - Automatic model selection strategies: `cost_aware`, `capability_first`, `health_first`, `round_robin`.
  - LiteLLM-style routing configuration generation.
  - Fallback execution policy with circuit breaker.
  - Optional multi-provider parallel execution with deterministic ordering.
  - New reporters: `routing`, `optimization`, `litellm_config`.
  - New CLI commands: `route`, `select`, `fallback`, `optimize`, `parallel`, `config generate-litellm`.
  - Thread-safe `HealthTracker` and `HistoryWriter` for parallel execution safety.
  - CI workflow with test, lint, and type-check.
- Sprint 7: History-Driven Selection, Context-Window Safety, Model Alternation, Release Automation
  - History-aware model ranking using SQLite run history.
  - Context-window feasibility checks before execution.
  - Configurable fallback ordering: `provider_first`, `model_first`, `hybrid`.
  - Model alternation under fallback policy.
  - Release automation workflow with draft release generation.
  - Deterministic routing tie-break contract.
- CLI:
  - `benchmark run main` executes all configured benchmarks.
  - `benchmark leaderboard generate` builds historical leaderboards.
  - `benchmark recommend` recommends best model per category.
  - `benchmark team` assembles an AI engineering team from history.
  - `benchmark compare` compares latest run against a previous run.
  - `benchmark trends` shows trend analysis across runs.
  - `benchmark explain` prints human-readable recommendation explanations.
  - `benchmark providers` lists all registered providers.
  - `benchmark provider health` shows provider health status.
  - `benchmark provider compare` compares providers and shows ranking.

## Architecture

```
aibenchmark/
  app/
    analytics.py             - Analytics: leaderboard, trends, recommendations, team
    auto_validation.py       - Automatic benchmark quality guards
    calibration.py           - Benchmark weight/category calibration
    config.py                - Providers, weights, retry, timeout, cost config
    engine.py                - BenchEngine: provider init, prompt loading, retries, metadata
    history.py               - SQLite persistence: init_db, save_run, load_latest
    logging.py               - Logging setup
    models.py                - Dataclasses + validation/calibration/reliability models
    prompts.py               - PromptLoader: YAML prompt discovery + metadata
    recommendation_validation.py - Recommendation stability/confidence checks
    reliability.py           - Reliability aggregation + latency percentiles
    statistics.py           - Descriptive stats, confidence intervals, drift
    token_accounting.py     - Token usage + cost estimation
    validation.py           - Structural result and metadata validation
    evaluation/
      __init__.py           - Evaluator implementations per category
    plugin/
      registry.py           - Decorator registration
      manager.py            - PluginManager: discovery, registration, lookup, unload, priority
    provider_registry.py     - ProviderRegistry: discovery, health, capabilities, metadata, validation
    provider_health.py       - Health monitoring: rolling-window metrics, status classification
    provider_capabilities.py - Capability detection: 13 flags per provider
    auth.py                  - Authentication layer: env, .env, config, credential validation
    rate_limits.py           - Rate limit detection: 429, quota, maintenance, burst limits
    certification.py         - Provider certification: platinum/gold/silver/bronze classification
    cross_provider.py        - Cross-provider benchmarking and deterministic ranking
    execution_policy.py      - Sprint 6 fallback/circuit-breaker policy
    model_selector.py        - Sprint 6 automatic model selection
    parallel_executor.py     - Sprint 6 parallel execution coordinator
  plugins/
    benchmarks/             - Benchmark plugins (one category per module)
    providers/              - Provider plugins
    reporters/              - JSON, Markdown, CSV + Sprint 4/5 reporters
      analytics.py          - Sprint 3 analytics reporters
      generator.py          - JSON/Markdown/CSV report generation
      sprint4.py            - Validation, calibration, reliability, stats, cost, metadata
      provider_comparison.py - Sprint 5 provider comparison reports
      provider_health.py     - Sprint 5 provider health reports
      capabilities.py        - Sprint 5 capability reports
    evaluators/             - Optional external evaluator plugins
  cli.py                     - Click CLI: run, recommend, team, explain, validate, calibrate, providers, health, compare, models, capabilities, auth, discover, certify
  tests/                     - pytest suite
  prompts/                   - YAML prompt files per benchmark
  configs/                   - benchmark.yaml, providers.yaml
```

## Installation

See [docs/installation.md](docs/installation.md) for the full installation guide, including developer bootstrap and optional extras.

Quick start:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Requirements

- Python 3.13 is the currently tested and officially supported baseline.
- Dependencies: httpx, pydantic, pyyaml, click, python-dotenv
- Dev: pytest, mypy, ruff, pytest-cov, sphinx

## Quick Start

See [docs/quickstart.md](docs/quickstart.md) for a step-by-step walkthrough.

```bash
benchmark run main
benchmark discover
```

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md).

## Plugin SDK

See [docs/plugins/sdk.md](docs/plugins/sdk.md) and [docs/plugins/compatibility.md](docs/plugins/compatibility.md).

## Reports

`configs/benchmark.yaml`

- `weights:` category weights for final score computation.
- `default_prompts:` prompt file mapping.
- `run_defaults:` temperature, top_p, seed, iterations, confidence thresholds.
- `retry:` retry count, backoff factor, retryable error classes.
- `timeouts:` request/benchmark/category/connect timeouts.
- `cost:` per-provider/model token pricing.
- `prompt_versions:` version string per benchmark category.
- `benchmark_version:` overall benchmark suite version.
- `routing:` strategy, cost ceiling, fallback controls, circuit breaker, parallel execution, selection preferences.
  - `fallback.strategy:` fallback ordering: `provider_first`, `model_first`, `hybrid`. Defaults to `provider_first`.
- `routing.fallback_chain:` ordered providers to attempt after primary provider failure.

`configs/providers.yaml`

- Provider-specific settings: name, api_key, api_key_env, base_url, models, default.

### Routing

Use `benchmark route` to preview routing plans without executing:

```bash
benchmark route coding
benchmark select coding --provider ollama
benchmark fallback ollama --model llama3
```

History-driven selection uses SQLite run history to rank candidates. Context-window safety checks skip providers whose context limits cannot accommodate the estimated prompt. Fallback ordering is configurable via `routing.fallback.strategy`.

### Release Automation

The repository includes `.github/workflows/release.yml` for draft release generation.

- Trigger: manual `workflow_dispatch` with tag input.
- Behavior: runs tests, generates artifact bundle, creates draft release.
- Limitation: does not auto-publish; manager approval required.

## Example Benchmark Output

```json
[
  {
    "benchmark": "llama3",
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
- leaderboard: historical top models.
- recommendations: per-category recommendations with confidence and trade-offs.
- team: AI engineering team assembly with roles.
- trends: trend analysis across runs.
- compare: run-to-run comparison.
- validation: structural and automatic quality guardrails.
- calibration: category bias, inflation, discriminative power, instability.
- reliability: success/failure/timeout/retry, latency percentiles, availability.
- statistics: mean, median, std, confidence intervals, drift, outliers.
- tokens: prompt/completion/total tokens, tokens/sec, breakdown by model.
- cost: total cost, by provider, by model.
- metadata: reproducibility metadata table.
- governance: recommendation explainability with alternatives and confidence derivation.
- provider_comparison: cross-provider rankings, capability matrix, cost, token efficiency.
- provider_health: per-provider health status and metrics.
- capabilities: provider capability flags and detection method.

## Project Structure

```
.
├── aibenchmark/
│   ├── app/
│   │   ├── analytics.py             - Sprint 3 analytics: leaderboard, trends, recommendations, team
│   │   ├── auto_validation.py       - Automatic benchmark quality guards
│   │   ├── calibration.py           - Benchmark weight/category calibration
│   │   ├── config.py                - Providers, weights, retry, timeout, cost config
│   │   ├── engine.py                - BenchEngine: provider init, prompt loading, retries, metadata
│   │   ├── history.py               - SQLite persistence: init_db, save_run, load_latest
│   │   ├── logging.py               - Logging setup
│   │   ├── models.py                - Dataclasses + validation/calibration/reliability models
│   │   ├── plugin/
│   │   │   ├── registry.py          - Decorator registration
│   │   │   └── manager.py           - PluginManager: discovery, registration, lookup, unload, priority
│   │   ├── prompts.py               - PromptLoader: YAML prompt discovery + metadata
│   │   ├── provider_registry.py     - ProviderRegistry: discovery, health, capabilities, metadata, validation
│   │   ├── provider_health.py       - Health monitoring: rolling-window metrics, status classification
│   │   ├── provider_capabilities.py - Capability detection: 13 flags per provider
│   │   ├── auth.py                  - Authentication layer: env, .env, config, credential validation
│   │   ├── rate_limits.py           - Rate limit detection: 429, quota, maintenance, burst limits
│   │   ├── certification.py         - Provider certification: platinum/gold/silver/bronze classification
│   │   ├── cross_provider.py        - Cross-provider benchmarking and deterministic ranking
│   │   ├── recommendation_validation.py - Recommendation stability/confidence checks
│   │   ├── reliability.py           - Reliability aggregation + latency percentiles
│   │   ├── statistics.py            - Descriptive stats, confidence intervals, drift
│   │   ├── token_accounting.py      - Token usage + cost estimation
│   │   ├── validation.py            - Structural result and metadata validation
│   │   └── evaluation/
│   │       └── __init__.py          - Evaluator implementations per category
│   ├── plugins/
│   │   ├── benchmarks/              - Benchmark plugins (one category per module)
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
│   │   ├── providers/               - Provider plugins
│   │   │   ├── __init__.py
│   │   │   ├── huggingface.py
│   │   │   ├── nvidia.py
│   │   │   ├── ollama.py
│   │   │   └── openrouter.py
│   │   └── reporters/               - JSON, Markdown, CSV + Sprint 4/5 reporters + Sprint 6 routing/optimization/LiteLLM
│   │       ├── analytics.py         - Sprint 3 analytics reporters
│   │       ├── generator.py         - JSON/Markdown/CSV report generation
│   │       ├── sprint4.py           - Validation, calibration, reliability, stats, cost, metadata, governance
│   │       ├── provider_comparison.py - Sprint 5 provider comparison reports
│   │       ├── provider_health.py     - Sprint 5 provider health reports
│   │       └── capabilities.py        - Sprint 5 capability reports, governance
│   ├── cli.py                       - Click CLI
│   ├── interfaces/                  - Abstract interfaces (provider/benchmark/evaluator/reporter/strategy)
│   ├── plugin/                      - Plugin registry core
│   │   ├── __init__.py
│   │   ├── registry.py
│   │   └── manager.py
│   ├── execution_policy.py           - Fallback/circuit-breaker policy, fallback strategy ordering
│   ├── model_selector.py             - Automatic model selection with history ranking and context checks
│   ├── parallel_executor.py          - Parallel execution coordinator
│   ├── history.py                    - SQLite persistence: init_db, save_run, load_latest, recent_category_performance
│   └── tests/                       - pytest suite
├── configs/
│   ├── benchmark.yaml
│   └── providers.yaml
├── docs/
│   ├── sprint-1.md
│   ├── sprint-4.md
│   ├── sprint-5.md
│   ├── sprint-6-plan.md
│   ├── architecture/
│   │   └── sprint-6-architecture-review.md
│   └── sprints/
│       ├── sprint-2.md
│       └── sprint-3.md
├── history/                         - Generated report outputs (gitignored)
├── prompts/                         - YAML prompt files per benchmark
├── .env.example
├── .gitignore
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
└── CHANGELOG.md
```

## Roadmap

- Sprint 1: Core engine + latency benchmark
- Sprint 2: Multi-category benchmarks + evaluation engine + weighted scoring + rich reports
- Sprint 3: History, trend analysis, leaderboard, recommendations, confidence engine, AI engineering team builder
- Sprint 4: Validation, calibration, reliability, token accounting, retry/timeout policies, metadata
- Sprint 5: Universal Provider Platform
- Sprint 6: Intelligent Routing & Automatic Model Selection
- Sprint 7: History-Driven Selection, Context-Window Safety, Model Alternation, Release Automation

## Operational Notes

### Retry semantics
`retry_count` in `configs/benchmark.yaml` specifies the **number of retries**, not total requests. The engine will make `retry_count + 1` total attempts for retryable errors (timeout, connection, rate, server_error).

### Confidence calculation
Recommendation confidence is a composite of:
- Category score (70%)
- Score gap vs second-best candidate (15%)
- Reliability score (10%)
- Historical familiarity (5%)

Values are clamped to `[0.0, 1.0]` and labelled Medium (>=0.6) or High (>=0.75).

### Cost estimation
Cost is estimated from configured token prices in `configs/benchmark.yaml` under the `cost:` section. If a provider/model has no price entry, cost falls back to `0.0`. The report reflects the configuration; it does not fabricate market prices.

## Version

Current version: `1.2.0`

## Sprint History

- **Sprint 1**: Core plugin engine, latency benchmark, basic reporters.
- **Sprint 2**: Multi-category benchmarks, objective evaluation, weighted scoring, prompt versioning, CSV/Markdown/JSON reports.
- **Sprint 3**: SQLite history, analytics engine, trend analysis, historical leaderboards, model recommendations with confidence, AI engineering team assembly, run comparison.
- **Sprint 4**: Benchmark validation, calibration, statistics, reliability metrics, token/cost accounting, retry/timeout policies, reproducibility metadata, expanded CLI and reporters.
- **Sprint 5**: Universal Provider Interface, dynamic provider plugins, provider registry, health monitoring, auth, rate limits, certification, cross-provider benchmarking, provider comparison/health/capabilities reports.
- **Sprint 6**: Intelligent routing, automatic model selection, fallback/circuit-breaker policy, parallel execution, LiteLLM config generation, routing/optimization reporters, coverage/health history.

## License

MIT

## Contributing

PRs welcome. Run `pytest` and ensure coverage remains >=90% before submitting.

See [docs/developer-guide.md](docs/developer-guide.md) for local setup, testing workflow, plugin development, and governance process.
