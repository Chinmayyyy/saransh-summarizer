"""LangGraph orchestrator for the resume matching pipeline."""

import logging
from functools import partial

from langgraph.graph import StateGraph, END

from app.agents.state import ResumeState
from app.agents.nodes.parser import parser_node  # Reuse the same parser
from app.agents.nodes.profile_extractor import profile_extractor_node
from app.agents.nodes.job_matcher import job_matcher_node
from app.agents.nodes.career_advisor import career_advisor_node
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def _check_parser_error(state: dict) -> str:
    if state.get("error"):
        return "error_exit"
    return "extract_profile"


def _check_profile_error(state: dict) -> str:
    profile = state.get("profile", {})
    skills = profile.get("skills", [])
    if not skills:
        logger.warning("Profile has no skills — matching may be inaccurate")
    return "match_jobs"


def _error_exit_node(state: dict) -> dict:
    return {}


def build_resume_graph(llm: LLMService, embedding_service: EmbeddingService) -> StateGraph:
    profile_with_llm = partial(profile_extractor_node, llm=llm)
    matcher_with_embeddings = partial(job_matcher_node, embedding_service=embedding_service)
    advisor_with_llm = partial(career_advisor_node, llm=llm)

    # Build graph
    graph = StateGraph(ResumeState)

    # Add nodes
    graph.add_node("parser", parser_node)
    graph.add_node("profile_extractor", profile_with_llm)
    graph.add_node("job_matcher", matcher_with_embeddings)
    graph.add_node("career_advisor", advisor_with_llm)
    graph.add_node("error_exit", _error_exit_node)

    # Entry point
    graph.set_entry_point("parser")

    # Edges
    graph.add_conditional_edges(
        "parser",
        _check_parser_error,
        {
            "error_exit": "error_exit",
            "extract_profile": "profile_extractor",
        }
    )

    graph.add_conditional_edges(
        "profile_extractor",
        _check_profile_error,
        {
            "match_jobs": "job_matcher",
        }
    )

    graph.add_edge("job_matcher", "career_advisor")
    graph.add_edge("career_advisor", END)
    graph.add_edge("error_exit", END)

    # Compile
    compiled = graph.compile()
    logger.info("Resume agent graph compiled successfully")
    return compiled
