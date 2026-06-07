"""Career advisor node using LLM to generate match explanations and next steps."""

import json
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ADVISOR_SYSTEM_PROMPT = """You are a career advisor AI. For each job match, provide:
1. A clear explanation of why this role fits the candidate
2. Skills the candidate is missing for this role
3. Specific, actionable next steps to improve their profile

Be honest, constructive, and specific. Reference actual skills from their profile.

Respond ONLY in valid JSON as a list:
[
  {
    "role_title": "Job Title",
    "company": "Company Name",
    "match_score": 85.0,
    "why_it_matches": "Clear explanation referencing specific skills...",
    "missing_skills": ["Skill1", "Skill2"],
    "suggested_next_steps": ["Take X course", "Build Y project", "Learn Z tool"]
  }
]"""

ADVISOR_USER_PROMPT = """Analyze these job matches for the candidate and provide detailed explanations.

Candidate Profile:
- Name: {name}
- Skills: {skills}
- Tools: {tools}
- Experience: {experience} years
- Domains: {domains}

Top Job Matches:
{job_matches}

For each job, explain why it matches, what skills are missing, and what the candidate should do next. Respond with a JSON array."""


def career_advisor_node(state: dict, llm: LLMService) -> dict:
    """Generates career advisor next steps and feedback on job matches using LLM."""
    profile = state.get("profile", {})
    top_matches = state.get("top_matches", [])

    if not top_matches:
        return {"match_explanations": []}

    logger.info(f"Career Advisor Agent: Analyzing {len(top_matches)} matches")

    # Format job matches for the prompt
    job_matches_text = ""
    for i, match in enumerate(top_matches, 1):
        job_matches_text += f"\n{i}. {match.get('title', 'Unknown')} at {match.get('company', 'Unknown')}"
        job_matches_text += f"\n   Match Score: {match.get('match_score', 0)}%"
        job_matches_text += f"\n   Required Skills: {', '.join(match.get('required_skills', []))}"
        job_matches_text += f"\n   Preferred Skills: {', '.join(match.get('preferred_skills', []))}"
        job_matches_text += f"\n   Description: {match.get('description', '')[:200]}"
        job_matches_text += "\n"

    try:
        prompt = ADVISOR_USER_PROMPT.format(
            name=profile.get("name", "Unknown"),
            skills=", ".join(profile.get("skills", [])),
            tools=", ".join(profile.get("tools", [])),
            experience=profile.get("experience_years", "Unknown"),
            domains=", ".join(profile.get("domains", [])),
            job_matches=job_matches_text,
        )

        response = llm.generate(
            prompt=prompt,
            system_prompt=ADVISOR_SYSTEM_PROMPT,
            max_tokens=2048,
            temperature=0.3,
        )

        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_response

        explanations = json.loads(clean_response)

        if not isinstance(explanations, list):
            explanations = [explanations]

        # Ensure all fields exist
        for exp in explanations:
            exp.setdefault("role_title", "Unknown")
            exp.setdefault("company", "Unknown")
            exp.setdefault("match_score", 0)
            exp.setdefault("why_it_matches", "")
            exp.setdefault("missing_skills", [])
            exp.setdefault("suggested_next_steps", [])

        logger.info(f"Career Advisor: Generated {len(explanations)} match explanations")

        return {"match_explanations": explanations}

    except json.JSONDecodeError:
        logger.warning("Career Advisor: JSON parse failed, creating basic explanations")
        # Fallback: create basic explanations from match data
        basic = []
        for match in top_matches:
            basic.append({
                "role_title": match.get("title", "Unknown"),
                "company": match.get("company", "Unknown"),
                "match_score": match.get("match_score", 0),
                "why_it_matches": f"Your skills align with the requirements for {match.get('title', 'this role')}.",
                "missing_skills": match.get("required_skills", [])[:3],
                "suggested_next_steps": ["Review the job description", "Strengthen relevant skills"],
            })
        return {"match_explanations": basic}

    except Exception as e:
        logger.error(f"Career Advisor error: {e}")
        return {"match_explanations": [], "error": f"Career advice generation failed: {str(e)}"}
