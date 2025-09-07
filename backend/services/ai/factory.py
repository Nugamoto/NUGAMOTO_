"""AI service factory for creating service instances."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.services.ai.base import AIService
from backend.services.ai.openai_service import OpenAIService


class AIServiceFactory:
    """Factory for creating AI service instances."""

    @staticmethod
    def create_ai_service(db: Session, provider: str = "openai") -> AIService:
        """Create an AI service instance.

        Args:
            db: Database session.
            provider: AI service provider (default: "openai").

        Returns:
            AI service instance.

        Raises:
            ValueError: If provider is not supported.
        """
        if provider.lower() == "openai":
            return OpenAIService(db)
        # Future providers can be added here:
        # elif provider.lower() == "groq":
        #     return GroqService(db)
        # elif provider.lower() == "gemini":
        #     return GeminiService(db)
        else:
            raise ValueError(f"Unsupported AI provider: {provider}")

    @staticmethod
    def get_default_service(db: Session) -> AIService:
        """Get the default AI service.

        Args:
            db: Database session.

        Returns:
            Default AI service instance.
        """
        default_provider = getattr(settings, 'DEFAULT_AI_PROVIDER', 'openai')
        return AIServiceFactory.create_ai_service(db, default_provider)