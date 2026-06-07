"""RAG retrieval agent node using FAISS and local/Bedrock embeddings."""

import logging
import re

from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Chunking parameters
CHUNK_SIZE = 800       # Target words per chunk
CHUNK_OVERLAP = 100    # Overlap words between chunks
TOP_K_CHUNKS = 5       # Number of chunks to retrieve


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks based on sentences.
    Preserves sentence boundaries to maintain readability.
    """
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return [text] if text.strip() else []

    chunks = []
    current_chunk: list[str] = []
    current_word_count = 0

    for sentence in sentences:
        sentence_words = len(sentence.split())

        if current_word_count + sentence_words > chunk_size and current_chunk:
            # Save current chunk
            chunk_text = " ".join(current_chunk)
            if chunk_text.strip():
                chunks.append(chunk_text.strip())

            # Calculate overlap: keep last N words worth of sentences
            overlap_words = 0
            overlap_start = len(current_chunk)
            for i in range(len(current_chunk) - 1, -1, -1):
                overlap_words += len(current_chunk[i].split())
                if overlap_words >= overlap:
                    overlap_start = i
                    break

            current_chunk = current_chunk[overlap_start:]
            current_word_count = sum(len(s.split()) for s in current_chunk)

        current_chunk.append(sentence)
        current_word_count += sentence_words

    # Don't forget the last chunk
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        if chunk_text.strip():
            chunks.append(chunk_text.strip())

    return chunks


def rag_retriever_node(state: dict, embedding_service: EmbeddingService) -> dict:
    """Retrieves relevant chunks of text using vector embeddings and FAISS."""
    raw_text = state.get("raw_text", "")
    word_count = state.get("word_count", 0)

    # Short document threshold: skip RAG if < 2000 words
    if word_count < 2000:
        logger.info(f"RAG Retriever: Document is short ({word_count} words), skipping RAG")
        return {
            "chunks": [],
            "relevant_chunks": [raw_text],  # Use full text as single "chunk"
            "used_rag": False,
        }

    logger.info(f"RAG Retriever: Chunking long document ({word_count} words)")

    # 1. Chunk the text
    chunks = _chunk_text(raw_text)
    logger.info(f"RAG Retriever: Created {len(chunks)} chunks")

    if not chunks:
        return {
            "chunks": [],
            "relevant_chunks": [raw_text[:5000]],
            "used_rag": False,
        }

    try:
        # 2. Embed all chunks
        chunk_embeddings = embedding_service.embed(chunks)

        # 3. Build FAISS index
        store = VectorStore(dimension=embedding_service.dimension)
        store.add_chunks(chunks, chunk_embeddings)

        # 4. Create a query from the first chunk (represents the document's topic)
        # Use a "summarize this document" style query
        query_text = f"Main topics and key information: {chunks[0][:500]}"
        query_embedding = embedding_service.embed_single(query_text)

        # 5. Retrieve top-k relevant chunks
        relevant = store.search(query_embedding, top_k=TOP_K_CHUNKS)

        logger.info(f"RAG Retriever: Retrieved {len(relevant)} relevant chunks")

        return {
            "chunks": chunks,
            "relevant_chunks": relevant,
            "used_rag": True,
        }

    except Exception as e:
        logger.error(f"RAG Retriever error: {e}. Falling back to first chunks.")
        # Fallback: just use first few chunks
        fallback_chunks = chunks[:TOP_K_CHUNKS]
        return {
            "chunks": chunks,
            "relevant_chunks": fallback_chunks,
            "used_rag": False,
        }
