import click
from pathlib import Path
from typing import Any

from aibenchmark.app.config import ConfigError
from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.history import load_latest, save_run
from aibenchmark.app.logging import setup_logging
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory

setup_logging()


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.argument("provider_name")
@click.option("--model", "-m", required=False)
@click.option("--benchmark", "-b", multiple=True, default=None)
@click.option("--out", "-o", default="history")
def run(provider_name: str, model: str | None, benchmark: tuple[str, ...], out: str) -> None:
    """Run selected benchmarks for a model.

    provider_name may be a configured provider name or 'main', which uses
    the default provider and model from benchmark configuration.
    """
    try:
        engine = BenchEngine()
    except RuntimeError as exc:
        raise click.ClickException(str(exc))

    if provider_name == "main":
        defaults = engine.config.defaults()
        provider_name = str(defaults.get("default_provider") or "")
        model = model or str(defaults.get("default_model") or "")
        if not provider_name or not model:
            raise click.ClickException(
                "Config missing 'defaults.default_provider' or 'defaults.default_model'."
            )

    if not model:
        raise click.UsageError("Missing --model. Use 'benchmark run main' for configured defaults, or pass -m <model>.")

    if not benchmark:
        benchmark = tuple(engine.list_benchmarks())

    available = engine.list_benchmarks()
    results = []
    messages = [{"role": "user", "content": "Say hello"}]
    for name in benchmark:
        if name not in available:
            click.echo(f"{name}: SKIP (not available)")
            continue
        try:
            r = engine.run_benchmark(provider_name, model, BenchmarkName(name), messages)
            status = r.metadata.get("status", "success")
            click.echo(f"{name}: {r.overall:.2f} [{status}]")
            results.append(r)
        except Exception as exc:
            click.echo(f"{name}: ERROR {exc}")
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results, out_path)
    try:
        save_run(results, details={"source": "cli", "run_type": "main"})
    except Exception as exc:  # pragma: no cover - persistence secondary
        click.echo(f"History save failed: {exc}")
    click.echo(f"Reports written to {out_path}")


@cli.group()
def provider() -> None:
    pass


@provider.command("list")
@click.argument("provider_name")
def provider_list(provider_name: str) -> None:
    import aibenchmark.plugins  # noqa: F401 - trigger built-in registration
    try:
        engine = BenchEngine()
    except RuntimeError as exc:
        raise click.ClickException(str(exc))

    cls = engine.plugins.get(PluginCategory.PROVIDER, provider_name)
    if cls is None:
        raise click.BadParameter(f"Unknown provider: {provider_name}")

    cfg = engine.config.provider_config(provider_name)
    api_key = cfg.get("api_key", "")
    if not api_key:
        raise click.ClickException(f"Missing API key for provider '{provider_name}'. Set {cfg.get('api_key_env', 'API_KEY')}.")
    try:
        p = cls(api_key=api_key, base_url=cfg.get("base_url", ""))
        models = p.list_models()
        for m in models:
            click.echo(m)
    except Exception as exc:
        raise click.ClickException(f"Failed to list models for {provider_name}: {exc}") from exc


@cli.command("diagnostics")
def diagnostics() -> None:
    """Show startup diagnostics and system status."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine

    try:
        engine = BenchEngine()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(engine.diagnostics_summary())


@cli.command("providers")
def providers() -> None:
    """List all registered providers."""
    import aibenchmark.plugins  # noqa: F401
    engine = BenchEngine()
    for name in engine.list_providers():
        click.echo(name)


@provider.command("info")
@click.argument("provider_name")
def provider_info(provider_name: str) -> None:
    """Print detailed provider info and metadata."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    try:
        meta = registry.metadata(provider_name)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    for k, v in meta.items():
        click.echo(f"{k}: {v}")


