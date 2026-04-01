from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    api_port: int = 8080
    ollama_base_url: str = "http://ollama:11434"
    redis_url: str = "redis://:cc_redis_pass_123@redis:6379/0"
    cors_origins: str = "*"
    n8n_base_url: str = "http://n8n:5678"
    n8n_api_key: str = ""

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
