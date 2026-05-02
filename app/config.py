from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    anthropic_api_key: str
    openai_api_key: str = ""
    openai_model_fast: str = "gpt-5-mini"
    openai_model_smart: str = "gpt-5"
    anthropic_model_fast: str = "claude-haiku-4-5-20251001"
    anthropic_model_smart: str = "claude-sonnet-4-6"
    database_url: str = "postgresql://agora_user:agora_pass@db:5432/agora"
    default_tick_duration_days: int = 15
    default_agent_concurrent_calls: int = 10
    max_concurrent_calls: int = 20
    max_concurrent_simulations: int = 3
    debug: bool = False
    admin_master_key: str = "change-me-in-production"
    encryption_key: str = ""  # Fernet-Key für API-Key-Verschlüsselung; Fallback: admin_master_key
    cors_origins: list[str] = ["*"]  # In Produktion auf eigene Domain einschränken

    class Config:
        env_file = ".env"


settings = Settings()