@provider.command("health")
@click.option("--provider", "provider_name", default=None, help="Specific provider to check.")
def provider_health(provider_name: str) -> None:
    """Show provider health status."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        try:
            h = registry.health(provider_name)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Provider: {h.provider_name}")
        click.echo(f"Status: {h.status}")
        click.echo(f"Availability: {h.availability:.2%}")
        click.echo(f"Average Latency: {h.average_latency_ms:.1f}ms" if h.average_latency_ms else "Average Latency: N/A")
        click.echo(f"Failure Rate: {h.failure_rate:.2%}")
        click.echo(f"Total Checks: {h.total_checks}")
        click.echo(f"Rate Limit: {h.rate_limit.retry_recommendation}")
    else:
        for name in registry.list_providers():
            h = registry.health(name)
            click.echo(f"{name}: {h.status} | failure={h.failure_rate:.2%} | latency={h.average_latency_ms or 0:.1f}ms")


@provider.command("compare")
@click.argument("provider_names", nargs=-1)
def provider_compare(provider_names: tuple[str, ...]) -> None:
    """Compare providers and show ranking."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    names = list(provider_names) or registry.list_providers()
    comparison = registry.compare_providers(names, {n: [] for n in names})
    click.echo("Overall Ranking:")
    for entry in comparison.get("overall_ranking", []):
        click.echo(f"#{entry['rank']} {entry['provider']}: score={entry['score']:.4f}")


@cli.command("models")
@click.argument("provider_name", required=False)
def models(provider_name: str) -> None:
    """List models for a provider."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    for name in names:
        try:
            ms = registry.list_models(name)
            click.echo(f"== {name} ({len(ms)} models) ==")
            for m in ms[:20]:
                click.echo(f"  {m}")
            if len(ms) > 20:
                click.echo(f"  ... and {len(ms) - 20} more")
        except ValueError as exc:
            click.echo(f"{name}: {exc}")


@cli.command("capabilities")
@click.argument("provider_name", required=False)
def capabilities(provider_name: str) -> None:
    """Show provider capabilities."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    for name in names:
        try:
            caps = registry.capabilities(name)
            click.echo(f"== {name} ==")
            for flag in caps.flags():
                click.echo(f"  {flag}: enabled")
            if caps.context_window:
                click.echo(f"  context_window: {caps.context_window}")
        except ValueError as exc:
            click.echo(f"{name}: {exc}")


@cli.command("auth")
@click.argument("provider_name", required=False)
def auth(provider_name: str) -> None:
    """Validate authentication credentials."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    for name in names:
        result = registry.validate_configuration(name)
        status = "VALID" if result["valid"] else "INVALID"
        click.echo(f"{name}: {status}")
        for issue in result.get("issues", []):
            click.echo(f"  - {issue}")


@provider.command("capabilities")
@click.argument("provider_name", required=False)
def provider_capabilities(provider_name: str) -> None:
    """Show provider capabilities."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    for name in names:
        try:
            caps = registry.capabilities(name)
            click.echo(f"== {name} ==")
            for flag in caps.flags():
                click.echo(f"  {flag}: enabled")
            if caps.context_window:
                click.echo(f"  context_window: {caps.context_window}")
        except ValueError as exc:
            click.echo(f"{name}: {exc}")


@provider.command("validate")
@click.argument("provider_name", required=False)
def provider_validate(provider_name: str) -> None:
    """Run full provider validation and generate a report."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    all_results = registry.validate_all()
    for name in names:
        result = all_results.get(name, {"valid": False, "issues": ["Unknown provider"]})
        status = "PASS" if result.get("valid") else "FAIL"
        click.echo(f"{name}: {status}")
        for issue in result.get("issues", []):
            click.echo(f"  - {issue}")


@provider.command("certify")
@click.argument("provider_name", required=False)
def provider_certify(provider_name: str) -> None:
    """Generate provider certification report."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    if provider_name:
        names = [provider_name]
    else:
        names = registry.list_providers()
    for name in names:
        try:
            report = registry.certify(name)
            click.echo(report.summary())
        except ValueError as exc:
            click.echo(f"{name}: {exc}")
        click.echo("")


