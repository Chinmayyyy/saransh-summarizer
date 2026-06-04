"""
Saransh — Pydantic Request/Response Models

All API schemas for summarization and resume matching responses.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ============================================
# Summarize Mode Schemas
# ============================================

class SummaryResponse(BaseModel):
    """Response from the summarization agent pipeline."""
    mode: str = "summarize"
    filename: str
    short_summary: str = Field(description="2-3 sentence overview")
    detailed_summary: str = Field(description="1-2 paragraph detailed summary")
    key_points: list[str] = Field(description="Bullet-point key takeaways")
    keywords: list[str] = Field(description="Extracted keywords/entities")
    metadata: dict = Field(default_factory=dict, description="Document metadata")
    processing_time_ms: int = Field(description="Total processing time in milliseconds")


# ============================================
# Resume Mode Schemas
# ============================================

class ResumeProfile(BaseModel):
    """Extracted resume profile from the Profile Extractor agent."""
    name: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    experience_years: Optional[float] = None
    education: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class JobMatch(BaseModel):
    """A single job match result from the Career Advisor agent."""
    role_title: str
    company: str
    match_score: float = Field(ge=0, le=100, description="Match score 0-100")
    why_it_matches: str = Field(description="Human-readable explanation of the match")
    missing_skills: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)


class ResumeMatchResponse(BaseModel):
    """Response from the resume matching agent pipeline."""
    mode: str = "resume"
    filename: str
    profile: ResumeProfile
    top_matches: list[JobMatch] = Field(default_factory=list)
    processing_time_ms: int = Field(description="Total processing time in milliseconds")


# ============================================
# Error Schema
# ============================================

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: str
    status_code: int = 500
