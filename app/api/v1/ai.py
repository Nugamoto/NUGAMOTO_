"""AI recipe generation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.core.enums import OutputType, OutputFormat, AIOutputTargetType
from app.crud import ai_model_output as crud_ai_output
from app.crud import recipe as crud_recipe
from app.schemas.ai_model_output import AIModelOutputCreate
from app.schemas.ai_service import (
    RecipeWithAIOutput,
    RecipeRequestInput
)

from app.services.ai.factory import AIServiceFactory

router = APIRouter(prefix="/ai", tags=["AI Services"])


@router.post("/recipes", response_model=RecipeWithAIOutput)
async def generate_recipe(
        *,
        db: Annotated[Session, Depends(get_db)],
        user_id: Annotated[int, Body(...)],
        kitchen_id: Annotated[int, Body(...)],
        request: Annotated[RecipeRequestInput, Body(...)],
) -> RecipeWithAIOutput:
    """Generate a recipe using AI based on user input and kitchen context."""
    try:
        # Create AI service
        ai_service = AIServiceFactory.create_ai_service(db)

        # Generate recipe
        recipe_response = await ai_service.generate_recipe(
            request=request.to_generation_request(),
            user_id=user_id,
            kitchen_id=kitchen_id
        )

        recipe_data = recipe_response.to_recipe_create(db)

        # Create recipe in DB
        recipe = crud_recipe.create_recipe(
            db=db,
            recipe_data=recipe_data,
            is_ai_generated=True,
            created_by_user_id=user_id
        )

        # Log AI interaction
        ai_output = crud_ai_output.create_ai_output(
            db=db,
            output_data=AIModelOutputCreate(
                user_id=user_id,
                model_version=ai_service.model,
                output_type=OutputType.RECIPE,
                output_format=OutputFormat.JSON,
                prompt_used=request.user_input,
                raw_output=recipe_response.model_dump_json(),
                target_type=AIOutputTargetType.RECIPE,
                target_id=recipe.id,
                extra_data={"accepted": True}
            )
        )

        return RecipeWithAIOutput(
            recipe=recipe,
            ai_output=ai_output
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recipe generation failed: {str(e)}"
        )
