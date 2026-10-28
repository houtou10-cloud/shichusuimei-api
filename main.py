import logging
import sys
import time

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
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

    started = time.perf_counter()
    status = "ok"
    try:
        from engine.solar_terms import _get_ephemeris, _get_timescale

        _get_timescale()
        _get_ephemeris()
    except Exception:
        status = "skipped"
        logger.debug("chart runtime warm-up skipped", exc_info=True)
    finally:
        sys.stderr.write(
            f"[PERF_STARTUP] step=chart_runtime_warmup status={status} "
            f"elapsed={time.perf_counter() - started:.3f}s\n"
        )
        sys.stderr.flush()


@app.on_event("startup")
def warm_chart_runtime() -> None:
    _warm_chart_runtime()

@app.get("/")
def root(request: Request):
    # ブラウザで開いた人は販売ページへ。監視やAPIの呼び出し（HTML以外）には従来どおりJSONを返す。
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/career-reading", status_code=302)
    return {"status":"ok","message":"Shichusuimei API is running."}
