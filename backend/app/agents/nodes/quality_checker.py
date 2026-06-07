"""Quality checker node using LLM to validate summary quality."""

import json
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

QC_SYSTEM_PROMPT = """You are a quality assurance expert for document summaries. Your job is to evaluate whether a summary is good enough to present to the user.

Check for:
1. Coverage: Does the summary capture the main topics?
2. Accuracy: Are the key points factual (based on the source)?
3. Completeness: Are there important aspects missing?
4. Clarity: Is the summary clear and well-written?

Respond ONLY in valid JSON:
{
  "pass": true/false,
  "feedback": "Brief explanation of issues if any"
}"""


QC_USER_PROMPT = """Evaluate this summary against the source document.

Source document (first 2000 chars):
---
{source_preview}
---

Generated summary:
---
Short: {short_summary}
Key points: {key_points}
---

Does this summary adequately cover the source material? Respond with JSON: {{"pass": true/false, "feedback": "..."}}"""


def quality_checker_node(state: dict, llm: LLMService) -> dict:
    """Evaluates summary quality against the source preview."""
    raw_text = state.get("raw_text", "")
    short_summary = state.get("short_summary", "")
    key_points = state.get("key_points", [])
    retry_count = state.get("retry_count", 0)

    # Skip quality check if already retried once
    if retry_count >= 1:
        logger.info("Quality Checker: Max retries reached, auto-passing")
        return {
            "quality_pass": True,
            "quality_feedback": "",
            "retry_count": retry_count,
        }

    # Skip if summary is empty (already an error state)
    if not short_summary or short_summary.startswith("Summary generation"):
        return {
            "quality_pass": True,
            "quality_feedback": "Skipped: no summary to check",
            "retry_count": retry_count,
        }

    logger.info("Quality Checker Agent: Evaluating summary quality")

    try:
        source_preview = raw_text[:2000]
        prompt = QC_USER_PROMPT.format(
            source_preview=source_preview,
            short_summary=short_summary,
            key_points=", ".join(key_points[:5]),
        )

        response = llm.generate(
            prompt=prompt,
            system_prompt=QC_SYSTEM_PROMPT,
            max_tokens=256,
            temperature=0.1,
        )

        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_response

        result = json.loads(clean_response)

        passed = result.get("pass", True)
        feedback = result.get("feedback", "")

        logger.info(f"Quality Checker: {'PASS' if passed else 'FAIL'} — {feedback}")

        return {
            "quality_pass": passed,
            "quality_feedback": feedback,
            "retry_count": retry_count + (0 if passed else 1),
        }

    except Exception as e:
        logger.warning(f"Quality Checker error: {e}. Auto-passing.")
        return {
            "quality_pass": True,
            "quality_feedback": f"Quality check skipped due to error: {str(e)}",
            "retry_count": retry_count,
        }
