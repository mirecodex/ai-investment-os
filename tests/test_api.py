from __future__ import annotations

import dataclasses

import pytest
from fastapi.testclient import TestClient

from investment_os.app.container import Container
from investment_os.interfaces.api import create_app


@pytest.fixture()
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_tickers_lists_universe(client: TestClient) -> None:
    symbols = [t["ticker"] for t in client.get("/tickers").json()]
    assert {"BBCA", "ANTM", "TLKM", "SIDO"} <= set(symbols)


def test_brief_carries_disclaimer(client: TestClient) -> None:
    payload = client.get("/brief").json()
    assert "sentiment" in payload and "macro" in payload
    assert "bukan nasihat investasi" in payload["disclaimer"]


def test_analyze_returns_full_report(client: TestClient) -> None:
    payload = client.post("/analyze/bbca").json()
    assert payload["ticker"] == "BBCA"
    assert payload["decision"]["verdict"] == "BUY"
    assert payload["evidence"], "report must carry evidence"
    assert payload["audit_trail"][0]["node"] == "load_context"
    assert "bukan nasihat investasi" in payload["disclaimer"]


def test_analyze_unknown_ticker_404(client: TestClient) -> None:
    assert client.post("/analyze/ZZZZ").status_code == 404


def test_recommendations_history_flows_through(client: TestClient) -> None:
    client.post("/analyze/TLKM")
    records = client.get("/recommendations", params={"ticker": "TLKM", "limit": 5}).json()
    assert records and records[0]["ticker"] == "TLKM"
    assert records[0]["verdict"] == "HOLD"


def test_calibration_empty_state(client: TestClient) -> None:
    payload = client.get("/calibration", params={"horizon": "99d"}).json()
    assert payload["directional_count"] == 0
    assert payload["overall_hit_rate"] is None


def test_dashboard_serves_self_contained_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    page = response.text
    for marker in ("/brief", "/calibration", "/recommendations", "/tickers", "/analyze/"):
        assert marker in page  # the page drives the existing JSON endpoints
    assert "https://" not in page  # strictly self-contained: no external assets


def test_basic_auth_locks_everything_but_health(container: Container) -> None:
    secured = dataclasses.replace(
        container,
        settings=container.settings.model_copy(update={"api_auth": "ops:rahasia"}),
    )
    locked = TestClient(create_app(secured))

    assert locked.get("/health").status_code == 200  # probes stay unauthenticated
    denied = locked.get("/")
    assert denied.status_code == 401
    assert denied.headers["www-authenticate"].startswith("Basic")
    assert locked.get("/tickers", auth=("ops", "salah")).status_code == 401
    assert locked.get("/tickers", auth=("ops", "rahasia")).status_code == 200
    assert locked.get("/", auth=("ops", "rahasia")).status_code == 200


def test_no_auth_configured_leaves_api_open(client: TestClient) -> None:
    assert client.get("/tickers").status_code == 200
