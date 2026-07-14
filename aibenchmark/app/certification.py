from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

from aibenchmark.app.models import ProviderMetadata

logger = logging.getLogger(__name__)


class ProviderCertificationLevel(str, Enum):
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    STABLE = "stable"
    CERTIFIED = "certified"


@dataclass(frozen=True)
class ProviderCertificationReport:
    provider_name: str
    certification_level: ProviderCertificationLevel
    reliability_score: float = 0.0
    benchmark_success_rate: float = 0.0
    health_score: float = 0.0
    metadata_completeness: float = 0.0
    capability_detection_score: float = 0.0
    configuration_valid: bool = False
    connection_health: bool = True
    issues: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"Provider: {self.provider_name}",
            f"Certification Level: {self.certification_level.value.upper()}",
            f"Reliability Score: {self.reliability_score:.2f}",
            f"Benchmark Success Rate: {self.benchmark_success_rate:.2f}",
            f"Health Score: {self.health_score:.2f}",
            f"Metadata Completeness: {self.metadata_completeness:.2f}",
            f"Capability Detection: {self.capability_detection_score:.2f}",
            f"Configuration Valid: {self.configuration_valid}",
            f"Connection Health: {self.connection_health}",
        ]
        if self.issues:
            lines.append("Issues:")
            for issue in self.issues:
                lines.append(f"  - {issue}")
        return "\n".join(lines)


class ProviderCertifier:
    def __init__(self) -> None:
        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.provider_registry import ProviderRegistry

        self.registry = ProviderRegistry()

    def certify(self, provider_name: str) -> ProviderCertificationReport:
        issues: list[str] = []

        # 1. Configuration validation
        try:
            validation = self.registry.validate_configuration(provider_name)
            config_valid = validation.get("valid", False)
            if not config_valid:
                issues.extend(validation.get("issues", []))
        except Exception as exc:
            config_valid = False
            issues.append(f"Configuration validation failed: {exc}")

        # 2. Metadata completeness
        try:
            raw_meta = self.registry.metadata(provider_name)
            meta = ProviderMetadata(
                provider_name=raw_meta.get("provider_name", provider_name),
                endpoint=raw_meta.get("endpoint"),
                region=raw_meta.get("region"),
                supported_models=raw_meta.get("supported_models", []),
                authentication_type=raw_meta.get("authentication_type", ""),
                context_window=raw_meta.get("context_window"),
            )
            expected_fields = [
                "provider_name",
                "provider_version",
                "endpoint",
                "region",
                "capabilities",
                "supported_models",
                "authentication_type",
                "context_window",
                "streaming_support",
                "function_calling_support",
                "vision_support",
                "reasoning_support",
                "embeddings_support",
                "json_mode_support",
            ]
            present = sum(1 for f in expected_fields if getattr(meta, f, None) or (f == "capabilities" and raw_meta.get("capabilities")))
            metadata_completeness = present / len(expected_fields)
        except Exception as exc:
            issues.append(f"Metadata retrieval failed: {exc}")
            metadata_completeness = 0.0

        # 3. Capability detection
        try:
            caps = self.registry.capabilities(provider_name)
            expected_caps = [
                "chat",
                "reasoning",
                "streaming",
                "function_calling",
                "json_mode",
                "structured_output",
                "vision",
                "image_generation",
                "audio",
                "tool_calling",
                "long_context",
                "context_window",
                "max_output_tokens",
            ]
            detected = sum(1 for c in expected_caps if caps.has(c))
            capability_detection_score = detected / len(expected_caps)
        except Exception as exc:
            issues.append(f"Capability detection failed: {exc}")
            capability_detection_score = 0.0

        # 4. Health
        try:
            health = self.registry.health(provider_name)
            availability = health.availability
            connection_health = health.connection_health
            failure_rate = health.failure_rate
            latency = health.average_latency_ms or 0.0
            # Health score: availability * 0.4 + latency fitness * 0.3 + connection * 0.3
            latency_fitness = max(0.0, min(1.0, 1.0 - latency / 10000.0))
            health_score = availability * 0.4 + latency_fitness * 0.3 + (1.0 if connection_health else 0.0) * 0.3
            benchmark_success_rate = 1.0 - failure_rate
        except Exception as exc:
            issues.append(f"Health check failed: {exc}")
            availability = 0.0
            connection_health = False
            failure_rate = 1.0
            health_score = 0.0
            benchmark_success_rate = 0.0

        # 5. Reliability score
        reliability_score = health_score * 0.7 + benchmark_success_rate * 0.3

        # Certification level logic
        if not config_valid or not connection_health or metadata_completeness < 0.5:
            level = ProviderCertificationLevel.EXPERIMENTAL
        elif reliability_score >= 0.85 and metadata_completeness >= 0.8 and capability_detection_score >= 0.7 and config_valid:
            level = ProviderCertificationLevel.CERTIFIED
        elif reliability_score >= 0.7 and metadata_completeness >= 0.6 and capability_detection_score >= 0.5 and config_valid:
            level = ProviderCertificationLevel.STABLE
        else:
            level = ProviderCertificationLevel.BETA

        return ProviderCertificationReport(
            provider_name=provider_name,
            certification_level=level,
            reliability_score=reliability_score,
            benchmark_success_rate=benchmark_success_rate,
            health_score=health_score,
            metadata_completeness=metadata_completeness,
            capability_detection_score=capability_detection_score,
            configuration_valid=config_valid,
            connection_health=connection_health,
            issues=issues,
        )
