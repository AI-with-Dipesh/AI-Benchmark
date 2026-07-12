import click
from pathlib import Path
from typing import Any

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.history import load_latest, save_run
from aibenchmark.app.logging import setup_logging
from aibenchmark.app.models import BenchmarkName, PluginCategory

setup_logging()


@click.group()
def cli():
    pass


@cli.command()
@click.argument("provider_name")
@click.option("--model", "-m", required=False)
@click.option("--benchmark", "-b", multiple=True, default=None)
@click.option("--out", "-o", default="history")
def run(provider_name, model, benchmark, out):
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
        provider_name = defaults.get("default_provider")
        model = model or defaults.get("default_model")
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
def provider():
    pass


@provider.command("list")
@click.argument("provider_name")
def provider_list(provider_name):
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


def main() -> None:
    cli()


if __name__ == "__main__":
    main()


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
    from aibenchmark.app.history import init_db

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
    results_b = latest[1]
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
