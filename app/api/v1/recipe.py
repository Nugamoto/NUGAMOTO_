"""FastAPI router exposing the recipe endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.crud import recipe as crud_recipe
from app.schemas.recipe import (
    RecipeCreate, RecipeRead, RecipeUpdate, RecipeWithDetails,
    RecipeIngredientCreate, RecipeIngredientRead, RecipeIngredientUpdate,
    RecipeSearchParams, RecipeSummary,
    RecipeNutritionCreate, RecipeNutritionRead, RecipeNutritionUpdate,
    RecipeReviewUpsert, RecipeReviewRead, RecipeReviewUpdate,
    RecipeRatingSummary
)

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.post(
    "/",
    response_model=RecipeRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recipe",
)
def create_recipe(
        recipe_data: RecipeCreate,
        db: Session = Depends(get_db),
) -> RecipeRead:
    """Create a new recipe with ingredients and steps."""
    try:
        db_recipe = crud_recipe.create_recipe(db, recipe_data)
        return RecipeRead.model_validate(db_recipe, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/",
    response_model=list[RecipeRead],
    status_code=status.HTTP_200_OK,
    summary="Get all recipes with filtering",
)
def get_all_recipes(
        title_contains: str | None = Query(None, description="Filter by title containing text"),
        is_ai_generated: bool | None = Query(None, description="Filter by AI generation status"),
        created_by_user_id: int | None = Query(None, gt=0, description="Filter by creator"),
        has_nutrition: bool | None = Query(None, description="Filter by nutrition availability"),
        max_kcal: float | None = Query(None, gt=0, description="Maximum calories"),
        min_protein_g: float | None = Query(None, ge=0, description="Minimum protein"),
        skip: int = Query(0, ge=0, description="Number of recipes to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of recipes to return"),
        db: Session = Depends(get_db),
) -> list[RecipeRead]:
    """Get all recipes with optional filtering and pagination."""
    search_params = RecipeSearchParams(
        title_contains=title_contains,
        is_ai_generated=is_ai_generated,
        created_by_user_id=created_by_user_id,
        has_nutrition=has_nutrition,
        max_kcal=max_kcal,
        min_protein_g=min_protein_g
    )

    recipes = crud_recipe.get_all_recipes(db, search_params, skip, limit)
    return [RecipeRead.model_validate(recipe, from_attributes=True) for recipe in recipes]


@router.get(
    "/summary",
    response_model=RecipeSummary,
    status_code=status.HTTP_200_OK,
    summary="Get recipe statistics",
)
def get_recipe_summary(
        db: Session = Depends(get_db),
) -> RecipeSummary:
    """Get summary statistics for all recipes."""
    return crud_recipe.get_recipe_summary(db)


@router.get(
    "/{recipe_id}",
    response_model=RecipeWithDetails,
    status_code=status.HTTP_200_OK,
    summary="Get a recipe with all details",
)
def get_recipe(
        recipe_id: int,
        db: Session = Depends(get_db),
) -> RecipeWithDetails:
    """Get a specific recipe with all ingredients, steps, and nutrition."""
    recipe = crud_recipe.get_recipe_with_details(db, recipe_id)
    if recipe is None:
        raise HTTPException(404, f"Recipe with ID {recipe_id} not found")
    return RecipeWithDetails.model_validate(recipe, from_attributes=True)


@router.patch(
    "/{recipe_id}",
    response_model=RecipeRead,
    status_code=status.HTTP_200_OK,
    summary="Update a recipe",
)
def update_recipe(
        recipe_id: int,
        recipe_data: RecipeUpdate,
        db: Session = Depends(get_db),
) -> RecipeRead:
    """Update an existing recipe."""
    updated_recipe = crud_recipe.update_recipe(db, recipe_id, recipe_data)
    if updated_recipe is None:
        raise HTTPException(404, f"Recipe with ID {recipe_id} not found")
    return RecipeRead.model_validate(updated_recipe, from_attributes=True)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe",
)
def delete_recipe(
        recipe_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a recipe and all its related data."""
    try:
        crud_recipe.delete_recipe(db, recipe_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Recipe not found.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{recipe_id}/ingredients",
    response_model=RecipeIngredientRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an ingredient to a recipe",
)
def add_recipe_ingredient(
        recipe_id: int,
        ingredient_data: RecipeIngredientCreate,
        db: Session = Depends(get_db),
) -> RecipeIngredientRead:
    """Add an ingredient to a recipe."""
    try:
        ingredient = crud_recipe.add_recipe_ingredient(db, recipe_id, ingredient_data)
        return RecipeIngredientRead.model_validate(ingredient, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{recipe_id}/ingredients",
    response_model=list[RecipeIngredientRead],
    summary="Get recipe ingredients",
)
def get_recipe_ingredients(
        recipe_id: int,
        db: Session = Depends(get_db),
) -> list[RecipeIngredientRead]:
    """Get all ingredients for a recipe."""
    ingredients = crud_recipe.get_ingredients_for_recipe(db, recipe_id)
    return [RecipeIngredientRead.model_validate(ingredient, from_attributes=True) for ingredient in ingredients]


