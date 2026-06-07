"""Application configuration settings."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from .env file or environment variables."""

    aws_access_key_id: str = Field(default="", description="AWS Access Key ID")
    aws_secret_access_key: str = Field(default="", description="AWS Secret Access Key")
    aws_default_region: str = Field(default="us-east-1", description="AWS Region")

    bedrock_llm_model_id: str = Field(
        default="amazon.nova-micro-v1:0",
        description="Bedrock LLM model ID"
    )
    bedrock_embedding_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0",
        description="Bedrock embedding model ID"
    )

    use_bedrock: bool = Field(
        default=True,
        description="Use Bedrock for LLM/embeddings."
    )
    max_file_size_mb: int = Field(default=10, description="Max file upload size in MB")
    rate_limit_per_minute: int = Field(default=10, description="Max API requests per minute")
    upload_limit_per_minute: int = Field(default=3, description="Max file uploads per minute")

    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Comma-separated CORS origins"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def bedrock_available(self) -> bool:
        is_aws_env = bool(
            os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or os.environ.get("AWS_EXECUTION_ENV")
            or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
        )
        return bool(
            self.use_bedrock
            and (is_aws_env or (self.aws_access_key_id and self.aws_secret_access_key))
        )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Singleton settings instance
settings = Settings()
