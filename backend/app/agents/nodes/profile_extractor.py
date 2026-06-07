"""Profile extractor agent node using LLM to parse resumes."""

import json
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

PROFILE_SYSTEM_PROMPT = """You are an expert resume parser. Extract structured information from the resume text provided.

Be thorough — capture ALL skills, tools, and technologies mentioned.
For experience_years, estimate from dates mentioned (e.g., "2020-2024" = 4 years). If the person is a student/fresher with no work experience, set to 0.

Respond ONLY in valid JSON with this exact structure:
{
  "name": "Full Name or null if not found",
  "skills": ["Python", "Machine Learning", "..."],
  "tools": ["Docker", "AWS", "Git", "..."],
  "experience_years": 2.0,
  "education": ["B.Tech Computer Science, XYZ University, 2024"],
  "domains": ["Machine Learning", "Web Development", "..."],
  "projects": ["Project Name: brief description", "..."]
}"""

PROFILE_USER_PROMPT = """Parse the following resume and extract the candidate's profile information.

Resume text:
---
{resume_text}
---

Extract: name, skills, tools, experience_years, education, domains, projects. Respond with valid JSON only."""


def profile_extractor_node(state: dict, llm: LLMService) -> dict:
    """Extracts candidate profile information from resume text using the LLM."""
    raw_text = state.get("raw_text", "")

    if not raw_text:
        return {
            "profile": {
                "name": None, "skills": [], "tools": [],
                "experience_years": None, "education": [],
                "domains": [], "projects": [],
            },
            "error": "No resume text to parse",
        }

    # Use full resume text (resumes are typically short)
    resume_text = raw_text[:8000]

    logger.info(f"Profile Extractor Agent: Parsing resume ({len(resume_text)} chars)")

    try:
        prompt = PROFILE_USER_PROMPT.format(resume_text=resume_text)
        response = llm.generate(
            prompt=prompt,
            system_prompt=PROFILE_SYSTEM_PROMPT,
            max_tokens=1024,
            temperature=0.1,
        )

        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_response

        profile = json.loads(clean_response)

        # Ensure all fields exist with defaults
        profile.setdefault("name", None)
        profile.setdefault("skills", [])
        profile.setdefault("tools", [])
        profile.setdefault("experience_years", None)
        profile.setdefault("education", [])
        profile.setdefault("domains", [])
        profile.setdefault("projects", [])

        logger.info(f"Profile Extractor: Found {len(profile['skills'])} skills, {len(profile['tools'])} tools")

        return {"profile": profile}

    except json.JSONDecodeError:
        logger.warning("Profile Extractor: JSON parse failed, using basic extraction")
        return {
            "profile": {
                "name": None, "skills": [], "tools": [],
                "experience_years": None, "education": [],
                "domains": [], "projects": [],
            },
        }
    except Exception as e:
        logger.error(f"Profile Extractor error: {e}")
        return {
            "profile": {
                "name": None, "skills": [], "tools": [],
                "experience_years": None, "education": [],
                "domains": [], "projects": [],
            },
            "error": f"Profile extraction failed: {str(e)}",
        }
