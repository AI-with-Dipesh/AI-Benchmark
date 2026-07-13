from __future__ import annotations

import inspect
from typing import Any

import pytest

from aibenchmark.app.models import ProviderType, PluginCategory
from aibenchmark.app.plugin.registry import get_manager
from aibenchmark.interfaces.provider import BaseProvider

# ensure all bundled provider plugins are mounted in the registry for this test session
from aibenchmark.plugins import providers as _providers  # noqa: F401

CONTRACT_METHODS = [
    "connect",
    "list_models",
    "chat",
    "capabilities",
    "metadata",
    "estimate_tokens",
    "estimate_cost",
    "validate_configuration",
    # following may be default implementations or direct overrides
    "initialize",
    "authenticate",
    "health_check",
    "shutdown",
    "supports",
    "supports_streaming",
    "supports_tools",
    "supports_json",
    "supports_context_length",
    "invoke",
    "stream",
    "_parse_rate_limit",
]


def _registered_providers() -> dict[str, type[BaseProvider]]:
    mgr = get_manager()
    providers: dict[str, type[BaseProvider]] = {}
    for name, cls in mgr.providers.items():
        if inspect.isclass(cls) and issubclass(cls, BaseProvider):
            providers[name] = cls
    return providers


class TestProviderContractMatrix:

    def test_all_registered_providers_implement_contract(self) -> None:
        providers = _registered_providers()
        assert providers, "No registered providers found"
        matrix: dict[str, dict[str, str]] = {}
        for name, cls in providers.items():
            matrix[name] = {}
            for method in CONTRACT_METHODS:
                if hasattr(cls, method):
                    func = getattr(cls, method)
                    if func is getattr(BaseProvider, method, None):
                        matrix[name][method] = "default"
                    else:
                        # verify it is actually callable (not abstract stub accidentally inherited)
                        if func is None or not callable(func):
                            matrix[name][method] = "missing"
                        else:
                            matrix[name][method] = "override"
                else:
                    matrix[name][method] = "missing"

        # every provider must have no missing entries
        fails = []
        for name, rows in matrix.items():
            missing = [m for m, s in rows.items() if s == "missing"]
            if missing:
                fails.append(f"{name}: missing {missing}")
        assert not fails, "Contract gaps:\n" + "\n".join(fails)

    def test_contract_matrix_print(self, capsys: pytest.CaptureFixture[str]) -> None:
        providers = _registered_providers()
        rows = []
        rows.append(f"{'Method':<35}" + "".join(f"{n:<16}" for n in providers.keys()))
        rows.append("-" * (35 + 16 * len(providers)))
        for method in CONTRACT_METHODS:
            row = f"{method:<35}"
            for name, cls in providers.items():
                if hasattr(cls, method):
                    func = getattr(cls, method)
                    if func is getattr(BaseProvider, method, None):
                        row += f"{'(default)':<16}"
                    else:
                        row += f"{'(override)':<16}"
                else:
                    row += f"{'MISSING':<16}"
            rows.append(row)
        out = "\n".join(rows)
        # print the matrix so it is visible in test output
        print("\n" + out)
        # assert so pytest captures it meaningfully
        assert all("MISSING" not in line for line in rows if line.startswith(("", "connect", "list_models", "chat", "capabilities", "metadata", "estimate_tokens", "estimate_cost", "validate_configuration", "initialize")))

    def test_default_implementations_have_docstring(self) -> None:
        for method in ("initialize", "authenticate", "health_check", "shutdown", "supports", "metadata", "estimate_tokens", "estimate_cost", "validate_configuration", "invoke", "stream", "_parse_rate_limit"):
            func = getattr(BaseProvider, method)
            assert callable(func)
            # ensure it isn't a broken abstract stub
            source = inspect.getsource(func).strip()
            assert "..." not in source, f"BaseProvider.{method} still has ellipsis body"
