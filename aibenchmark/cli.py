import click
from pathlib import Path

from aibenchmark.app.engine import BenchEngine
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


def main():
    cli()


if __name__ == "__main__":
    main()
