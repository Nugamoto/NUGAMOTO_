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
    DATABASE_URL: str = "sqlite:///./nugamoto.db"
    OPENAI_API_KEY: str = "dummy-key"

    class Config:
        env_file = str(PROJECT_ROOT / '.env')
        env_file_encoding = 'utf-8'

settings = Settings()

# Debug output - can be removed later
if settings.OPENAI_API_KEY == "dummy-key":
    print(f"Warning: Using dummy API key. Check that your .env file exists at {PROJECT_ROOT / '.env'}")
