"""
Saransh — Agent State Schemas

TypedDict state definitions for LangGraph agent graphs.
These are the shared "blackboard" that all agents read/write to.
"""

from typing import TypedDict, Optional, Any


class SummarizeState(TypedDict, total=False):
    """Shared state for the Summarize mode agent graph."""

    # --- Input (set by API router) ---
    file_bytes: bytes
    filename: str

    # --- Parser Agent output ---
    raw_text: str
    file_type: str
    word_count: int

    # --- Analyzer Agent output ---
    doc_type: str           # "report", "article", "data_table", "letter", "technical", "general"
    entities: list[str]     # Key named entities found
    metadata: dict          # Title, author, date, etc. if extractable

    # --- RAG Retriever output ---
    chunks: list[str]
    relevant_chunks: list[str]
    used_rag: bool          # Whether RAG was used (long docs) or skipped (short docs)

    # --- Summarizer Agent output ---
    short_summary: str
    detailed_summary: str
    key_points: list[str]
    keywords: list[str]

    # --- Quality Checker output ---
    quality_pass: bool
    quality_feedback: str
    retry_count: int

    # --- Control ---
    error: Optional[str]


class ResumeState(TypedDict, total=False):
    """Shared state for the Resume mode agent graph."""

    # --- Input ---
    file_bytes: bytes
    filename: str

    # --- Resume Parser output ---
    raw_text: str

    # --- Profile Extractor output ---
    profile: dict       # name, skills, tools, experience_years, education, domains, projects

    # --- Job Matcher output ---
    job_postings: list[dict]
    match_scores: list[dict]    # [{job_index, score, job_title, company}, ...]
    top_matches: list[dict]     # Top N matches with full job data

    # --- Career Advisor output ---
    match_explanations: list[dict]  # [{role_title, company, match_score, why_it_matches, missing_skills, suggested_next_steps}]

    # --- Control ---
    error: Optional[str]
