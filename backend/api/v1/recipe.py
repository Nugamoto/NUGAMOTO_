"""Recipe API endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.core.dependencies import get_db
from backend.core.enums import DifficultyLevel
from backend.crud import recipe as crud_recipe
from backend.crud.recipe import InsufficientIngredientsError, cook_recipe
from backend.schemas.recipe import (
    RecipeCreate, RecipeRead, RecipeUpdate, RecipeWithDetails,
    RecipeIngredientCreate, RecipeIngredientRead, RecipeIngredientUpdate,
    RecipeStepCreate, RecipeStepRead, RecipeStepUpdate,
    RecipeNutritionCreate, RecipeNutritionRead, RecipeNutritionUpdate,
    RecipeReviewUpsert, RecipeReviewRead, RecipeReviewUpdate,
    RecipeSearchParams, RecipeSummary, RecipeRatingSummary, RecipeCookResponse
)

# ================================================================== #
# Sub-routers for better organization                               #
# ================================================================== #

recipe_router = APIRouter(tags=["Recipes"])
ingredients_router = APIRouter(prefix="/{recipe_id}/ingredients", tags=["Recipe Ingredients"])
steps_router = APIRouter(prefix="/{recipe_id}/steps", tags=["Recipe Steps"])
nutrition_router = APIRouter(prefix="/{recipe_id}/nutrition", tags=["Recipe Nutrition"])
reviews_router = APIRouter(prefix="/{recipe_id}/reviews", tags=["Recipe Reviews"])


# ================================================================== #
# Recipe CRUD Endpoints                                         #
# ================================================================== #


@recipe_router.post(
    "/",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recipe"
)
def create_recipe(
        recipe_data: RecipeCreate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeRead:
    """Create a new recipe with ingredients, steps, and optional nutrition.

    Args:
        recipe_data: Recipe creation data with ingredients, steps, and optional nutrition.
        db: Database session dependency.

    Returns:
        The created recipe with all properties.

    Raises:
        HTTPException: 400 if validation fails or required entities don't exist.
    """
    try:
        return crud_recipe.create_recipe(db=db, recipe_data=recipe_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@recipe_router.get(
    "/",
    response_model=list[RecipeRead],
    summary="Get all recipes with optional filtering"
)
def get_all_recipes(
        db: Annotated[Session, Depends(get_db)],
        title_contains: Annotated[str | None, Query(description="Filter by title containing text")] = None,
        is_ai_generated: Annotated[bool | None, Query(description="Filter by AI generated flag")] = None,
        created_by_user_id: Annotated[int | None, Query(description="Filter by creator user ID")] = None,
        difficulty: Annotated[DifficultyLevel | None, Query(description="Filter by difficulty")] = None,
        has_nutrition: Annotated[bool | None, Query(description="Filter by nutrition availability")] = None,
        max_kcal: Annotated[int | None, Query(description="Filter by max calories")] = None,
        min_protein_g: Annotated[float | None, Query(description="Filter by min protein (g)")] = None,
        tags_contains: Annotated[list[str] | None, Query(description="Filter by tags containing")] = None,
        skip: int = 0,
        limit: int = 100
) -> list[RecipeRead]:
    """Get all recipes with pagination and optional filtering.

    Args:
        db: Database session dependency.
        title_contains: Filter by title containing text.
        is_ai_generated: Filter by AI generated flag.
        created_by_user_id: Filter by creator user ID.
        difficulty: Filter by difficulty level (enum: easy, medium, hard).
        has_nutrition: Filter by nutrition availability.
        max_kcal: Filter by maximum calories.
        min_protein_g: Filter by minimum protein (g).
        tags_contains: Filter by tags containing specified values.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        List of recipes matching the criteria.
    """
    # Build search parameters
    search_params = None
    if any([title_contains, is_ai_generated is not None, created_by_user_id, difficulty,
            has_nutrition is not None, max_kcal, min_protein_g, tags_contains]):
        search_params = RecipeSearchParams(
            title_contains=title_contains,
            is_ai_generated=is_ai_generated,
            created_by_user_id=created_by_user_id,
            difficulty=difficulty,
            has_nutrition=has_nutrition,
            max_kcal=max_kcal,
            min_protein_g=min_protein_g,
            tags_contains=tags_contains
        )

    return crud_recipe.get_all_recipes(
        db=db,
        search_params=search_params,
        skip=skip,
        limit=limit
    )


@recipe_router.get(
    "/summary",
    response_model=RecipeSummary,
    summary="Get recipe statistics summary"
)
def get_recipe_summary(
        db: Annotated[Session, Depends(get_db)]
) -> RecipeSummary:
    """Get recipe statistics summary.

    Args:
        db: Database session dependency.

    Returns:
        Recipe statistics summary.
    """
    return crud_recipe.get_recipe_summary(db=db)


@recipe_router.get(
    "/suggestions/by-ingredients",
    response_model=list[RecipeRead],
    summary="Get recipe suggestions by available ingredients"
)
def get_recipe_suggestions_by_ingredients(
        food_item_ids: Annotated[list[int], Query(description="List of available food item IDs")],
        db: Annotated[Session, Depends(get_db)],
        min_match_percentage: Annotated[
            float, Query(description="Minimum match percentage (0.0-1.0)", ge=0.0, le=1.0)] = 0.7
) -> list[RecipeRead]:
    """Get recipe suggestions based on available ingredients.

    Args:
        food_item_ids: List of available food item IDs.
        min_match_percentage: Minimum match percentage (0.0-1.0).
        db: Database session dependency.

    Returns:
        List of recipe suggestions ordered by match percentage.
    """
    if not food_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one food item ID is required"
        )

    return crud_recipe.get_recipes_by_available_ingredients(
        db=db,
        food_item_ids=food_item_ids,
        min_match_percentage=min_match_percentage
    )


@recipe_router.get(
    "/ai-generated",
    response_model=list[RecipeRead],
    summary="Get AI-generated recipes"
)
def get_ai_generated_recipes(
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[RecipeRead]:
    """Get all AI-generated recipes.

    Args:
        db: Database session dependency.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        List of AI-generated recipes.
    """
    return crud_recipe.get_ai_generated_recipes(db=db, skip=skip, limit=limit)


@recipe_router.get(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Get a recipe by ID"
)
def get_recipe(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeRead:
    """Get a recipe by ID.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        The recipe with basic information.

    Raises:
        HTTPException: 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    recipe = crud_recipe.get_recipe_by_id(db=db, recipe_id=recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    return recipe


@recipe_router.get(
    "/{recipe_id}/details",
    response_model=RecipeWithDetails,
    summary="Get a recipe with full details"
)
def get_recipe_details(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeWithDetails:
    """Get a recipe with full details including ingredients, steps, and nutrition.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        The recipe with all details.

    Raises:
        HTTPException: 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    recipe = crud_recipe.get_recipe_with_details(db=db, recipe_id=recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    return recipe


@recipe_router.patch(
    "/{recipe_id}",
    response_model=RecipeRead,
    summary="Update an existing recipe"
)
def update_recipe(
        recipe_id: int,
        recipe_data: RecipeUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeRead:
    """Update an existing recipe.

    Args:
        recipe_id: Recipe ID.
        recipe_data: Recipe update data.
        db: Database session dependency.

    Returns:
        The updated recipe.

    Raises:
        HTTPException: 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    updated_recipe = crud_recipe.update_recipe(
        db=db,
        recipe_id=recipe_id,
        recipe_data=recipe_data
    )

    if not updated_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    return updated_recipe


@recipe_router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe"
)
def delete_recipe(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        Empty response.

    Raises:
        HTTPException: 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    try:
        crud_recipe.delete_recipe(db=db, recipe_id=recipe_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# new Endpoint

@recipe_router.post("/{recipe_id}/cook", response_model=RecipeCookResponse)
async def cook_recipe_endpoint(
        recipe_id: int,
        kitchen_id: int,
        db: Session = Depends(get_db)
) -> RecipeCookResponse:
    """Cook a recipe by deducting ingredients from kitchen inventory.

    Args:
        recipe_id: ID of the recipe to cook
        kitchen_id: ID of the kitchen to use ingredients from (query parameter)
        db: Database session dependency

    Returns:
        Result of cooking operation with success status and details

    Raises:
        HTTPException:
            - 404 if recipe not found
            - 422 if insufficient ingredients available
            - 400 for other validation errors
    """
    try:
        result = cook_recipe(db, recipe_id, kitchen_id)
        return RecipeCookResponse(**result)
    except InsufficientIngredientsError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(e),
                "insufficient_ingredients": e.insufficient_ingredients
            }
        )
    except ValueError as e:
        if "Recipe not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ================================================================== #
# Recipe Ingredient Endpoints                                        #
# ================================================================== #

@ingredients_router.post(
    "",
    response_model=RecipeIngredientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an ingredient to a recipe"
)
def add_recipe_ingredient(
        recipe_id: int,
        ingredient_data: RecipeIngredientCreate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeIngredientRead:
    """Add an ingredient to a recipe.

    Args:
        recipe_id: Recipe ID.
        ingredient_data: Ingredient creation data.
        db: Database session dependency.

    Returns:
        The created ingredient.

    Raises:
        HTTPException: 400 if validation fails, 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    try:
        return crud_recipe.add_recipe_ingredient(
            db=db,
            recipe_id=recipe_id,
            ingredient_data=ingredient_data
        )
    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )


@ingredients_router.get(
    "",
    response_model=list[RecipeIngredientRead],
    summary="Get all ingredients for a recipe"
)
def get_recipe_ingredients(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> list[RecipeIngredientRead]:
    """Get all ingredients for a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        List of recipe ingredients.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    return crud_recipe.get_ingredients_for_recipe(db=db, recipe_id=recipe_id)


@ingredients_router.patch(
    "/{food_item_id}",
    response_model=RecipeIngredientRead,
    summary="Update a recipe ingredient"
)
def update_recipe_ingredient(
        recipe_id: int,
        food_item_id: int,
        ingredient_data: RecipeIngredientUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeIngredientRead:
    """Update a recipe ingredient.

    Args:
        recipe_id: Recipe ID.
        food_item_id: Food item ID.
        ingredient_data: Ingredient update data.
        db: Database session dependency.

    Returns:
        The updated ingredient.

    Raises:
        HTTPException: 404 if ingredient not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if food_item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Food item ID must be a positive integer"
        )

    updated_ingredient = crud_recipe.update_recipe_ingredient(
        db=db,
        recipe_id=recipe_id,
        food_item_id=food_item_id,
        ingredient_data=ingredient_data
    )

    if not updated_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ingredient with food item ID {food_item_id} not found in recipe {recipe_id}"
        )

    return updated_ingredient


@ingredients_router.delete(
    "/{food_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe ingredient"
)
def delete_recipe_ingredient(
        recipe_id: int,
        food_item_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Remove an ingredient from a recipe.

    Args:
        recipe_id: Recipe ID.
        food_item_id: Food item ID.
        db: Database session dependency.

    Returns:
        Empty response.

    Raises:
        HTTPException: 404 if ingredient not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if food_item_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Food item ID must be a positive integer"
        )

    try:
        crud_recipe.delete_recipe_ingredient(
            db=db,
            recipe_id=recipe_id,
            food_item_id=food_item_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ================================================================== #
# Recipe Step Endpoints                                              #
# ================================================================== #

@steps_router.post(
    "",
    response_model=RecipeStepRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a step to a recipe"
)
def add_recipe_step(
        recipe_id: int,
        step_data: RecipeStepCreate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeStepRead:
    """Add a step to a recipe.

    Args:
        recipe_id: Recipe ID.
        step_data: Step creation data.
        db: Database session dependency.

    Returns:
        The created step.

    Raises:
        HTTPException: 400 if validation fails, 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    try:
        return crud_recipe.add_recipe_step(
            db=db,
            recipe_id=recipe_id,
            step_data=step_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@steps_router.get(
    "",
    response_model=list[RecipeStepRead],
    summary="Get all steps for a recipe"
)
def get_recipe_steps(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[RecipeStepRead]:
    """Get all steps for a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        List of recipe steps ordered by step number.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    return crud_recipe.get_steps_for_recipe(
        db=db,
        recipe_id=recipe_id,
        skip=skip,
        limit=limit
    )


@steps_router.patch(
    "/{step_id}",
    response_model=RecipeStepRead,
    summary="Update a recipe step"
)
def update_recipe_step(
        recipe_id: int,
        step_id: int,
        step_data: RecipeStepUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeStepRead:
    """Update a recipe step.

    Args:
        recipe_id: Recipe ID.
        step_id: Step ID.
        step_data: Step update data.
        db: Database session dependency.

    Returns:
        The updated step.

    Raises:
        HTTPException: 404 if step not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if step_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step ID must be a positive integer"
        )

    updated_step = crud_recipe.update_recipe_step(
        db=db,
        recipe_id=recipe_id,
        step_id=step_id,
        step_data=step_data
    )

    if not updated_step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step with ID {step_id} not found in recipe {recipe_id}"
        )

    return updated_step


@steps_router.delete(
    "/{step_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe step"
)
def delete_recipe_step(
        recipe_id: int,
        step_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a recipe step.

    Args:
        recipe_id: Recipe ID.
        step_id: Step ID.
        db: Database session dependency.

    Returns:
        Empty response.

    Raises:
        HTTPException: 404 if step not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if step_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Step ID must be a positive integer"
        )

    try:
        crud_recipe.delete_recipe_step(
            db=db,
            recipe_id=recipe_id,
            step_id=step_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ================================================================== #
# Recipe Nutrition Endpoints                                         #
# ================================================================== #

@nutrition_router.post(
    "",
    response_model=RecipeNutritionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update recipe nutrition"
)
def create_recipe_nutrition(
        recipe_id: int,
        nutrition_data: RecipeNutritionCreate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeNutritionRead:
    """Create or update nutrition information for a recipe.

    Args:
        recipe_id: Recipe ID.
        nutrition_data: Nutrition creation data.
        db: Database session dependency.

    Returns:
        The created or updated nutrition information.

    Raises:
        HTTPException: 404 if recipe not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    try:
        return crud_recipe.create_or_update_recipe_nutrition(
            db=db,
            recipe_id=recipe_id,
            nutrition_data=nutrition_data
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@nutrition_router.patch(
    "",
    response_model=RecipeNutritionRead,
    summary="Update recipe nutrition"
)
def update_recipe_nutrition(
        recipe_id: int,
        nutrition_data: RecipeNutritionUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeNutritionRead:
    """Update nutrition information for a recipe.

    Args:
        recipe_id: Recipe ID.
        nutrition_data: Nutrition update data.
        db: Database session dependency.

    Returns:
        The updated nutrition information.

    Raises:
        HTTPException: 404 if nutrition not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    updated_nutrition = crud_recipe.update_recipe_nutrition(
        db=db,
        recipe_id=recipe_id,
        nutrition_data=nutrition_data
    )

    if not updated_nutrition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Nutrition information for recipe {recipe_id} not found"
        )

    return updated_nutrition


@nutrition_router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recipe nutrition"
)
def delete_recipe_nutrition(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete nutrition information for a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        Empty response.

    Raises:
        HTTPException: 404 if nutrition not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    try:
        crud_recipe.delete_recipe_nutrition(db=db, recipe_id=recipe_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ================================================================== #
# Recipe Review Endpoints                                            #
# ================================================================== #

@reviews_router.post(
    "",
    response_model=RecipeReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a recipe review"
)
def create_recipe_review(
        recipe_id: int,
        user_id: Annotated[int, Query(description="User ID of the reviewer")],
        review_data: RecipeReviewUpsert,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeReviewRead:
    """Create or update a recipe review.

    Args:
        recipe_id: Recipe ID.
        user_id: User ID of the reviewer.
        review_data: Review data.
        db: Database session dependency.

    Returns:
        The created or updated review.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    return crud_recipe.create_or_update_recipe_review(
        db=db,
        user_id=user_id,
        recipe_id=recipe_id,
        review_data=review_data
    )


@reviews_router.get(
    "",
    response_model=list[RecipeReviewRead],
    summary="Get all reviews for a recipe"
)
def get_recipe_reviews(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)],
        skip: int = 0,
        limit: int = 100
) -> list[RecipeReviewRead]:
    """Get all reviews for a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        List of recipe reviews.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    return crud_recipe.get_recipe_reviews(
        db=db,
        recipe_id=recipe_id,
        skip=skip,
        limit=limit
    )


@reviews_router.get(
    "/rating-summary",
    response_model=RecipeRatingSummary,
    summary="Get rating summary for a recipe"
)
def get_recipe_rating_summary(
        recipe_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeRatingSummary:
    """Get rating summary for a recipe.

    Args:
        recipe_id: Recipe ID.
        db: Database session dependency.

    Returns:
        Rating summary with average rating and distribution.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    return crud_recipe.get_recipe_rating_summary(db=db, recipe_id=recipe_id)


@reviews_router.patch(
    "/{user_id}",
    response_model=RecipeReviewRead,
    summary="Update a recipe review"
)
def update_recipe_review(
        recipe_id: int,
        user_id: int,
        review_data: RecipeReviewUpdate,
        db: Annotated[Session, Depends(get_db)]
) -> RecipeReviewRead:
    """Update a recipe review.

    Args:
        recipe_id: Recipe ID.
        user_id: User ID of the reviewer.
        review_data: Review update data.
        db: Database session dependency.

    Returns:
        The updated review.

    Raises:
        HTTPException: 404 if review not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    updated_review = crud_recipe.update_recipe_review(
        db=db,
        user_id=user_id,
        recipe_id=recipe_id,
        review_data=review_data
    )

    if not updated_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review for recipe {recipe_id} by user {user_id} not found"
        )

    return updated_review


@reviews_router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe review"
)
def delete_recipe_review(
        recipe_id: int,
        user_id: int,
        db: Annotated[Session, Depends(get_db)]
) -> Response:
    """Delete a recipe review.

    Args:
        recipe_id: Recipe ID.
        user_id: User ID of the reviewer.
        db: Database session dependency.

    Returns:
        Empty response.

    Raises:
        HTTPException: 404 if review not found.
    """
    if recipe_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recipe ID must be a positive integer"
        )

    if user_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID must be a positive integer"
        )

    try:
        crud_recipe.delete_recipe_review(
            db=db,
            user_id=user_id,
            recipe_id=recipe_id
        )
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


# ================================================================== #
# Main Router Assembly                                               #
# ================================================================== #

router = APIRouter(prefix="/recipes")

# Include all sub-routers
router.include_router(recipe_router)
router.include_router(ingredients_router)
router.include_router(steps_router)
router.include_router(nutrition_router)
router.include_router(reviews_router)
