from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Core
    ENVIRONMENT: str = "dev"
    SECRET_KEY: str = ""
    ENCRYPTION_KEY: str = ""
    JWT_PRIVATE_KEY_PATH: str = "/keys/jwt_private.pem"
    JWT_PUBLIC_KEY_PATH: str = "/keys/jwt_public.pem"

    # Database and cache
    DB_USER: str = "odin"
    DB_PASSWORD: str = "odin_dev_password"
    DB_NAME: str = "odin"
    DATABASE_URL: str = "postgresql+asyncpg://odin:odin_dev_password@database-node:5432/odin"
    REDIS_URL: str = "redis://redis-broker:6379/0"

    # Workspace
    WORKSPACE_ROOT: str = "/data/ODIN"

    # LLM providers
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    ANTHROPIC_API_KEY: str = ""
    HERMES_MODEL_ANTHROPIC: str = "claude-opus-4-8"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    RERANK_ENABLED: bool = False

    # WhatsApp
    WHATSAPP_APP_SECRET: str = ""
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_ALLOWED_NUMBER: str = ""
    WHATSAPP_ALERT_TEMPLATE: str = ""
    WA_DRY_RUN: bool = True

    # SMTP
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""

    # Integrations
    CLOUDFLARE_API_TOKEN: str = ""
    HETZNER_API_TOKEN: str = ""
    GITHUB_TOKEN: str = ""

    # Backups
    BACKUP_LOCAL_DIR: str = "/backups"
    BACKUP_OFFSITE_REMOTE: str = ""
    BACKUP_RETENTION_DAYS: int = 30

    # Watcher
    WATCHER_FORCE_POLLING: bool = True

    # Voice
    TTS_ENABLED: bool = True
    TTS_VOICE: str = "onyx"
    TTS_MODEL: str = "tts-1-hd"

    # CORS
    CORS_ALLOWED_ORIGIN: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
