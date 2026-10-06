import logging

from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="Shichusuimei API", version="0.1.0")
app.include_router(router)

logger = logging.getLogger(__name__)


def _warm_chart_runtime() -> None:
    """Load astronomy resources before the first customer request.

    ``calculate_chart`` already caches these resources.  Warming the caches
    during application startup moves the one-time Skyfield file load out of
    the first /app/reading request without changing any calculation result.
    The warm-up is best-effort so a missing optional resource preserves the
    existing request-time error behavior.
    """

    try:
        from engine.solar_terms import _get_ephemeris, _get_timescale

        _get_timescale()
        _get_ephemeris()
    except Exception:
        logger.debug("chart runtime warm-up skipped", exc_info=True)


@app.on_event("startup")
def warm_chart_runtime() -> None:
    _warm_chart_runtime()

@app.get("/")
def root():
    return {"status":"ok","message":"Shichusuimei API is running."}
