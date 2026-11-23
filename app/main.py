import logging
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.api.router import api_router

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("attendance_gate")

# Initialize database schema
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Production-grade FastAPI service that validates attendance spreadsheets against versioned rules, "
        "quarantines files failing quality checks, and serves cleaned files and row-level reports."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests with execution duration."""
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000.0
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)"
    )
    return response


# Include API Endpoints (all routes: /uploads, /rules, /health)
app.include_router(api_router)

# Mount static assets
static_path = Path(__file__).resolve().parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serve the interactive web UI dashboard."""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
        "rules": "/rules",
    })
