"""Job matcher node using cosine similarity on candidate and job embeddings."""

import json
import logging
import os
from pathlib import Path

import numpy as np

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

TOP_N_MATCHES = 5  # Return top 5 job matches


def _load_job_postings() -> list[dict]:
    """Load job postings from the bundled dataset."""
    # job_matcher.py is in app/agents/nodes/
    # __file__.parent = nodes
    # __file__.parent.parent = agents
    # __file__.parent.parent.parent = app
    
    base_path = Path(__file__).resolve().parent.parent.parent
    jobs_path = base_path / "data" / "jobs.json"
    
    if jobs_path.exists():
        with open(jobs_path, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        logger.info(f"Loaded {len(jobs)} job postings from {jobs_path}")
        return jobs
    
    logger.error(f"jobs.json not found at expected path: {jobs_path}")
    return []


def _profile_to_text(profile: dict) -> str:
    """Convert structured profile to a searchable text representation."""
    parts = []
    if profile.get("name"):
        parts.append(f"Candidate: {profile['name']}")
    if profile.get("skills"):
        parts.append(f"Skills: {', '.join(profile['skills'])}")
    if profile.get("tools"):
        parts.append(f"Tools: {', '.join(profile['tools'])}")
    if profile.get("domains"):
        parts.append(f"Domains: {', '.join(profile['domains'])}")
    if profile.get("experience_years") is not None:
        parts.append(f"Experience: {profile['experience_years']} years")
    if profile.get("education"):
        parts.append(f"Education: {', '.join(profile['education'])}")
    if profile.get("projects"):
        parts.append(f"Projects: {', '.join(profile['projects'][:5])}")
    return ". ".join(parts)


def _job_to_text(job: dict) -> str:
    """Convert job posting to a searchable text representation."""
    parts = [
        f"Role: {job.get('title', '')}",
        f"Company: {job.get('company', '')}",
        f"Description: {job.get('description', '')}",
    ]
    if job.get("required_skills"):
        parts.append(f"Required Skills: {', '.join(job['required_skills'])}")
    if job.get("preferred_skills"):
        parts.append(f"Preferred Skills: {', '.join(job['preferred_skills'])}")
    if job.get("domain"):
        parts.append(f"Domain: {job['domain']}")
    return ". ".join(parts)


def job_matcher_node(state: dict, embedding_service: EmbeddingService) -> dict:
    """Matches candidate profile against job postings using embeddings."""
    profile = state.get("profile", {})

    # Load job postings
    job_postings = _load_job_postings()
    if not job_postings:
        return {
            "job_postings": [],
            "match_scores": [],
            "top_matches": [],
            "error": "No job postings available for matching",
        }

    logger.info(f"Job Matcher Agent: Matching against {len(job_postings)} jobs")

    try:
        # Convert profile and jobs to text
        profile_text = _profile_to_text(profile)
        job_texts = [_job_to_text(job) for job in job_postings]

        # Embed everything
        profile_embedding = embedding_service.embed_single(profile_text)
        job_embeddings = embedding_service.embed(job_texts)

        # Normalize for cosine similarity
        profile_norm = profile_embedding / (np.linalg.norm(profile_embedding) + 1e-10)
        job_norms = job_embeddings / (np.linalg.norm(job_embeddings, axis=1, keepdims=True) + 1e-10)

        # Compute cosine similarities
        similarities = np.dot(job_norms, profile_norm)

        # Build scored list
        match_scores = []
        for i, score in enumerate(similarities):
            match_scores.append({
                "job_index": i,
                "score": float(score) * 100,  # Convert to 0-100 scale
                "job_title": job_postings[i].get("title", "Unknown"),
                "company": job_postings[i].get("company", "Unknown"),
            })

        # Sort by score descending
        match_scores.sort(key=lambda x: x["score"], reverse=True)

        # Take top N
        top_matches = []
        for match in match_scores[:TOP_N_MATCHES]:
            idx = match["job_index"]
            top_matches.append({
                **job_postings[idx],
                "match_score": round(match["score"], 1),
            })

        logger.info(f"Job Matcher: Top match: {match_scores[0]['job_title']} ({match_scores[0]['score']:.1f}%)")

        return {
            "job_postings": job_postings,
            "match_scores": match_scores[:TOP_N_MATCHES],
            "top_matches": top_matches,
        }

    except Exception as e:
        logger.error(f"Job Matcher error: {e}")
        return {
            "job_postings": job_postings,
            "match_scores": [],
            "top_matches": [],
            "error": f"Job matching failed: {str(e)}",
        }
