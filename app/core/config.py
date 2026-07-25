from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    env: str = "development"
    log_level: str = "INFO"
    http_timeout_seconds: float = 5.0
    max_concurrent_fetches: int = 20
    max_url_length: int = 2048
    max_body_size_bytes: int = 10240
    max_redirects: int = 3
    cache_ttl_seconds: float = 300.0
    rate_limit_requests: int = 10

    rate_limit_window_seconds: float = 60.0

    class Config:
        env_file = ".env"


settings = Settings()
