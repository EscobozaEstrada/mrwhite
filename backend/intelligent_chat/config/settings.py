"""
Configuration Settings for Intelligent Chat System
"""
import os
from typing import Literal
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = {"extra": "ignore"}  # Allow extra fields from .env to be ignored
    
    # Environment
    ENVIRONMENT: Literal["development", "production"] = os.getenv("ENVIRONMENT", "development")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    
    # AWS Configuration
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # S3 Configuration
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "")
    S3_INTELLIGENT_CHAT_PREFIX: str = "intelligent-chat"
    
    # Bedrock Configuration
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "us.anthropic.claude-3-5-haiku-20241022-v1:0")
    BEDROCK_EMBEDDING_MODEL_ID: str = "amazon.titan-embed-text-v2:0"
    BEDROCK_MAX_TOKENS: int = 4096
    BEDROCK_TEMPERATURE: float = 0.7
    
    # Pinecone Configuration
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "")
    PINECONE_INDEX_NAME: str = "dog-project"  # Shared index with fastapi_chat, separate namespaces
    
    # Pinecone Namespaces
    @property
    def PINECONE_NAMESPACE_DOCUMENTS(self) -> str:
        return f"intelligent-chat-documents-{self.ENVIRONMENT}"
    
    @property
    def PINECONE_NAMESPACE_VET_REPORTS(self) -> str:
        return f"intelligent-chat-vet-reports-{self.ENVIRONMENT}"
    
    @property
    def PINECONE_NAMESPACE_CONVERSATIONS(self) -> str:
        return f"intelligent-chat-conversations-{self.ENVIRONMENT}"
    
    @property
    def PINECONE_NAMESPACE_BOOK_COMMENTS(self) -> str:
        return f"intelligent-chat-book-comments-{self.ENVIRONMENT}"
    
    # Embedding Configuration
    EMBEDDING_DIMENSION: int = 1024  # For Titan embeddings
    EMBEDDING_MAX_TOKENS: int = 8192
    
    # Chunking Configuration
    CHUNK_SIZE: int = 1000  # tokens
    CHUNK_OVERLAP: int = 200  # tokens
    VET_REPORT_CHUNK_SIZE: int = 800  # smaller for medical precision
    VET_REPORT_CHUNK_OVERLAP: int = 150
    
    # Retrieval Configuration
    DEFAULT_TOP_K: int = 10
    HEALTH_MODE_TOP_K: int = 15
    WAYOFDOG_MODE_TOP_K: int = 8
    RERANK_TOP_N: int = 5
    HEALTH_MODE_RERANK_TOP_N: int = 7  # More chunks for medical queries
    
    # Credit System
    CREDITS_PER_MESSAGE: float = 0.01
    CREDITS_PER_1K_TOKENS: float = 0.002
    CREDITS_PER_DOCUMENT: float = 0.05
    CREDITS_PER_IMAGE_ANALYSIS: float = 0.03
    CREDITS_PER_VOICE_MINUTE: float = 0.10
    
    # Rate Limiting
    MAX_MESSAGES_PER_MINUTE: int = 30
    MAX_DOCUMENTS_PER_MESSAGE: int = 5
    MAX_DOCUMENT_SIZE_MB: int = 25
    
    # File Upload Configuration
    ALLOWED_DOCUMENT_TYPES: list = ["pdf", "docx", "txt", "doc"]
    ALLOWED_IMAGE_TYPES: list = ["jpg", "jpeg", "png", "gif", "webp"]
    MAX_FILE_SIZE: int = 25 * 1024 * 1024  # 25 MB
    
    # Voice Configuration
    VOICE_MAX_DURATION_SECONDS: int = 120  # 2 minutes
    VOICE_TRANSCRIPTION_MODEL: str = "whisper-1"  # or AWS Transcribe
    
    # Streaming Configuration
    ENABLE_STREAMING: bool = True
    STREAM_CHUNK_SIZE: int = 50  # characters
    
    # Conversation Configuration
    MAX_CONTEXT_MESSAGES: int = 20  # Last N messages for context
    CONVERSATION_TIMEOUT_HOURS: int = 24
    
    # Search Configuration
    SEARCH_RESULTS_LIMIT: int = 50
    DATE_GROUP_LABELS: dict = {
        0: "Today",
        1: "Yesterday",
        # Older dates will show day name or date
    }
    
    # Pawtree Integration
    PAWTREE_BASE_URL: str = "https://pawtree.com/doglove/products/search"
    ENABLE_PAWTREE_LINKS: bool = True
    
    # Prompt Configuration
    SYSTEM_PROMPT_MAX_LENGTH: int = 2000
    USER_MESSAGE_MAX_LENGTH: int = 10000
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Global settings instance
settings = Settings()