@router.patch(
    "/{recipe_id}/ingredients/{food_item_id}",
    response_model=RecipeIngredientRead,
    summary="Update a recipe ingredient",
)
def update_recipe_ingredient(
        recipe_id: int,
        food_item_id: int,
        ingredient_data: RecipeIngredientUpdate,
        db: Session = Depends(get_db),
) -> RecipeIngredientRead:
    """Update a recipe ingredient."""
    try:
        ingredient = crud_recipe.update_recipe_ingredient(db, recipe_id, food_item_id, ingredient_data)
        if ingredient is None:
            raise HTTPException(404, "Ingredient not found")
        return RecipeIngredientRead.model_validate(ingredient, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete(
    "/{recipe_id}/ingredients/{food_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an ingredient from a recipe",
)
def delete_recipe_ingredient(
        recipe_id: int,
        food_item_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Remove an ingredient from a recipe."""
    try:
        crud_recipe.delete_recipe_ingredient(db, recipe_id, food_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Ingredient not found.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{recipe_id}/nutrition",
    response_model=RecipeNutritionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update recipe nutrition",
)
def create_or_update_recipe_nutrition(
        recipe_id: int,
        nutrition_data: RecipeNutritionCreate,
        db: Session = Depends(get_db),
) -> RecipeNutritionRead:
    """Create or update nutrition information for a recipe."""
    try:
        nutrition = crud_recipe.create_or_update_recipe_nutrition(db, recipe_id, nutrition_data)
        return RecipeNutritionRead.model_validate(nutrition, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{recipe_id}/nutrition",
    response_model=RecipeNutritionRead,
    summary="Update recipe nutrition",
)
def update_recipe_nutrition(
        recipe_id: int,
        nutrition_data: RecipeNutritionUpdate,
        db: Session = Depends(get_db),
) -> RecipeNutritionRead:
    """Update existing nutrition information for a recipe."""
    nutrition = crud_recipe.update_recipe_nutrition(db, recipe_id, nutrition_data)
    if nutrition is None:
        raise HTTPException(404, "Nutrition information not found")
    return RecipeNutritionRead.model_validate(nutrition, from_attributes=True)


@router.delete(
    "/{recipe_id}/nutrition",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recipe nutrition",
)
def delete_recipe_nutrition(
        recipe_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete nutrition information for a recipe."""
    try:
        crud_recipe.delete_recipe_nutrition(db, recipe_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Nutrition not found.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/suggestions/by-ingredients",
    response_model=list[RecipeRead],
    summary="Get recipe suggestions by available ingredients",
)
def get_recipe_suggestions_by_ingredients(
        food_item_ids: list[int] = Query(..., description="Available food item IDs"),
        min_match_percentage: float = Query(0.7, ge=0.0, le=1.0, description="Minimum match percentage"),
        db: Session = Depends(get_db),
) -> list[RecipeRead]:
    """Get recipes that can be made with available ingredients."""
    recipes = crud_recipe.get_recipes_by_available_ingredients(db, food_item_ids, min_match_percentage)
    return [RecipeRead.model_validate(recipe, from_attributes=True) for recipe in recipes]


@router.get(
    "/ai-generated",
    response_model=list[RecipeRead],
    summary="Get AI-generated recipes",
)
def get_ai_generated_recipes(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
) -> list[RecipeRead]:
    """Get all AI-generated recipes."""
    recipes = crud_recipe.get_ai_generated_recipes(db, skip, limit)
    return [RecipeRead.model_validate(recipe, from_attributes=True) for recipe in recipes]


@router.post(
    "/{recipe_id}/reviews",
    response_model=RecipeReviewRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update a recipe review",
)
def create_or_update_recipe_review(
        recipe_id: int,
        user_id: int,
        review_data: RecipeReviewUpsert,
        db: Session = Depends(get_db),
) -> RecipeReviewRead:
    """Create or update a recipe review."""
    try:
        review = crud_recipe.create_or_update_recipe_review(db, user_id, recipe_id, review_data)
        return RecipeReviewRead.model_validate(review, from_attributes=True)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/{recipe_id}/reviews",
    response_model=list[RecipeReviewRead],
    summary="Get recipe reviews",
)
def get_recipe_reviews(
        recipe_id: int,
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db),
) -> list[RecipeReviewRead]:
    """Get all reviews for a recipe."""
    reviews = crud_recipe.get_recipe_reviews(db, recipe_id, skip, limit)
    return [RecipeReviewRead.model_validate(review, from_attributes=True) for review in reviews]


@router.get(
    "/{recipe_id}/rating-summary",
    response_model=RecipeRatingSummary,
    summary="Get recipe rating summary",
)
def get_recipe_rating_summary(
        recipe_id: int,
        db: Session = Depends(get_db),
) -> RecipeRatingSummary:
    """Get rating summary for a recipe."""
    return crud_recipe.get_recipe_rating_summary(db, recipe_id)


@router.patch(
    "/{recipe_id}/reviews/{user_id}",
    response_model=RecipeReviewRead,
    summary="Update a recipe review",
)
def update_recipe_review(
        recipe_id: int,
        user_id: int,
        review_data: RecipeReviewUpdate,
        db: Session = Depends(get_db),
) -> RecipeReviewRead:
    """Update an existing recipe review."""
    review = crud_recipe.update_recipe_review(db, user_id, recipe_id, review_data)
    if review is None:
        raise HTTPException(404, "Review not found")
    return RecipeReviewRead.model_validate(review, from_attributes=True)


@router.delete(
    "/{recipe_id}/reviews/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a recipe review",
)
def delete_recipe_review(
        recipe_id: int,
        user_id: int,
        db: Session = Depends(get_db),
) -> Response:
    """Delete a recipe review."""
    try:
        crud_recipe.delete_recipe_review(db, user_id, recipe_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Review not found.") from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
