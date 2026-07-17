# Claude Code Routing Generator

## Overview

Automatically generate routing configurations from benchmark evidence.

Supported formats:
- Claude Code Router
- Generic YAML
- JSON
- Markdown

## Implementation

- `aibenchmark/plugins/reporters/routing.py` — routing reporter plugin
- `aibenchmark/plugins/reporters/litellm_config.py` — LiteLLM config export
- `aibenchmark/app/model_selector.py` — runtime routing strategy engine

## CLI

```bash
benchmark route <benchmark_name>
benchmark route coding
```

Generates routing plan with primary, fallback, confidence, and evidence.

## Generated Routing Plan

```yaml
default:
  model: tencent/hy3:free
  provider: openrouter
  fallback_chain:
    - provider: ollama
      model: llama3.2
```

## Configuration Strategy

Strategies available in `model_selector.py`:

- `cost_aware` — cheapest token cost above minimum score
- `capability_first` — highest capability match
- `health_first` — most available provider
- `round_robin` — distribute load

## Integration

Routing plans are consumed by:
- `BenchEngine.run_benchmark()` primary execution
- `BenchEngine._execute_fallback()` fallback chain
- `ExecutionPolicy` circuit breaker and cooldown
