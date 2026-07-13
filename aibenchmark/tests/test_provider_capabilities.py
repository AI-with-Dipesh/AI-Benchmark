from __future__ import annotations

import pytest

from aibenchmark.app.provider_capabilities import ProviderCapabilityDetector


class TestProviderCapabilityDetector:
    def test_detect_nvidia_caps(self) -> None:
        det = ProviderCapabilityDetector()
        caps = det.detect("nvidia")
        assert caps.chat is True
        assert caps.streaming is True
        assert caps.json_mode is True
        assert caps.context_window == 128000

    def test_detect_openrouter_caps(self) -> None:
        det = ProviderCapabilityDetector()
        caps = det.detect("openrouter")
        assert caps.vision is True
        assert caps.tool_calling is True
        assert caps.structured_output is True
        assert caps.context_window == 200000

    def test_detect_ollama_caps(self) -> None:
        det = ProviderCapabilityDetector()
        caps = det.detect("ollama")
        assert caps.function_calling is True
        assert caps.long_context is True

    def test_detect_unknown_returns_basic(self) -> None:
        det = ProviderCapabilityDetector(provider_names=["fake_provider"])
        caps = det.detect("fake_provider")
        assert caps.chat is False

    def test_has_capability(self) -> None:
        det = ProviderCapabilityDetector()
        caps = det.detect("nvidia")
        assert caps.has("chat") is True
        assert caps.has("vision") is False

    def test_flags_returns_list(self) -> None:
        det = ProviderCapabilityDetector()
        caps = det.detect("nvidia")
        flags = caps.flags()
        assert "chat" in flags
        assert "streaming" in flags

    def test_detect_from_config_tags(self) -> None:
        from aibenchmark.app.models import ProviderPluginConfig
        det = ProviderCapabilityDetector()
        cfg = ProviderPluginConfig(name="ollama", tags=["audio", "reasoning"])
        caps = det.detect_from_config(cfg)
        assert caps.audio is True
        assert caps.reasoning is True
