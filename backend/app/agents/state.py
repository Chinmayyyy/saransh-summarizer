"""LangGraph state schemas for agent graphs."""

from typing import TypedDict, Optional, Any


class SummarizeState(TypedDict, total=False):
    """Shared state for the Summarize mode agent graph."""
    file_bytes: bytes
    filename: str

    raw_text: str
    file_type: str
    word_count: int

    doc_type: str
    entities: list[str]
    metadata: dict

    chunks: list[str]
    relevant_chunks: list[str]
    used_rag: bool

    short_summary: str
    detailed_summary: str
    key_points: list[str]
    keywords: list[str]

    quality_pass: bool
    quality_feedback: str
    retry_count: int

    error: Optional[str]


class ResumeState(TypedDict, total=False):
    """Shared state for the Resume mode agent graph."""
    file_bytes: bytes
    filename: str

    raw_text: str

    profile: dict

    job_postings: list[dict]
    match_scores: list[dict]
    top_matches: list[dict]

    match_explanations: list[dict]

    error: Optional[str]
