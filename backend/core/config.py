from pathlib import Path

from pydantic_settings import BaseSettings


# Find the project root directory (where the .env file should be)
# Start with the current directory and go up until we find a .env file or reach the root
def find_project_root():
    current_dir = Path(__file__).parent
    while current_dir != current_dir.parent:  # Stop at filesystem root
        if (current_dir / '.env').exists():
            return current_dir
        current_dir = current_dir.parent
    return Path(__file__).parent.parent.parent  # Default to 2 levels up from config.py


# Set the project root as the working directory for loading .env
PROJECT_ROOT = find_project_root()


class Settings(BaseSettings):
    # Application settings
    EXPIRING_ITEMS_THRESHOLD_DAYS: int = 3

    # Database settings
    DATABASE_URL: str = "sqlite:///./nugamoto.sqlite"

    # API keys
    OPENAI_API_KEY: str = "dummy-key"

    # JWT settings
    SECRET_KEY: str = "CHANGE_ME_TO_A_SECURE_RANDOM_VALUE"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Admin settings
    ADMIN_EMAILS: str = ""
    ADMIN_EMAIL_DOMAINS: str = ""

    class Config:
        env_file = str(PROJECT_ROOT / '.env')
        env_file_encoding = 'utf-8'

settings = Settings()
