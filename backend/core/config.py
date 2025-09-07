"""Application configuration loaded from environment and .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None


def find_project_root() -> Path:
    """Return the nearest ancestor directory that contains a .env file.

    Starts at the directory of this file and walks up to the filesystem root.
    Falls back to two levels above this file if no .env is found.
    """
    current_dir = Path(__file__).parent
    while current_dir != current_dir.parent:
        if (current_dir / ".env").exists():
            return current_dir
        current_dir = current_dir.parent
    # Default: repository root (adjust if your layout differs)
    return Path(__file__).parent.parent.parent


# Resolve project root and (optionally) pre-load .env to populate os.environ
PROJECT_ROOT: Path = find_project_root()
if load_dotenv is not None:
    # Only attempt to load if python-dotenv is available
    load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from environment and .env."""

    # Application
    EXPIRING_ITEMS_THRESHOLD_DAYS: int = 3

    # Database
    DATABASE_URL: str = "sqlite:///./nugamoto.sqlite"

    # API keys (example)
    OPENAI_API_KEY: str = "dummy-key"

    # JWT
    SECRET_KEY: str = "CHANGE_ME_TO_A_SECURE_RANDOM_VALUE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Admin whitelist (comma-separated)
    ADMIN_EMAILS: str = ""
    ADMIN_EMAIL_DOMAINS: str = ""

    class Config:
        # pydantic-settings will also read the .env directly for its own values.
        # We still load dotenv above so that code using os.getenv(...) also sees them.
        env_file = str(PROJECT_ROOT / ".env")
        env_file_encoding = "utf-8"


# Singleton settings instance
settings = Settings()