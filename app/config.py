from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./cache.db"
    transformer_delay: float = 0.5  # секунды, имитация медленного сервиса


settings = Settings()