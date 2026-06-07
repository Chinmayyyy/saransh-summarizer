"""Analyzer agent node using LLM to extract document metadata."""

import json
import logging
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

ANALYZER_SYSTEM_PROMPT = """You are a document analysis expert. Your job is to quickly analyze a document and identify:
1. The document type (report, article, data_table, letter, technical, resume, general)
2. Key named entities (people, organizations, locations, dates, products)
3. Any metadata you can extract (title, author, date, subject)

Respond ONLY in valid JSON with this exact structure:
{
  "doc_type": "report",
  "entities": ["Entity1", "Entity2"],
  "metadata": {"title": "...", "subject": "..."}
}"""


ANALYZER_USER_PROMPT = """Analyze the following document text and extract the document type, key entities, and metadata.

Document text (first 3000 characters):
---
{text}
---

Respond with valid JSON only."""


def analyzer_node(state: dict, llm: LLMService) -> dict:
    """Identifies document type, entities, and metadata."""
    raw_text = state.get("raw_text", "")

    if not raw_text:
        return {
            "doc_type": "general",
            "entities": [],
            "metadata": {},
        }

    # Send first 3000 chars to avoid token waste on analysis
    text_preview = raw_text[:3000]

    logger.info(f"Analyzer Agent: Analyzing document ({len(raw_text)} chars)")

    try:
        prompt = ANALYZER_USER_PROMPT.format(text=text_preview)
        response = llm.generate(
            prompt=prompt,
            system_prompt=ANALYZER_SYSTEM_PROMPT,
            max_tokens=512,
            temperature=0.1,
        )

        # Parse JSON from response (handle markdown code blocks)
        clean_response = response.strip()
        if clean_response.startswith("```"):
            # Remove markdown code fences
            lines = clean_response.split("\n")
            clean_response = "\n".join(lines[1:-1]) if len(lines) > 2 else clean_response

        result = json.loads(clean_response)

        doc_type = result.get("doc_type", "general")
        entities = result.get("entities", [])[:20]  # Cap at 20 entities
        metadata = result.get("metadata", {})

        logger.info(f"Analyzer Agent: doc_type={doc_type}, entities={len(entities)}")

        return {
            "doc_type": doc_type,
            "entities": entities,
            "metadata": metadata,
        }

    except json.JSONDecodeError:
        logger.warning("Analyzer Agent: Failed to parse LLM JSON response, using defaults")
        return {
            "doc_type": "general",
            "entities": [],
            "metadata": {},
        }
    except Exception as e:
        logger.error(f"Analyzer Agent error: {e}")
        return {
            "doc_type": "general",
            "entities": [],
            "metadata": {},
        }
