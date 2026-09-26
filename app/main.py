import logging
import secrets
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.routes import router
from app.core.config import settings
from app.core.logging import configure
from app.db.database import get_db
from app.services.market_data import MarketDataError

configure(settings().log_level)
app = FastAPI(
    title="MarketPulse",
    version="1.0.0",
    description="Reproducible quantitative research. Synthetic demo data is not market history.",
)


def authorize(request: Request):
    key = settings().api_key
    if key and not secrets.compare_digest(request.headers.get("X-API-Key", ""), key):
        raise HTTPException(401, "Invalid API key")


@app.exception_handler(MarketDataError)
async def market_error(request, exc):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


app.include_router(router, dependencies=[Depends(authorize)])


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    logging.getLogger("requests").info(
        "method=%s path=%s status=%s elapsed_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.exception_handler(ValueError)
async def invalid_research(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(LookupError)
async def missing_resource(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    logging.getLogger(__name__).error(
        "Unhandled error type=%s path=%s", type(exc).__name__, request.url.path
    )
    return JSONResponse(status_code=500, content={"detail": "Internal error; consult server logs"})


@app.get("/health")
def health(db=Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "version": "1.0.0"}
