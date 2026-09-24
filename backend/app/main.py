from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.analyze import router as analyze_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

configure_logging()
log = get_logger("app")
settings = get_settings()

MULTIPART_OVERHEAD_BYTES = settings.max_message_body_chars * 4 + 64 * 1024

_expose_docs = not settings.is_production

app = FastAPI(
    title="Namma Kavacham AI",
    version="0.1.0",
    description=(
        "Explainable scam-risk assessment for messages, URLs, and screenshots. Deterministic checks "
        "decide the risk level; AI only explains. Missing or unavailable checks are never reported as safe."
    ),
    docs_url="/docs" if _expose_docs else None,
    redoc_url="/redoc" if _expose_docs else None,
    openapi_url="/openapi.json" if _expose_docs else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def limit_body_and_harden(request: Request, call_next):
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES:
        return JSONResponse(status_code=413, content={"error": "payload_too_large", "detail": "Request too large"})
    try:
        response = await call_next(request)
    except Exception as exc:
        # Handled here rather than by the Exception handler alone: Starlette re-raises after that
        # handler so the server prints a traceback, and exception text (e.g. a pydantic input_value)
        # could carry submitted content into the logs.
        response = await unhandled_handler(request, exc)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [{"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "validation_error", "detail": errors})


_ERROR_CODES = {413: "payload_too_large", 415: "unsupported_media_type", 422: "validation_error"}


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _ERROR_CODES.get(exc.status_code, "request_error")
    return JSONResponse(status_code=exc.status_code, content={"error": code, "detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_error", extra={"exc_type": type(exc).__name__})
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": "Analysis failed"})


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    return {"status": "ok", "virustotal_enabled": settings.virustotal_active, "gemini_configured": settings.gemini_configured}


app.include_router(analyze_router)
