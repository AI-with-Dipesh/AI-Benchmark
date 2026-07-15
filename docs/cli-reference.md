# CLI Reference

Complete reference for the `benchmark` command-line interface.

## Global Options

```
benchmark --help   Show this message and exit.
```

## Command Groups

### `benchmark run`

Run selected benchmarks for a model.

```bash
benchmark run <provider_name> -m <model> [-b <benchmark>...] [-o <out_dir>]
```

- `<provider_name>` — Configured provider name, or `main` for configured defaults.
- `--model / -m` — Model name (required unless using `main`).
- `--benchmark / -b` — Repeatable. Benchmark category to run. Defaults to all.
- `--out / -o` — Report output directory. Default: `history`.

---

### `benchmark providers`

List all registered providers.

```bash
benchmark providers
```

---

### `benchmark provider`

Provider subcommands:

```bash
benchmark provider list <provider_name>
benchmark provider info <provider_name>
benchmark provider health [--provider <name>]
benchmark provider compare [<provider_names>...]
benchmark provider validate [<provider_name>]
benchmark provider certify [<provider_name>]
benchmark provider capabilities [<provider_name>]
benchmark provider validate-compat
```

---

### `benchmark models`

List models for a provider.

```bash
benchmark models [<provider_name>]
```

---

### `benchmark capabilities`

Show provider capabilities.

```bash
benchmark capabilities [<provider_name>]
```

---

### `benchmark auth`

Validate authentication credentials.

```bash
benchmark auth [<provider_name>]
```

---

### `benchmark discover`

Discover and list all plugins.

```bash
benchmark discover
```

---

### `benchmark plugin`

Plugin management commands.

```bash
benchmark plugin validate           Validate all plugin metadata and compatibility
benchmark plugin list               List plugins by category
```

---

### `benchmark leaderboard generate`

Generate leaderboard report from persisted run history.

```bash
benchmark leaderboard generate --runs 1 --out history
```

---

### `benchmark recommend`

Recommend best model per category based on history.

```bash
benchmark recommend --runs 1 --out history
```

---

### `benchmark team`

Build an AI engineering team from latest history.

```bash
benchmark team --runs 1 --out history
```

---

### `benchmark compare`

Compare latest run against an earlier run.

```bash
benchmark compare --against 2 --out history
```

---

### `benchmark trends`

Show trends across the latest N runs.

```bash
benchmark trends --runs 5 --out history
```

---

### `benchmark explain`

Print human-readable recommendation explanations.

```bash
benchmark explain --runs 1
```

---

### `benchmark validate`

Validate benchmark results and scoring integrity.

```bash
benchmark validate --out history
```

---

### `benchmark calibrate`

Run benchmark calibration and generate report.

```bash
benchmark calibrate --out history
```

---

### `benchmark stats`

Generate statistical summary for latest runs.

```bash
benchmark stats --runs 1 --out history
```

---

### `benchmark reliability`

Generate reliability metrics report.

```bash
benchmark reliability --runs 1 --out history
```

---

### `benchmark reproduce`

Print reproducibility metadata for latest run.

```bash
benchmark reproduce --out history
```

---

### `benchmark cost`

Generate cost estimation report.

```bash
benchmark cost --out history
```

---

### `benchmark tokens`

Generate token usage report.

```bash
benchmark tokens --out history
```

---

### `benchmark governance`

Generate governance/recommendation explainability report.

```bash
benchmark governance --out history
```

---

### `benchmark route [benchmark]`

Show routing plan for a benchmark without executing.

```bash
benchmark route [benchmark_name]
```

---

### `benchmark select <benchmark>`

Automatic model selection for category.

```bash
benchmark select <benchmark> [--provider <name>] [--model <name>]
```

---

### `benchmark fallback <provider> [model]`

Test fallback chain for provider/model.

```bash
benchmark fallback <provider_name> [model]
```

---

### `benchmark optimize`

Cost-optimized benchmark execution preview.

```bash
benchmark optimize [-b <benchmark>...] [--provider <name>]
```

---

### `benchmark parallel`

Multi-provider parallel execution.

```bash
benchmark parallel -p <provider> [-b <benchmark>...]
```

---

### `benchmark config generate-litellm`

Generate LiteLLM configuration.

```bash
benchmark config generate-litellm -o configs/litellm.yaml
```
