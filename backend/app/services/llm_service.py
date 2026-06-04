"""
Saransh — LLM Service

Abstraction layer for LLM calls. Supports:
  - Amazon Bedrock Nova Micro (primary, cheapest at $0.035/1M input)
  - Local extractive fallback (no API needed)

All agent nodes call this service — never boto3 directly.
"""

import json
import logging
import re
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)


class LLMService(ABC):
    """Abstract base class for LLM interactions."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Generate text from a prompt. Returns the generated string."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the LLM backend."""
        pass


class BedrockLLMService(LLMService):
    """
    Amazon Bedrock Nova Micro LLM service.
    Uses the invoke_model API with the Converse-style message format.
    """

    def __init__(self, model_id: str, region: str, aws_access_key_id: str, aws_secret_access_key: str):
        import boto3

        self.model_id = model_id
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        logger.info(f"BedrockLLMService initialized with model: {model_id}")

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """Call Bedrock Nova Micro via invoke_model."""
        messages = [{"role": "user", "content": [{"text": prompt}]}]

        request_body = {
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": temperature,
            },
        }

        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )
            result = json.loads(response["body"].read())

            # Nova Micro returns output.message.content[0].text
            output_text = result.get("output", {}).get("message", {}).get("content", [{}])[0].get("text", "")
            return output_text.strip()

        except Exception as e:
            logger.error(f"Bedrock LLM call failed: {e}")
            raise RuntimeError(f"Bedrock LLM call failed: {e}")

    @property
    def name(self) -> str:
        return f"Bedrock ({self.model_id})"


class LocalFallbackLLM(LLMService):
    """
    Local extractive summarization fallback.
    Uses TF-IDF sentence scoring — no API calls, no GPU.
    Works offline for development and testing.
    """

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> str:
        """
        Extractive fallback: scores sentences by word frequency
        and returns the top-N most informative sentences.
        """
        # Extract the document text from the prompt (look for text after common markers)
        text = prompt

        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) <= 3:
            return text.strip()

        # Simple TF scoring
        word_freq: dict[str, int] = {}
        for sentence in sentences:
            words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Score each sentence
        scored = []
        for i, sentence in enumerate(sentences):
            words = re.findall(r'\b[a-zA-Z]{3,}\b', sentence.lower())
            if not words:
                continue
            score = sum(word_freq.get(w, 0) for w in words) / len(words)
            scored.append((score, i, sentence))

        # Take top 30% of sentences, maintain order
        n_keep = max(3, len(scored) // 3)
        scored.sort(key=lambda x: x[0], reverse=True)
        top_indices = sorted([s[1] for s in scored[:n_keep]])
        summary = " ".join(sentences[i] for i in top_indices)

        return summary.strip()

    @property
    def name(self) -> str:
        return "Local Fallback (Extractive TF-IDF)"


def create_llm_service(
    use_bedrock: bool = True,
    model_id: str = "amazon.nova-micro-v1:0",
    region: str = "us-east-1",
    aws_access_key_id: str = "",
    aws_secret_access_key: str = "",
) -> LLMService:
    """
    Factory function to create the appropriate LLM service.
    Tries Bedrock first, falls back to local if unavailable.
    """
    if use_bedrock and aws_access_key_id and aws_secret_access_key:
        try:
            service = BedrockLLMService(model_id, region, aws_access_key_id, aws_secret_access_key)
            logger.info(f"Using Bedrock LLM: {model_id}")
            return service
        except Exception as e:
            logger.warning(f"Failed to initialize Bedrock LLM: {e}. Falling back to local.")

    logger.info("Using local fallback LLM (extractive TF-IDF)")
    return LocalFallbackLLM()
