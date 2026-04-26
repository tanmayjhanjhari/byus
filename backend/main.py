"""
ByUs Backend — FastAPI Application Entry Point
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from routers import upload, analyze, mitigate, report, gemini_chat, explain

# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise in-memory session store on startup
    app.state.sessions = {}
    yield
    # Nothing to clean up on shutdown for in-memory store


async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": True, "detail": str(exc), "code": 500}
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    content = {"error": True, "detail": str(exc.detail), "code": exc.status_code}
    if exc.status_code == 503:
        content["fallback"] = True
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="ByUs API",
        description=(
            "Detect, explain, and mitigate bias in datasets and ML models "
            "using Google Gemini 2.0 Flash."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # ── Exception Handlers ──────────────────────────────────────────────────
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ─────────────────────────────────────────────────────────────
    app.include_router(upload.router, prefix="/api")
    app.include_router(analyze.router, prefix="/api")
    app.include_router(mitigate.router, prefix="/api")
    app.include_router(report.router, prefix="/api")
    app.include_router(gemini_chat.router, prefix="/api")
    app.include_router(explain.router, prefix="/api")

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/api/health", tags=["Health"])
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
