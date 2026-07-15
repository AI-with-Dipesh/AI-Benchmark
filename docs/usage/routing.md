# Routing Guide

Sprint 7 adds history-aware model selection, context-window safety checks, and configurable fallback ordering to the routing subsystem introduced in Sprint 6.

## Model Selection

`benchmark select <category>` runs `ModelSelector` for a single benchmark category.

Strategies:
- `cost_aware`: cheapest qualified model first
- `capability_first`: highest capability match first
- `health_first`: lowest failure rate / latency first
- `round_robin`: deterministic hash-based rotation

Selection inputs:
- `ProviderCapabilities`: capability flags, context window, max output tokens
- `ProviderHealth`: failure rate, latency, availability
- `AppConfig`: cost lookup, strategy preference
- SQLite run history: recent normalized scores, success proxy, cost by provider/model

Tie-break contract:
- `cost_aware`: `(estimated_cost, -capability_score, -history_score, provider, model)`
- `capability_first`: `(-capability_score, estimated_cost, -history_score, provider, model)`
- `health_first`: `(failure_rate, average_latency_ms, estimated_cost, -history_score, provider, model)`
- `round_robin`: hash, then provider/model lex order

History ranking formula:
```text
history_score = success_rate * 0.5 + normalized_score * 0.3 + cost_efficiency * 0.2
```

Empty history is treated as neutral; all candidates receive equivalent score.

## Context-Window Safety

Before selection finalizes, `ModelSelector` estimates prompt tokens using a word-count heuristic. If a provider exposes `ProviderCapabilities.context_window`, the selector excludes providers whose estimated prompt+completion tokens exceed the window.

- No new runtime dependency is introduced.
- Providers without a declared context window are treated as unbounded.
- Max output tokens are estimated from `ProviderCapabilities.max_output_tokens` or `prompt_tokens // 2`.

## Fallback Policy

`ExecutionPolicy` owns fallback topology. The engine executes fallback attempts according to `routing.fallback.strategy`:

- `provider_first`: alternate providers first, then alternate models within each provider
- `model_first`: try alternate models on primary provider first, then alternate providers
- `hybrid`: interleave provider alternation and model alternation

Circuit breaker respects `routing.circuit_breaker` thresholds and cooldown windows. Retry semantics remain unchanged and engine-owned.

## Configuration

```yaml
routing:
  strategy: cost_aware
  cost_ceiling: 0.0
  fallback_enabled: false
  fallback_chain:
    - "ollama"
  circuit_breaker:
    enabled: true
    failure_rate_threshold: 0.5
    cooldown_seconds: 300
  parallel:
    enabled: false
    max_workers: 4
  preference:
    prefer_free: false
    min_capability_score: 0.7
  fallback:
    strategy: provider_first
```

## CLI

```bash
benchmark route [benchmark]
benchmark select <benchmark> [--provider PROVIDER] [--model MODEL]
benchmark fallback <provider> [model]
benchmark optimize [-b benchmark...] [--provider provider]
benchmark parallel -p <provider> [-b benchmark...]
benchmark config generate-litellm
```

## Determinism

All routing decisions are deterministic for identical inputs. History queries use bounded reads from SQLite with explicit limits. No random choices are made.
