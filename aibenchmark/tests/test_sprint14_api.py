from __future__ import annotations

import json
import threading
import time
from typing import Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from aibenchmark.api.app import create_app


@pytest.fixture(scope="session")
def client() -> Any:
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


class TestSystemEndpoints:
    def test_health(self, client: Any) -> None:
        response = client.get("/api/v1/system/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_version(self, client: Any) -> None:
        response = client.get("/api/v1/system/version")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.1.0"
        assert data["api_version"] == "v1"

    def test_diagnostics(self, client: Any) -> None:
        response = client.get("/api/v1/system/diagnostics")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestProviderEndpoints:
    def test_list_providers(self, client: Any) -> None:
        response = client.get("/api/v1/providers/")
        assert response.status_code == 200
        data = response.json()
        assert "providers" in data
        assert "total" in data

    def test_list_all_models(self, client: Any) -> None:
        response = client.get("/api/v1/providers/models")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestBenchmarkEndpoints:
    def test_list_benchmarks(self, client: Any) -> None:
        response = client.get("/api/v1/benchmarks/")
        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert "total" in data

    def test_run_benchmark_not_found(self, client: Any) -> None:
        response = client.post(
            "/api/v1/benchmarks/run",
            json={"provider_name": "nonexistent", "model": "test", "benchmarks": ["coding"]},
        )
        assert response.status_code in (400, 404, 500, 422)

    def test_benchmark_history(self, client: Any) -> None:
        response = client.get("/api/v1/benchmarks/history")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data


class TestRecommendationEndpoints:
    def test_generate_recommendations(self, client: Any) -> None:
        response = client.post("/api/v1/recommendations/", json={"runs": 1})
        assert response.status_code == 200
        data = response.json()
        assert "items" in data


class TestRoutingEndpoints:
    def test_route(self, client: Any) -> None:
        response = client.post(
            "/api/v1/routing/",
            json={"benchmark_name": "coding", "prefer_free": False},
        )
        assert response.status_code in (200, 400, 404, 500)


class TestAnalyticsEndpoints:
    def test_leaderboard(self, client: Any) -> None:
        response = client.get("/api/v1/analytics/leaderboard")
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data

    def test_trends(self, client: Any) -> None:
        response = client.get("/api/v1/analytics/trends")
        assert response.status_code == 200
        data = response.json()
        assert "trends" in data

    def test_history(self, client: Any) -> None:
        response = client.get("/api/v1/analytics/history")
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data


class TestReportEndpoints:
    def test_generate_reports(self, client: Any) -> None:
        response = client.post(
            "/api/v1/reports/generate",
            json={"formats": ["json"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "files" in data


class TestConfigEndpoints:
    def test_get_config(self, client: Any) -> None:
        response = client.get("/api/v1/config/")
        assert response.status_code == 200
        data = response.json()
        assert "benchmark_version" in data
        assert "providers" in data

    def test_patch_config(self, client: Any) -> None:
        response = client.patch("/api/v1/config/", json={"weights": {"coding": 1.0}})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "read_only"


class TestErrorHandling:
    def test_validation_error(self, client: Any) -> None:
        response = client.post("/api/v1/routing/", json={"invalid": "data"})
        assert response.status_code == 422

    def test_cors_headers(self, client: Any) -> None:
        response = client.options("/api/v1/system/health", headers={"Origin": "http://example.com"})
        assert response.status_code in (200, 405)


class TestOpenAPI:
    def test_openapi_schema(self, client: Any) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/api/v1/system/health" in schema["paths"]

    def test_swagger_ui(self, client: Any) -> None:
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc(self, client: Any) -> None:
        response = client.get("/redoc")
        assert response.status_code == 200