@cli.command("discover")
def discover() -> None:
    """Discover and list all plugins."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.plugin.registry import get_manager
    mgr = get_manager()
    click.echo("Providers:")
    for p in mgr.list_names(PluginCategory.PROVIDER):
        click.echo(f"  {p}")
    click.echo("Benchmarks:")
    for p in mgr.list_names(PluginCategory.BENCHMARK):
        click.echo(f"  {p}")
    click.echo("Reporters:")
    for p in mgr.list_names(PluginCategory.REPORTER):
        click.echo(f"  {p}")
    click.echo("Evaluators:")
    for p in mgr.list_names(PluginCategory.EVALUATOR):
        click.echo(f"  {p}")
    click.echo("Strategies:")
    for p in mgr.list_names(PluginCategory.STRATEGY):
        click.echo(f"  {p}")


@cli.group("plugin")
def plugin_group() -> None:
    """Plugin management commands."""
    pass


@plugin_group.command("validate")
def plugin_validate() -> None:
    """Validate all plugin metadata and API version compatibility."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.plugin.registry import validate_all_plugins

    results = validate_all_plugins()
    invalid = [r for r in results if not r["valid"]]
    click.echo(f"Validated {len(results)} plugins.")
    if invalid:
        click.echo(f"\n{len(invalid)} plugin(s) with issues:")
        for r in invalid:
            click.echo(f"  [{r['category']}] {r['name']}:")
            for issue in r.get("issues", []):
                click.echo(f"    - {issue}")
    else:
        click.echo("All plugins are valid.")


@plugin_group.command("list")
def plugin_list() -> None:
    """List plugins by category."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.plugin.registry import get_manager

    mgr = get_manager()
    click.echo("Providers:")
    for p in mgr.list_names(PluginCategory.PROVIDER):
        click.echo(f"  {p}")
    click.echo("Benchmarks:")
    for p in mgr.list_names(PluginCategory.BENCHMARK):
        click.echo(f"  {p}")
    click.echo("Reporters:")
    for p in mgr.list_names(PluginCategory.REPORTER):
        click.echo(f"  {p}")
    click.echo("Evaluators:")
    for p in mgr.list_names(PluginCategory.EVALUATOR):
        click.echo(f"  {p}")
    click.echo("Strategies:")
    for p in mgr.list_names(PluginCategory.STRATEGY):
        click.echo(f"  {p}")


def main() -> None:
    cli()


# ============================================================
# Sprint 3 Analytics Commands
# ============================================================


@cli.group()
def leaderboard() -> None:
    """Sprint 3: historical and category leaderboards."""


@leaderboard.command()
@click.option("--runs", default=1, show_default=True, help="Number of latest runs to aggregate.")
@click.option("--out", "-o", default="history", show_default=True)
def generate(runs: int, out: str) -> None:
    """Generate leaderboard report from persisted run history."""
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    from aibenchmark.app.engine import BenchEngine

    # Use cached reporter plugins
    engine = BenchEngine()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results, out_path, formats=["leaderboard"])
    click.echo(f"Leaderboard written to {out_path / 'results.leaderboard'}")


@cli.command()
@click.option("--runs", default=1, show_default=True, help="Number of latest runs to aggregate.")
@click.option("--out", "-o", default="history", show_default=True)
def recommend(runs: int, out: str) -> None:
    """Recommend best model per category based on history."""
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    engine = BenchEngine()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results, out_path, formats=["recommendations"])
    click.echo(f"Recommendations written to {out_path / 'results.recommendations'}")


@cli.command()
@click.option("--runs", default=1, show_default=True)
@click.option("--out", "-o", default="history", show_default=True)
def team(runs: int, out: str) -> None:
    """Build an AI engineering team from latest history."""
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    engine = BenchEngine()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results, out_path, formats=["team"])
    click.echo(f"Team report written to {out_path / 'results.team'}")


@cli.command()
@click.option("--against", "against_runs", default=2, show_default=True, help="Compare latest run against N-th latest.")
@click.option("--out", "-o", default="history", show_default=True)
def compare(against_runs: int, out: str) -> None:
    """Compare latest run against N-th latest run."""
    latest = load_latest(against_runs)
    if len(latest) < 2:
        click.echo("Not enough history for comparison.")
        return
    results_a = latest[0]
    engine = BenchEngine()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results_a, out_path, formats=["compare"])
    click.echo(f"Comparison written to {out_path / 'results.compare'}")


@cli.command()
@click.option("--runs", default=5, show_default=True, help="Max runs to analyze.")
@click.option("--out", "-o", default="history", show_default=True)
def trends(runs: int, out: str) -> None:
    """Show trends across the latest N runs."""
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    engine = BenchEngine()
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine.generate_reports(results, out_path, formats=["trends"])
    click.echo(f"Trends written to {out_path / 'results.trends'}")


@cli.command()
@click.option("--runs", default=1, show_default=True)
def explain(runs: int) -> None:
    """Print human-readable recommendation explanation to stdout."""
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    from aibenchmark.app.analytics import recommend, build_team, build_leaderboard
    from aibenchmark.app.analytics import fastest, highest_quality, best_value

    results = latest[0]
    click.echo("=== Recommendations ===")
    for rec in recommend(results):
        click.echo(f"{rec.category}: {rec.model} ({rec.provider}) conf={rec.confidence:.2f} {rec.confidence_label}")
        for reason in rec.reasons:
            click.echo(f"  - {reason}")
    click.echo("\n=== AI Engineering Team ===")
    for role in build_team(results):
        click.echo(f"{role.role}: {role.model} ({role.provider}) score={role.score:.2f} conf={role.confidence:.2f}")
    click.echo("\n=== Leaderboard Top 3 ===")
    for row in build_leaderboard(results)[:3]:
        click.echo(f"#{row.rank} {row.model} ({row.provider}) overall={row.overall:.2f}")
    fa = fastest(results)
    hq = highest_quality(results)
    mv = best_value(results)
    if fa:
        click.echo(f"Fastest: {fa.model} ({fa.provider}) latency_ms={_parse_latency(fa)}")
    if hq:
        click.echo(f"Highest quality: {hq.model} ({hq.provider}) overall={hq.overall:.2f}")
    if mv:
        click.echo(f"Best value: {mv.model} ({mv.provider})")


# ============================================================
# Sprint 4: Validation / Calibration / Stats / Reliability /
#           Reproduce / Cost / Metadata Commands
# ============================================================


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def validate(out: str) -> None:
    """Validate benchmark results and scoring integrity."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    from aibenchmark.app.auto_validation import auto_validate

    latest = load_latest(1)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    runs: list[list[BenchmarkResult]] | None = None
    if len(load_latest(2)) >= 2:
        runs = load_latest(2)
    report = auto_validate(results, runs=runs or [])
    click.echo(report.summary())
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["validation"])
    click.echo(f"Validation report written to {out_path / 'results.validation'}")


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def calibrate(out: str) -> None:
    """Run benchmark calibration and generate report."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    runs = load_latest(5)
    if not runs:
        click.echo("No history available.")
        return
    results = runs[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["calibration"], runs=runs)
    click.echo(f"Calibration report written to {out_path / 'results.calibration'}")


@cli.command()
@click.option("--runs", default=1, show_default=True)
@click.option("--out", "-o", default="history", show_default=True)
def stats(runs: int, out: str) -> None:
    """Generate statistical summary for latest runs."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["statistics"], runs=latest)
    click.echo(f"Statistics report written to {out_path / 'results.statistics'}")


