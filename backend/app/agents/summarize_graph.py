"""LangGraph orchestrator for the summarization pipeline."""

import logging
from functools import partial

from langgraph.graph import StateGraph, END

from app.agents.state import SummarizeState
from app.agents.nodes.parser import parser_node
from app.agents.nodes.analyzer import analyzer_node
from app.agents.nodes.rag_retriever import rag_retriever_node
from app.agents.nodes.summarizer import summarizer_node
from app.agents.nodes.quality_checker import quality_checker_node
from app.services.llm_service import LLMService
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

# Threshold: documents with fewer words skip RAG
SHORT_DOC_THRESHOLD = 2000


def _check_parser_error(state: dict) -> str:
    if state.get("error"):
        return "error_exit"
    return "analyze"


def _route_after_analysis(state: dict) -> str:
    word_count = state.get("word_count", 0)
    if word_count >= SHORT_DOC_THRESHOLD:
        logger.info(f"Supervisor: Long doc ({word_count} words) → RAG path")
        return "rag_retrieve"
    else:
        logger.info(f"Supervisor: Short doc ({word_count} words) → direct summarize")
        return "direct_summarize"


def _route_after_quality(state: dict) -> str:
    if state.get("quality_pass", True):
        return "finish"
    else:
        logger.info("Supervisor: Quality check failed → retry summarization")
        return "retry_summarize"


def _error_exit_node(state: dict) -> dict:
    return {}


def build_summarize_graph(llm: LLMService, embedding_service: EmbeddingService) -> StateGraph:
    analyzer_with_llm = partial(analyzer_node, llm=llm)
    rag_with_embeddings = partial(rag_retriever_node, embedding_service=embedding_service)
    summarizer_with_llm = partial(summarizer_node, llm=llm)
    quality_with_llm = partial(quality_checker_node, llm=llm)

    graph = StateGraph(SummarizeState)

    graph.add_node("parser", parser_node)
    graph.add_node("analyzer", analyzer_with_llm)
    graph.add_node("rag_retriever", rag_with_embeddings)
    graph.add_node("summarizer", summarizer_with_llm)
    graph.add_node("quality_checker", quality_with_llm)
    graph.add_node("error_exit", _error_exit_node)

    graph.set_entry_point("parser")

    # Edges
    graph.add_conditional_edges(
        "parser",
        _check_parser_error,
        {
            "error_exit": "error_exit",
            "analyze": "analyzer",
        }
    )

    graph.add_conditional_edges(
        "analyzer",
        _route_after_analysis,
        {
            "rag_retrieve": "rag_retriever",
            "direct_summarize": "summarizer",
        }
    )

    graph.add_edge("rag_retriever", "summarizer")

    graph.add_edge("summarizer", "quality_checker")

    graph.add_conditional_edges(
        "quality_checker",
        _route_after_quality,
        {
            "finish": END,
            "retry_summarize": "summarizer",
        }
    )

    graph.add_edge("error_exit", END)

    # Compile
    compiled = graph.compile()
    logger.info("Summarize agent graph compiled successfully")
    return compiled
