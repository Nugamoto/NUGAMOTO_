"""AI recipe generation endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.core.enums import OutputType, OutputFormat, AIOutputTargetType
from backend.crud import ai_model_output as crud_ai_output
from backend.schemas.ai_model_output import AIModelOutputCreate, AIModelOutputUpdate
from backend.schemas.ai_service import (
    RecipeGenerationAPIRequest,
    RecipeWithAIOutput,
    RecipeGenerationResponse
)
from backend.schemas.recipe import RecipeCreate
from backend.services.ai.factory import AIServiceFactory
from backend.services.ai.prompt_builder import PromptBuilder
from backend.services.conversions.unit_conversion_service import UnitConversionService

router = APIRouter(prefix="/ai", tags=["AI Services"])


@router.post("/recipes", response_model=RecipeWithAIOutput)
async def generate_recipe(
        *,
        db: Annotated[Session, Depends(get_db)],
        data: RecipeGenerationAPIRequest,
) -> RecipeWithAIOutput:
    """Generate a recipe using AI based on user input and kitchen context."""
    try:
        ai_service = AIServiceFactory.create_ai_service(db)

        # Build the prompt to capture what was actually sent to the AI
        prompt_builder = PromptBuilder(db)
        system_prompt, user_prompt = prompt_builder.build_recipe_prompt(
            request=data.request,
            user_id=data.user_id,
            kitchen_id=data.kitchen_id
        )

        recipe_response = await ai_service.generate_recipe(
            request=data.request,
            user_id=data.user_id,
            kitchen_id=data.kitchen_id
        )

        model_version = getattr(ai_service, 'model', 'unknown')

        # Create structured prompt data for storage
        prompt_data = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "original_request": data.request.model_dump()
        }

        ai_output = crud_ai_output.create_ai_output(
            db=db,
            output_data=AIModelOutputCreate(
                user_id=data.user_id,
                model_version=model_version,
                output_type=OutputType.RECIPE,
                output_format=OutputFormat.JSON,
                prompt_used=str(prompt_data),
                raw_output=recipe_response.model_dump_json(),
                target_type=AIOutputTargetType.RECIPE,
                target_id=None,
                extra_data={"status": "generated"}
            )
        )

        return RecipeWithAIOutput(
            recipe=recipe_response,
            ai_output=ai_output
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recipe generation failed: {str(e)}"
        )


@router.post("/recipes/{ai_output_id}/convert-to-recipe-create", response_model=RecipeCreate)
async def convert_ai_recipe_to_create(
        *,
        db: Annotated[Session, Depends(get_db)],
        ai_output_id: int,
        user_id: int,
) -> RecipeCreate:
    """Convert AI recipe response to RecipeCreate format for saving."""
    try:
        ai_output = crud_ai_output.get_ai_output_by_id(db, ai_output_id)
        if not ai_output or ai_output.user_id != user_id:
            raise HTTPException(status_code=404, detail="AI output not found")

        recipe_response = RecipeGenerationResponse.model_validate_json(ai_output.raw_output)

        unit_conversion_service = UnitConversionService(db)
        recipe_create = recipe_response.to_recipe_create(
            created_by_user_id=user_id,
            unit_conversion_service=unit_conversion_service
        )

        return recipe_create

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recipe conversion failed: {str(e)}"
        )


@router.patch("/recipes/{ai_output_id}/mark-saved")
async def mark_ai_recipe_as_saved(
        *,
        db: Annotated[Session, Depends(get_db)],
        ai_output_id: int,
        recipe_id: int,
        user_id: int,
) -> dict[str, str]:
    """Mark AI recipe as saved and link to created recipe."""
    try:
        ai_output = crud_ai_output.get_ai_output_by_id(db, ai_output_id)
        if not ai_output or ai_output.user_id != user_id:
            raise HTTPException(status_code=404, detail="AI output not found")

        update_data = AIModelOutputUpdate(
            target_id=recipe_id,
            extra_data={"status": "saved", "recipe_id": recipe_id}
        )

        updated_output = crud_ai_output.update_ai_output(
            db=db,
            output_id=ai_output_id,
            output_data=update_data
        )

        if not updated_output:
            raise HTTPException(status_code=404, detail="Failed to update AI output")

        return {"message": "AI recipe marked as saved"}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to mark recipe as saved: {str(e)}"
        )
