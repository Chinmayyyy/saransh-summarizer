"""FastAPI Application Entry Point for Saransh."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.routers import summarize, resume

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

_summarize_graph = None
_resume_graph = None


def get_summarize_graph():
    return _summarize_graph


def get_resume_graph():
    return _resume_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _summarize_graph, _resume_graph

    logger.info("Saransh starting up...")

    from app.services.llm_service import create_llm_service
    llm = create_llm_service(
        use_bedrock=settings.use_bedrock,
        model_id=settings.bedrock_llm_model_id,
        region=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    from app.services.embedding_service import create_embedding_service
    embedding_service = create_embedding_service(
        use_bedrock=settings.use_bedrock,
        model_id=settings.bedrock_embedding_model_id,
        region=settings.aws_default_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    from app.agents.summarize_graph import build_summarize_graph
    from app.agents.resume_graph import build_resume_graph

    _summarize_graph = build_summarize_graph(llm, embedding_service)
    _resume_graph = build_resume_graph(llm, embedding_service)

    logger.info("Agent graphs compiled successfully.")
    yield

    logger.info("Saransh shutting down...")
    _summarize_graph = None
    _resume_graph = None


# --- Create FastAPI app ---
app = FastAPI(
    title="Saransh",
    description="AI-Powered Document Intelligence — Multi-agent document summarizer with Resume Mode",
    version="1.0.0",
    lifespan=lifespan,
)

# --- CORS middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# --- Routers ---
app.include_router(summarize.router)
app.include_router(resume.router)


# --- Health check ---
@app.get("/api/health", tags=["health"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def health_check(request: Request):
    return {
        "status": "healthy",
        "service": "Saransh",
        "version": "1.0.0",
        "llm_backend": "bedrock" if settings.bedrock_available else "local_fallback",
    }


# --- Global exception handler ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again.",
        },
    )


# --- AWS Lambda Handler ---
from mangum import Mangum
handler = Mangum(app)