@cli.command()
@click.option("--runs", default=1, show_default=True)
@click.option("--out", "-o", default="history", show_default=True)
def reliability(runs: int, out: str) -> None:
    """Generate reliability metrics report."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(runs)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["reliability"], runs=latest)
    click.echo(f"Reliability report written to {out_path / 'results.reliability'}")


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def reproduce(out: str) -> None:
    """Print reproducibility metadata for latest run."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(1)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["metadata"])
    click.echo(f"Reproducibility metadata written to {out_path / 'results.metadata'}")


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def cost(out: str) -> None:
    """Generate cost estimation report."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(1)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["cost"], runs=latest)
    click.echo(f"Cost report written to {out_path / 'results.cost'}")


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def tokens(out: str) -> None:
    """Generate token usage report."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(1)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["tokens"], runs=latest)
    click.echo(f"Token usage report written to {out_path / 'results.tokens'}")


@cli.command()
@click.option("--out", "-o", default="history", show_default=True)
def governance(out: str) -> None:
    """Generate governance/recommendation explainability report."""
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.history import load_latest
    latest = load_latest(1)
    if not latest:
        click.echo("No history available.")
        return
    results = latest[0]
    out_path = Path(out)
    out_path.mkdir(parents=True, exist_ok=True)
    engine = BenchEngine()
    engine.generate_reports(results, out_path, formats=["governance"])
    click.echo(f"Governance report written to {out_path / 'results.governance'}")


