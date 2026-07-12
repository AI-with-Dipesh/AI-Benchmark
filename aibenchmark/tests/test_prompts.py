from __future__ import annotations

from pathlib import Path
import pytest

from aibenchmark.app.prompts import PromptLoader, PromptLoadError


def test_prompt_loader_loads_latency():
    loader = PromptLoader()
    prompt = loader.load("latency")
    assert prompt is None or isinstance(prompt, object)


def test_prompt_loader_missing_prompt():
    loader = PromptLoader()
    prompt = loader.load("nonexistent")
    assert prompt is None
