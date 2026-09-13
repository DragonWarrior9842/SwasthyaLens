import pytest
from fastapi.testclient import TestClient


def test_health_returns_the_public_liveness_contract(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {"status": "ok", "service": "swasthyalens-api"}


def test_health_does_not_accept_mutations(client: TestClient) -> None:
    assert client.post("/health", json={"status": "changed"}).status_code == 405


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173"])
def test_allowed_frontend_can_read_health(client: TestClient, origin: str) -> None:
    response = client.get("/health", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "access-control-allow-credentials" not in response.headers
    assert "Origin" in response.headers["vary"]


def test_unlisted_origin_receives_no_cors_permission(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://untrusted.example"})

    # CORS controls browser access; it does not authenticate this public endpoint.
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_allowed_get_preflight_succeeds(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-methods"] == "GET"
    assert "access-control-allow-credentials" not in response.headers


@pytest.mark.parametrize(
    ("origin", "method"),
    [
        ("https://untrusted.example", "GET"),
        ("http://localhost:5173", "POST"),
    ],
)
def test_disallowed_preflight_is_rejected(client: TestClient, origin: str, method: str) -> None:
    response = client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": method},
    )

    assert response.status_code == 400
