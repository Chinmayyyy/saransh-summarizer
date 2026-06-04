"""
Saransh — Resume Match API Router

POST /api/resume-match — accepts resume upload, runs the resume agent graph.
"""

import time
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from app.middleware.rate_limiter import limiter
from app.models.schemas import ResumeMatchResponse, ResumeProfile, JobMatch, ErrorResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["resume"])

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def _get_extension(filename: str) -> str:
    parts = filename.rsplit(".", 1)
    return f".{parts[-1].lower()}" if len(parts) >= 2 else ""


@router.post(
    "/resume-match",
    response_model=ResumeMatchResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
    summary="Match resume against job postings",
    description="Upload a resume (PDF, DOCX, TXT) and receive AI-powered job matching with scores and career advice.",
)
@limiter.limit(f"{settings.upload_limit_per_minute}/minute")
async def match_resume(request: Request, file: UploadFile = File(...)):
    """
    Runs the multi-agent resume matching pipeline:
    Parser → Profile Extractor → Job Matcher → Career Advisor
    """
    start_time = time.time()

    # --- Validate file type ---
    ext = _get_extension(file.filename or "unknown")
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type for resume: '{ext}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # --- Read and validate ---
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")
    if len(file_bytes) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB",
        )

    logger.info(f"Resume match request: {file.filename} ({len(file_bytes)} bytes)")

    # --- Run the agent graph ---
    try:
        from app.main import get_resume_graph

        graph = get_resume_graph()
        if graph is None:
            raise HTTPException(status_code=503, detail="Resume matching service is not available")

        initial_state = {
            "file_bytes": file_bytes,
            "filename": file.filename or "unknown",
        }

        result = graph.invoke(initial_state)

        if result.get("error"):
            raise HTTPException(status_code=400, detail=result["error"])

        processing_time = int((time.time() - start_time) * 1000)

        # Build profile from result
        profile_data = result.get("profile", {})
        profile = ResumeProfile(
            name=profile_data.get("name"),
            skills=profile_data.get("skills", []),
            tools=profile_data.get("tools", []),
            experience_years=profile_data.get("experience_years"),
            education=profile_data.get("education", []),
            domains=profile_data.get("domains", []),
            projects=profile_data.get("projects", []),
        )

        # Build job matches from result
        explanations = result.get("match_explanations", [])
        top_matches = []
        for exp in explanations:
            top_matches.append(JobMatch(
                role_title=exp.get("role_title", "Unknown"),
                company=exp.get("company", "Unknown"),
                match_score=min(100.0, max(0.0, float(exp.get("match_score", 0)))),
                why_it_matches=exp.get("why_it_matches", ""),
                missing_skills=exp.get("missing_skills", []),
                suggested_next_steps=exp.get("suggested_next_steps", []),
            ))

        return ResumeMatchResponse(
            mode="resume",
            filename=file.filename or "unknown",
            profile=profile,
            top_matches=top_matches,
            processing_time_ms=processing_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resume matching pipeline error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resume matching failed: {str(e)}")
