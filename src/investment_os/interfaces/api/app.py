from __future__ import annotations

import base64
import secrets
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse

from investment_os import __version__
from investment_os.app.container import Container
from investment_os.core.service import TickerNotFoundError
from investment_os.eval import reliability_report
from investment_os.interfaces.api.dashboard import DASHBOARD_HTML

DISCLAIMER = "Riset & edukasi, bukan nasihat investasi. Keputusan tetap tanggung jawab pengguna."


def _basic_auth_ok(header: str | None, expected: str) -> bool:
    if not header or not header.startswith("Basic "):
        return False
    try:
        supplied = base64.b64decode(header.removeprefix("Basic "), validate=True).decode()
    except (ValueError, UnicodeDecodeError):
        return False
    return secrets.compare_digest(supplied.encode(), expected.encode())


def create_app(container: Container) -> FastAPI:
    app = FastAPI(
        title="AI Investment OS — Internal API",
        version=__version__,
        description=DISCLAIMER,
    )

    credentials = container.settings.api_auth
    if credentials:

        @app.middleware("http")
        async def require_auth(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ) -> Response:
            # /health stays open for container healthchecks and probes.
            if request.url.path != "/health" and not _basic_auth_ok(
                request.headers.get("Authorization"), credentials
            ):
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="investment-os"'},
                )
            return await call_next(request)

    @app.get("/", include_in_schema=False)
    def dashboard() -> HTMLResponse:
        return HTMLResponse(DASHBOARD_HTML)

    @app.get("/health")
    def health() -> dict[str, str]:
        if not container.kb.list_tickers():
            raise HTTPException(status_code=503, detail="knowledge base kosong")
        with container.db.transaction() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "version": __version__}

    @app.get("/tickers")
    def tickers() -> list[dict[str, str]]:
        return [profile.model_dump() for profile in container.kb.list_tickers()]

    @app.get("/brief")
    def brief() -> dict[str, object]:
        payload = container.analysis.daily_brief().model_dump(mode="json")
        payload["disclaimer"] = DISCLAIMER
        return payload

    @app.post("/analyze/{ticker}")
    async def analyze(ticker: str) -> dict[str, object]:
        try:
            result = await container.analysis.analyze(ticker)
        except TickerNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        payload = result.report.model_dump(mode="json")
        payload["disclaimer"] = DISCLAIMER
        return payload

    @app.get("/recommendations")
    def recommendations(
        ticker: str | None = Query(default=None),
        limit: int = Query(default=20, ge=1, le=200),
    ) -> list[dict[str, object]]:
        records = container.recommendations.history(ticker, limit=limit)
        return [record.model_dump(mode="json") for record in records]

    @app.get("/calibration")
    def calibration(horizon: str = Query(default="20d")) -> dict[str, object]:
        outcomes = container.recommendations.calibration_pairs(horizon=horizon)
        report = reliability_report(outcomes, horizon=horizon)
        return {
            "horizon": report.horizon,
            "directional_count": report.directional_count,
            "overall_hit_rate": report.overall_hit_rate,
            "ece": report.ece,
            "buckets": [bucket.__dict__ for bucket in report.buckets],
        }

    return app
