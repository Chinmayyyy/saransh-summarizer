"""
Saransh — Summarize API Router

POST /api/summarize — accepts file upload, runs the summarize agent graph.
"""

import time
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.middleware.rate_limiter import limiter
from app.models.schemas import SummaryResponse, ErrorResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["summarize"])

# Supported file extensions
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".csv", ".xlsx", ".json"}


def _get_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return f".{parts[-1].lower()}" if len(parts) >= 2 else ""


@router.post(
    "/summarize",
    response_model=SummaryResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}, 429: {"model": ErrorResponse}},
    summary="Summarize a document",
    description="Upload a document (PDF, DOCX, TXT, CSV, XLSX, JSON) and receive an AI-generated summary.",
)
@limiter.limit(f"{settings.upload_limit_per_minute}/minute")
async def summarize_document(request: Request, file: UploadFile = File(...)):
    """
    Runs the multi-agent summarization pipeline:
    Parser → Analyzer → [RAG Retriever] → Summarizer → Quality Checker
    """
    start_time = time.time()

    # --- Validate file type ---
    ext = _get_extension(file.filename or "unknown")
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # --- Read and validate file size ---
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(file_bytes) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    logger.info(f"Summarize request: {file.filename} ({len(file_bytes)} bytes)")

    # --- Run the agent graph ---
    try:
        from app.main import get_summarize_graph

        graph = get_summarize_graph()
        if graph is None:
            raise HTTPException(status_code=503, detail="Summarization service is not available")

        # Execute the agent pipeline
        initial_state = {
            "file_bytes": file_bytes,
            "filename": file.filename or "unknown",
            "retry_count": 0,
        }

        result = graph.invoke(initial_state)

        # Check for pipeline errors
        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        processing_time = int((time.time() - start_time) * 1000)

        return SummaryResponse(
            mode="summarize",
            filename=file.filename or "unknown",
            short_summary=result.get("short_summary", ""),
            detailed_summary=result.get("detailed_summary", ""),
            key_points=result.get("key_points", []),
            keywords=result.get("keywords", []),
            metadata={
                **result.get("metadata", {}),
                "word_count": result.get("word_count", 0),
                "doc_type": result.get("doc_type", "unknown"),
                "used_rag": result.get("used_rag", False),
            },
            processing_time_ms=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")
