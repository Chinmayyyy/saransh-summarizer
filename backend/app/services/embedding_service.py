"""
Saransh — Embedding Service

Abstraction layer for text embeddings. Supports:
  - Amazon Bedrock Titan Embed Text v2 (primary, $0.02/1M tokens)
  - Local sentence-transformers fallback (all-MiniLM-L6-v2)
"""

import json
import logging
from abc import ABC, abstractmethod

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    """Abstract base class for embedding generation."""

    @abstractmethod
    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Embed a list of texts into vectors.
        Returns numpy array of shape (n_texts, embedding_dim).
        """
        pass

    @abstractmethod
    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text. Returns 1D array."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass


class BedrockEmbeddingService(EmbeddingService):
    """
    Amazon Bedrock Titan Text Embeddings V2.
    1024-dimensional vectors, up to 8192 tokens per input.
    """

    def __init__(self, model_id: str, region: str, aws_access_key_id: str, aws_secret_access_key: str):
        import boto3

        self.model_id = model_id
        
        # Build client arguments; omit static credentials if they are empty to allow boto3 to use IAM roles
        client_kwargs = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = aws_access_key_id
            client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            
        self.client = boto3.client("bedrock-runtime", **client_kwargs)
        self._dimension = 1024
        logger.info(f"BedrockEmbeddingService initialized: {model_id}")

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text using Titan Embed v2."""
        # Truncate to avoid exceeding token limit (~8192 tokens ≈ 32000 chars)
        truncated = text[:30000]

        request_body = {
            "inputText": truncated,
            "dimensions": self._dimension,
        }

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())
            embedding = result.get("embedding", [])
            return np.array(embedding, dtype=np.float32)

        except Exception as e:
            logger.error(f"Bedrock embedding failed: {e}")
            raise RuntimeError(f"Bedrock embedding failed: {e}")

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts (calls Titan one at a time)."""
        embeddings = [self.embed_single(text) for text in texts]
        return np.array(embeddings, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return f"Bedrock ({self.model_id})"


class LocalEmbeddingService(EmbeddingService):
    """
    Local sentence-transformers fallback.
    Uses all-MiniLM-L6-v2 (384-dim, ~80MB download on first use).
    """

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self._dimension = 384
            logger.info("LocalEmbeddingService initialized: all-MiniLM-L6-v2")
        except ImportError:
            logger.error("sentence-transformers not installed. Install with: pip install sentence-transformers")
            raise

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts (batched for efficiency)."""
        embeddings = self.model.encode(texts, convert_to_numpy=True, batch_size=32)
        return embeddings.astype(np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def name(self) -> str:
        return "Local (all-MiniLM-L6-v2)"


def create_embedding_service(
    use_bedrock: bool = True,
    model_id: str = "amazon.titan-embed-text-v2:0",
    region: str = "us-east-1",
    aws_access_key_id: str = "",
    aws_secret_access_key: str = "",
) -> EmbeddingService:
    """Factory: Bedrock first, local fallback if unavailable."""
    import os
    is_aws_env = bool(
        os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
        or os.environ.get("AWS_EXECUTION_ENV")
        or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
    )
    
    if use_bedrock and (is_aws_env or (aws_access_key_id and aws_secret_access_key)):
        try:
            service = BedrockEmbeddingService(model_id, region, aws_access_key_id, aws_secret_access_key)
            logger.info(f"Using Bedrock Embeddings: {model_id}")
            return service
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock Embeddings: {e}. Falling back to local.")

    logger.info("Using local embedding model (all-MiniLM-L6-v2)")
    return LocalEmbeddingService()
