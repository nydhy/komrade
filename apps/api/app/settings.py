from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KOMRADE API"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    web_origin: str = "http://localhost:3000"
    database_url: str = "postgresql+psycopg2://komrade:komrade@localhost:5432/komrade"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