@cli.command("route")
@click.argument("benchmark_name", required=False)
def route(benchmark_name: str) -> None:
    """Show routing plan for benchmark without executing."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.models import BenchmarkName

    engine = BenchEngine()
    names = [BenchmarkName(benchmark_name)] if benchmark_name else list(BenchmarkName)
    for name in names:
        try:
            plan = engine.select_model({"benchmark_name": name.value})
        except Exception as exc:
            click.echo(f"{name.value}: ERROR {exc}")
            continue
        click.echo(f"=== {name.value} ===")
        click.echo(f"Provider: {plan['provider']}")
        click.echo(f"Model: {plan['model']}")
        click.echo(f"Rationale: {plan['rationale']}")
        if plan.get("fallback_providers"):
            click.echo(f"Fallbacks: {', '.join(plan['fallback_providers'])}")
        click.echo("")


@cli.command("select")
@click.argument("benchmark_name")
@click.option("--provider", default=None)
@click.option("--model", default=None)
def select(benchmark_name: str, provider: str, model: str) -> None:
    """Automatic model selection for category."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine

    engine = BenchEngine()
    try:
        plan = engine.select_model(
            {
                "benchmark_name": benchmark_name,
                "provider_name": provider,
                "model": model,
            }
        )
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Selected: {plan['provider']} / {plan['model']}")
    click.echo(f"Rationale: {plan['rationale']}")


@cli.command("fallback")
@click.argument("provider_name")
@click.argument("model", required=False)
def fallback(provider_name: str, model: str) -> None:
    """Test fallback chain for provider/model."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine

    engine = BenchEngine()
    plan = {
        "provider": provider_name,
        "model": model or "",
        "fallback_providers": engine.config.routing.get("fallback_chain", []),
    }
    result = engine.apply_policy(plan)
    click.echo(f"Primary: {result['provider']} / {result['model']}")
    click.echo(f"Fallbacks: {', '.join(result.get('fallback_providers', []))}")


@cli.command("optimize")
@click.option("--benchmark", "-b", multiple=True, default=None)
@click.option("--provider", default=None)
def optimize(benchmark: str, provider: str) -> None:
    """Cost-optimized benchmark execution preview."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.models import BenchmarkName

    engine = BenchEngine()
    names = [BenchmarkName(b) for b in benchmark] if benchmark else list(BenchmarkName)
    for name in names:
        try:
            plan = engine.select_model(
                {"benchmark_name": name.value, "provider_name": provider, "prefer_free": True}
            )
        except Exception as exc:
            click.echo(f"{name.value}: ERROR {exc}")
            continue
        click.echo(f"{name.value}: {plan['provider']} / {plan['model']} (est={plan.get('estimated_cost', 0.0):.4f})")


@cli.command("parallel")
@click.option("--providers", "-p", multiple=True, required=True)
@click.option("--benchmark", "-b", multiple=True, default=None)
def parallel(providers: tuple[str, ...], benchmark: str) -> None:
    """Multi-provider parallel execution."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.models import BenchmarkName

    try:
        engine = BenchEngine()
    except RuntimeError as exc:
        raise click.ClickException(str(exc)) from exc
    names = [BenchmarkName(b) for b in benchmark] if benchmark else engine.list_benchmarks()
    model = engine.config.defaults().get("default_model", "")
    messages = [{"role": "user", "content": "Say hello"}]
    benchmark_strs = [n.value if isinstance(n, BenchmarkName) else str(n) for n in names]
    try:
        results = engine.run_parallel(list(providers), model, benchmark_strs, messages)
    except ConfigError as exc:
        raise click.ClickException(str(exc)) from exc
    for r in results:
        status = r.metadata.get("status", "success")
        click.echo(f"{r.provider.value}/{r.model}: {r.overall:.2f} [{status}]")


@cli.group("config")
def config_group() -> None:
    pass


@config_group.command("generate-litellm")
@click.option("--out", "-o", default="configs/litellm.yaml", show_default=True)
def config_generate_litellm(out: str) -> None:
    """Generate LiteLLM configuration."""
    import aibenchmark.plugins  # noqa: F401
    from aibenchmark.app.engine import BenchEngine

    engine = BenchEngine()
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine.generate_reports([], path, formats=["litellm_config"])
    click.echo(f"LiteLLM configuration written to {path}")


def _parse_latency(result: Any) -> float | None:
    latency = None
    if hasattr(result, "metadata"):
        latency = result.metadata.get("latency_ms") if isinstance(result.metadata, dict) else None
    if latency is None and hasattr(result, "details"):
        latency = result.details.get("latency_ms") if isinstance(result.details, dict) else None
    if latency is None:
        return None
    try:
        return float(latency)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
