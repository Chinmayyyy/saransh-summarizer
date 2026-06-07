"""Summarizer agent node using LLM to generate structured summaries."""

import json
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

SUMMARIZER_SYSTEM_PROMPT = """You are Saransh, an expert AI document summarizer. Your task is to produce clear, accurate, and well-structured summaries.

Rules:
- Be concise but comprehensive
- Preserve all important facts and figures
- Do not hallucinate or add information not in the text
- Use professional, clear language
- Key points should be specific and actionable, not vague

Respond ONLY in valid JSON with this exact structure:
{
  "short_summary": "2-3 sentence concise overview of the entire document",
  "detailed_summary": "1-2 paragraph thorough summary covering all major sections and findings",
  "key_points": ["Specific key point 1", "Specific key point 2", "..."],
  "keywords": ["keyword1", "keyword2", "..."]
}"""


SUMMARIZER_USER_PROMPT = """Analyze and summarize the following document content.

Document type: {doc_type}
Key entities found: {entities}

Document content:
---
{context}
---

Provide a comprehensive summary with short_summary, detailed_summary, key_points (5-8 bullet points), and keywords (5-10 terms). Respond with valid JSON only."""


SUMMARIZER_RETRY_PROMPT = """Your previous summary was reviewed and found lacking. Here is the feedback:

Feedback: {feedback}

Please produce an improved summary of the same document content.

Document content:
---
{context}
---

Respond with valid JSON only with: short_summary, detailed_summary, key_points, keywords."""


def summarizer_node(state: dict, llm: LLMService) -> dict:
    """Generates a structured document summary using the LLM."""
    relevant_chunks = state.get("relevant_chunks", [])
    doc_type = state.get("doc_type", "general")
    entities = state.get("entities", [])
    quality_feedback = state.get("quality_feedback", "")
    retry_count = state.get("retry_count", 0)

    # Combine relevant chunks into context
    context = "\n\n".join(relevant_chunks)

    # Truncate to avoid exceeding token limits (~6000 words ≈ ~8000 tokens)
    if len(context.split()) > 6000:
        words = context.split()[:6000]
        context = " ".join(words)

    logger.info(f"Summarizer Agent: Generating summary (context: {len(context)} chars, retry: {retry_count})")

    try:
        if retry_count > 0 and quality_feedback:
            prompt = SUMMARIZER_RETRY_PROMPT.format(
                feedback=quality_feedback,
                context=context,
            )
        else:
            prompt = SUMMARIZER_USER_PROMPT.format(
                doc_type=doc_type,
                entities=", ".join(entities[:10]) if entities else "none identified",
                context=context,
            )

        response = llm.generate(
            prompt=prompt,
            system_prompt=SUMMARIZER_SYSTEM_PROMPT,
            max_tokens=2048,
            temperature=0.3,
        )

        # Parse JSON response
        clean_response = response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_response

        result = json.loads(clean_response)

        return {
            "short_summary": result.get("short_summary", "Summary could not be generated."),
            "detailed_summary": result.get("detailed_summary", ""),
            "key_points": result.get("key_points", [])[:10],
            "keywords": result.get("keywords", [])[:15],
        }

    except json.JSONDecodeError:
        logger.warning("Summarizer Agent: JSON parse failed, extracting text directly")
        # Fallback: use the raw LLM response as the summary
        return {
            "short_summary": response[:500] if 'response' in dir() else "Summary generation failed.",
            "detailed_summary": response if 'response' in dir() else "",
            "key_points": [],
            "keywords": [],
        }
    except Exception as e:
        logger.error(f"Summarizer Agent error: {e}")
        return {
            "short_summary": f"Summary generation encountered an error: {str(e)}",
            "detailed_summary": "",
            "key_points": [],
            "keywords": [],
        }
