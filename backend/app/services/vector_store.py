"""FAISS Vector Store wrapper."""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class VectorStore:
    """Lightweight FAISS wrapper for document chunk retrieval."""

    def __init__(self, dimension: int):
        """Initialize an empty FAISS index with the given dimension."""
        import faiss

        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine after normalization)
        self.chunks: list[str] = []
        logger.debug(f"VectorStore created with dimension={dimension}")

    def add_chunks(self, chunks: list[str], embeddings: np.ndarray) -> None:
        """
        Add document chunks and their embeddings to the index.

        Args:
            chunks: List of text chunks.
            embeddings: Numpy array of shape (n_chunks, dimension).
        """
        if len(chunks) != embeddings.shape[0]:
            raise ValueError(f"Mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings")

        # Normalize for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Avoid division by zero
        normalized = (embeddings / norms).astype(np.float32)

        self.index.add(normalized)
        self.chunks.extend(chunks)
        logger.debug(f"Added {len(chunks)} chunks to vector store (total: {len(self.chunks)})")

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[str]:
        """
        Find the top-k most similar chunks to the query.

        Args:
            query_embedding: 1D numpy array of the query embedding.
            top_k: Number of results to return.

        Returns:
            List of the most relevant text chunks.
        """
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty, returning no results")
            return []

        # Normalize query
        query = query_embedding.reshape(1, -1).astype(np.float32)
        norm = np.linalg.norm(query)
        if norm > 0:
            query = query / norm

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query, k)

        results = []
        for idx in indices[0]:
            if 0 <= idx < len(self.chunks):
                results.append(self.chunks[idx])

        logger.debug(f"Retrieved {len(results)} chunks (top_k={top_k})")
        return results

    @property
    def size(self) -> int:
        """Number of indexed chunks."""
        return self.index.ntotal
