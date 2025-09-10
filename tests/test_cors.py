"""Tests for CORS configuration based on environment."""

from fastapi.testclient import TestClient
from backend.main import create_app


def test_allowed_origin_dev(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    app = create_app()
    client = TestClient(app)
    response = client.options(
        "/",
        headers={
            "Origin": "http://localhost",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost"


def test_disallowed_origin(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    app = create_app()
    client = TestClient(app)
    response = client.options(
        "/",
        headers={
            "Origin": "http://malicious.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers


def test_allowed_origin_prod(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "prod")
    app = create_app()
    client = TestClient(app)
    response = client.options(
        "/",
        headers={
            "Origin": "https://nugamoto.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://nugamoto.example.com"
    )
