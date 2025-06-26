"""
Configuration management for AI ChatBot
Uses pydantic-settings for environment variable handling
"""

from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from typing import List, Optional, Literal
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings"""

    # AI Configuration
    ai_provider: str = Field("openai", env="AI_PROVIDER")  # openai, gemini, anthropic

    # OpenAI Configuration
    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-3.5-turbo", env="OPENAI_MODEL")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")

    # Google Gemini Configuration
    gemini_api_key: str = Field("", env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-pro", env="GEMINI_MODEL")

    # Anthropic Configuration
    anthropic_api_key: str = Field("", env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field("claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")

    # General AI Settings
    max_tokens: int = Field(1000, env="MAX_TOKENS")
    temperature: float = Field(0.7, env="TEMPERATURE")
    top_p: float = Field(1.0, env="TOP_P")
    frequency_penalty: float = Field(0.0, env="FREQUENCY_PENALTY")
    presence_penalty: float = Field(0.0, env="PRESENCE_PENALTY")

    # Voice Configuration
    whisper_model: str = Field("base", env="WHISPER_MODEL")
    whisper_preload: bool = Field(False, env="WHISPER_PRELOAD")
    audio_format: str = Field("wav", env="AUDIO_FORMAT")
    max_audio_duration: int = Field(60, env="MAX_AUDIO_DURATION")
    audio_sample_rate: int = Field(16000, env="AUDIO_SAMPLE_RATE")
    audio_channels: int = Field(1, env="AUDIO_CHANNELS")
    voice_enabled: bool = Field(True, env="VOICE_ENABLED")
    auto_send_after_transcription: bool = Field(True, env="AUTO_SEND_AFTER_TRANSCRIPTION")
    noise_reduction: bool = Field(True, env="NOISE_REDUCTION")
    silence_threshold: float = Field(2.0, env="SILENCE_THRESHOLD")

    # Memory Configuration
    memory_type: Literal["json", "redis"] = Field("json", env="MEMORY_TYPE")
    memory_path: str = Field("./data/conversations", env="MEMORY_PATH")
    max_history_messages: int = Field(50, env="MAX_HISTORY_MESSAGES")
    auto_save: bool = Field(True, env="AUTO_SAVE")
    compression_enabled: bool = Field(False, env="COMPRESSION_ENABLED")

    # RAG (Retrieval-Augmented Generation) Configuration
    rag_enabled: bool = Field(True, env="RAG_ENABLED")
    rag_top_k: int = Field(3, env="RAG_TOP_K")  # Number of relevant documents to retrieve
    rag_similarity_threshold: float = Field(0.7, env="RAG_SIMILARITY_THRESHOLD")  # Minimum similarity score
    rag_chunk_size: int = Field(500, env="RAG_CHUNK_SIZE")  # Size of text chunks for vectorization
    rag_chunk_overlap: int = Field(50, env="RAG_CHUNK_OVERLAP")  # Overlap between chunks
    rag_collection_name: str = Field("chatbot_memory", env="RAG_COLLECTION_NAME")
    rag_embedding_model: str = Field("sentence-transformers/all-MiniLM-L6-v2", env="RAG_EMBEDDING_MODEL")
    rag_persist_directory: str = Field("./data/vector_db", env="RAG_PERSIST_DIRECTORY")

    # Redis Settings
    redis_url: str = Field("redis://localhost:6379", env="REDIS_URL")
    redis_db: int = Field(0, env="REDIS_DB")
    redis_password: Optional[str] = Field(None, env="REDIS_PASSWORD")
    redis_ttl: int = Field(86400, env="REDIS_TTL")

    # Server Configuration
    host: str = Field("localhost", env="HOST")
    port: int = Field(8000, env="PORT")
    debug: bool = Field(True, env="DEBUG")
    reload: bool = Field(True, env="RELOAD")

    # CORS Settings
    cors_origins: List[str] = Field(
        ["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    cors_credentials: bool = Field(True, env="CORS_CREDENTIALS")
    cors_methods: List[str] = Field(
        ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        env="CORS_METHODS"
    )
    cors_headers: List[str] = Field(["*"], env="CORS_HEADERS")

    # Security
    secret_key: str = Field("change-this-in-production", env="SECRET_KEY")
    algorithm: str = Field("HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_hosts: List[str] = Field(["*"], env="ALLOWED_HOSTS")

    # Rate Limiting
    rate_limit_requests: int = Field(100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(60, env="RATE_LIMIT_WINDOW")

    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_format: Literal["json", "text"] = Field("json", env="LOG_FORMAT")
    log_file_enabled: bool = Field(True, env="LOG_FILE_ENABLED")
    log_file_path: str = Field("./logs/app.log", env="LOG_FILE_PATH")
    log_file_max_size: str = Field("10MB", env="LOG_FILE_MAX_SIZE")
    log_file_backup_count: int = Field(5, env="LOG_FILE_BACKUP_COUNT")

    # Monitoring
    health_check_enabled: bool = Field(True, env="HEALTH_CHECK_ENABLED")
    health_check_interval: int = Field(30, env="HEALTH_CHECK_INTERVAL")
    metrics_enabled: bool = Field(True, env="METRICS_ENABLED")
    metrics_port: int = Field(9090, env="METRICS_PORT")
    performance_monitoring: bool = Field(True, env="PERFORMANCE_MONITORING")
    slow_query_threshold: float = Field(1.0, env="SLOW_QUERY_THRESHOLD")

    # Development
    dev_mode: bool = Field(True, env="DEV_MODE")
    dev_mock_ai: bool = Field(False, env="DEV_MOCK_AI")
    dev_mock_voice: bool = Field(False, env="DEV_MOCK_VOICE")

    # Feature Flags
    feature_voice_output: bool = Field(False, env="FEATURE_VOICE_OUTPUT")
    feature_file_upload: bool = Field(False, env="FEATURE_FILE_UPLOAD")
    feature_multi_language: bool = Field(False, env="FEATURE_MULTI_LANGUAGE")
    feature_custom_models: bool = Field(False, env="FEATURE_CUSTOM_MODELS")
    feature_plugins: bool = Field(False, env="FEATURE_PLUGINS")

    # Beta Features
    beta_streaming_responses: bool = Field(True, env="BETA_STREAMING_RESPONSES")
    beta_conversation_search: bool = Field(False, env="BETA_CONVERSATION_SEARCH")
    beta_export_conversations: bool = Field(True, env="BETA_EXPORT_CONVERSATIONS")

    # Paths
    config_path: str = Field("./config", env="CONFIG_PATH")
    data_path: str = Field("./data", env="DATA_PATH")
    logs_path: str = Field("./logs", env="LOGS_PATH")

    # ChromaDB Settings
    chroma_api_url: Optional[str] = Field(None, env="CHROMA_API_URL")
    chroma_collection_name: str = Field("chatbot_memory", env="CHROMA_COLLECTION_NAME")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("cors_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v

    @field_validator("cors_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @field_validator("whisper_model")
    @classmethod
    def validate_whisper_model(cls, v):
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if v not in valid_models:
            raise ValueError(f"Invalid Whisper model. Must be one of: {valid_models}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v, info):
        if not info.data.get("debug") and v == "change-this-in-production":
            raise ValueError("SECRET_KEY must be changed from default in production environment!")
        return v

    @field_validator("ai_provider")
    @classmethod
    def validate_ai_keys(cls, v, info):
        if v == "openai" and not info.data.get("openai_api_key"):
            raise ValueError("OPENAI_API_KEY must be set when AI_PROVIDER is 'openai'")
        if v == "gemini" and not info.data.get("gemini_api_key"):
            raise ValueError("GEMINI_API_KEY must be set when AI_PROVIDER is 'gemini'")
        if v == "anthropic" and not info.data.get("anthropic_api_key"):
            raise ValueError("ANTHROPIC_API_KEY must be set when AI_PROVIDER is 'anthropic'")
        return v

    @field_validator("allowed_hosts")
    @classmethod
    def validate_allowed_hosts_production(cls, v, info):
        if not info.data.get("debug") and v == ["*"]:
            raise ValueError("allowed_hosts cannot be ['*'] in production environment. Please specify allowed hosts.")
        return v

    @field_validator("cors_headers")
    @classmethod
    def validate_cors_headers_production(cls, v, info):
        if not info.data.get("debug") and v == ["*"]:
            raise ValueError("cors_headers cannot be ['*'] in production environment. Please specify allowed headers.")
        return v

    @property
    def redis_connection_kwargs(self) -> dict:
        """Get Redis connection parameters"""
        kwargs = {
            "url": self.redis_url,
            "db": self.redis_db,
            "decode_responses": True
        }
        if self.redis_password:
            kwargs["password"] = self.redis_password
        return kwargs

    @property
    def openai_client_kwargs(self) -> dict:
        """Get OpenAI client parameters"""
        return {
            "api_key": self.openai_api_key,
            "base_url": self.openai_base_url
        }

    def create_directories(self):
        """Create necessary directories"""
        directories = [
            self.memory_path,
            self.logs_path,
            self.data_path,
            os.path.dirname(self.log_file_path),
            os.path.dirname(self.config_path) # Ensure config directory exists
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def save_to_file(self, file_path: str):
        """Save current settings to a JSON file, excluding sensitive data."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Exclude sensitive fields and properties that are not meant for direct saving
        # Use model_dump to get a dictionary representation
        settings_dict = self.model_dump(
            exclude={
                'openai_api_key', 'gemini_api_key', 'anthropic_api_key', 'secret_key', 'redis_password',
                'redis_connection_kwargs', 'openai_client_kwargs'
            }
        )
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, indent=2, ensure_ascii=False)
        logger.info(f"Settings saved to {file_path}")

    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['Settings']:
        """Load settings from a JSON file."""
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"Settings file not found: {file_path}")
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                settings_data = json.load(f)
            # Create a new Settings instance from the loaded data
            # This will re-apply validators and default values for missing fields
            loaded_settings = cls(**settings_data)
            logger.info(f"Settings loaded from {file_path}")
            return loaded_settings
        except Exception as e:
            logger.error(f"Failed to load settings from {file_path}: {e}")
            return None

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    settings = Settings()
    settings.create_directories()
    return settings
