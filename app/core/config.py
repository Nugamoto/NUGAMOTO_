from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./nugamoto.db"
    OPENAI_API_KEY: str = "dummy-key"

    class Config:
        env_file = ".env"

settings = Settings()