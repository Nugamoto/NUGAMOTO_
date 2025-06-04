"""CRUD helper functions for recipe management."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.inventory import FoodItem
from app.models.recipe import Recipe, RecipeIngredient, RecipeNutrition, RecipeStep
from app.models.user import User
from app.schemas.recipe import (
    RecipeCreate,
    RecipeSearchParams,
    RecipeSummary,
    RecipeUpdate,
    RecipeNutritionCreate,
    RecipeNutritionUpdate,
)


# ------------------------------------------------------------------ #
# Recipe CRUD                                                        #
# ------------------------------------------------------------------ #

def create_recipe(db: Session, recipe_data: RecipeCreate) -> Recipe:
    """Create and persist a new recipe with all related data.

    Args:
        db: Database session.
        recipe_data: Validated recipe payload including ingredients, steps, and nutrition.

    Returns:
        The newly created, *refreshed* recipe instance with all relationships.

    Raises:
        ValueError: If referenced food items or user do not exist.
    """
    # Validate that all food items exist
    food_item_ids = [ingredient.food_item_id for ingredient in recipe_data.ingredients]
    existing_food_items = db.scalars(
        select(FoodItem.id).where(FoodItem.id.in_(food_item_ids))
    ).all()

    if len(existing_food_items) != len(food_item_ids):
        missing_ids = set(food_item_ids) - set(existing_food_items)
        raise ValueError(f"Food items not found: {missing_ids}")

    # Validate user exists if specified
    if recipe_data.created_by_user_id is not None:
        user_stmt = select(User).where(User.id == recipe_data.created_by_user_id)
        if db.scalar(user_stmt) is None:
            raise ValueError("User not found.")

    # Create the recipe
    new_recipe = Recipe(
        title=recipe_data.title,
        is_ai_generated=recipe_data.is_ai_generated,
        created_by_user_id=recipe_data.created_by_user_id,
    )
    db.add(new_recipe)
    db.flush()  # Get the recipe ID without committing

    # Create ingredients
    for ingredient_data in recipe_data.ingredients:
        ingredient = RecipeIngredient(
            recipe_id=new_recipe.id,
            food_item_id=ingredient_data.food_item_id,
            amount=ingredient_data.amount,
            unit=ingredient_data.unit,
        )
        db.add(ingredient)

    # Create steps
    for step_data in recipe_data.steps:
        step = RecipeStep(
            recipe_id=new_recipe.id,
            step_number=step_data.step_number,
            instruction=step_data.instruction,
        )
        db.add(step)

    # Create nutrition if provided
    if recipe_data.nutrition is not None:
        nutrition = RecipeNutrition(
            recipe_id=new_recipe.id,
            kcal=recipe_data.nutrition.kcal,
            protein_g=recipe_data.nutrition.protein_g,
            fat_g=recipe_data.nutrition.fat_g,
            carbs_g=recipe_data.nutrition.carbs_g,
            fiber_g=recipe_data.nutrition.fiber_g,
            source=recipe_data.nutrition.source,
        )
        db.add(nutrition)

    db.commit()
    db.refresh(new_recipe)
    return new_recipe


def get_recipe_by_id(db: Session, recipe_id: int) -> Recipe | None:
    """Return a recipe by primary key.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.

    Returns:
        The matching recipe or ``None``.
    """
    stmt = select(Recipe).where(Recipe.id == recipe_id)
    return db.scalar(stmt)


def get_recipe_with_details(db: Session, recipe_id: int) -> Recipe | None:
    """Return a recipe by primary key with all related data eagerly loaded.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.

    Returns:
        The matching recipe with all relationships loaded, or ``None``.
    """
    stmt = (
        select(Recipe)
        .options(
            selectinload(Recipe.created_by_user),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition),
        )
        .where(Recipe.id == recipe_id)
    )
    return db.scalar(stmt)


def get_all_recipes(
        db: Session,
        search_params: RecipeSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[Recipe]:
    """Return all recipes with optional filtering and pagination.

    Args:
        db: Database session.
        search_params: Optional search and filter parameters.
        skip: Number of records to skip (for pagination).
        limit: Maximum number of records to return.

    Returns:
        A list of recipes matching the criteria.
    """
    stmt = select(Recipe).options(selectinload(Recipe.created_by_user))

    if search_params:
        if search_params.title_contains:
            stmt = stmt.where(Recipe.title.ilike(f"%{search_params.title_contains}%"))

        if search_params.is_ai_generated is not None:
            stmt = stmt.where(Recipe.is_ai_generated == search_params.is_ai_generated)

        if search_params.created_by_user_id is not None:
            stmt = stmt.where(Recipe.created_by_user_id == search_params.created_by_user_id)

        if search_params.has_nutrition is not None:
            if search_params.has_nutrition:
                stmt = stmt.where(Recipe.nutrition.has())
            else:
                stmt = stmt.where(~Recipe.nutrition.has())

        # Nutrition-based filters require a join
        if search_params.max_kcal is not None or search_params.min_protein_g is not None:
            stmt = stmt.join(Recipe.nutrition)

            if search_params.max_kcal is not None:
                stmt = stmt.where(RecipeNutrition.kcal <= search_params.max_kcal)

            if search_params.min_protein_g is not None:
                stmt = stmt.where(RecipeNutrition.protein_g >= search_params.min_protein_g)

    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt).all())


def update_recipe(db: Session, recipe_id: int, recipe_data: RecipeUpdate) -> Recipe:
    """Update an existing recipe with partial data.

    Note: This only updates basic recipe fields. For ingredients, steps, and nutrition,
    use the dedicated update functions.

    Args:
        db: Active database session.
        recipe_id: Primary key of the target recipe.
        recipe_data: Validated payload containing partial recipe data.

    Returns:
        The updated and refreshed recipe instance.

    Raises:
        ValueError: If the recipe does not exist or user validation fails.
    """
    recipe = get_recipe_by_id(db, recipe_id)
    if recipe is None:
        raise ValueError("Recipe not found.")

    # Validate user if being updated
    if recipe_data.created_by_user_id is not None:
        user_stmt = select(User).where(User.id == recipe_data.created_by_user_id)
        if db.scalar(user_stmt) is None:
            raise ValueError("User not found.")

    # Update fields
    if recipe_data.title is not None:
        recipe.title = recipe_data.title
    if recipe_data.is_ai_generated is not None:
        recipe.is_ai_generated = recipe_data.is_ai_generated
    if recipe_data.created_by_user_id is not None:
        recipe.created_by_user_id = recipe_data.created_by_user_id

    db.commit()
    db.refresh(recipe)
    return recipe


def delete_recipe(db: Session, recipe_id: int) -> None:
    """Remove a recipe from the database.

    All related ingredients, steps, and nutrition will be automatically
    deleted due to cascade configuration.

    Args:
        db: Active database session.
        recipe_id: Primary key of the recipe to delete.

    Raises:
        ValueError: If the recipe does not exist.
    """
    recipe = get_recipe_by_id(db, recipe_id)
    if recipe is None:
        raise ValueError("Recipe not found.")

    db.delete(recipe)
    db.commit()


def get_recipe_summary(db: Session) -> RecipeSummary:
    """Get summary statistics for all recipes.

    Args:
        db: Database session.

    Returns:
        Summary statistics including counts by type and nutrition status.
    """
    total_recipes = db.scalar(select(func.count(Recipe.id))) or 0

    ai_generated_count = db.scalar(
        select(func.count(Recipe.id)).where(Recipe.is_ai_generated == True)
    ) or 0

    manual_count = total_recipes - ai_generated_count

    with_nutrition_count = db.scalar(
        select(func.count(Recipe.id)).where(Recipe.nutrition.has())
    ) or 0

    return RecipeSummary(
        total_recipes=total_recipes,
        ai_generated_count=ai_generated_count,
        manual_count=manual_count,
        with_nutrition_count=with_nutrition_count,
    )


# ------------------------------------------------------------------ #
# Recipe Nutrition CRUD                                              #
# ------------------------------------------------------------------ #

def create_or_update_recipe_nutrition(
        db: Session, recipe_id: int, nutrition_data: RecipeNutritionCreate
) -> RecipeNutrition:
    """Create or update nutrition information for a recipe.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.
        nutrition_data: Validated nutrition payload.

    Returns:
        The created or updated nutrition instance.

    Raises:
        ValueError: If the recipe does not exist.
    """
    # Validate recipe exists
    recipe = get_recipe_by_id(db, recipe_id)
    if recipe is None:
        raise ValueError("Recipe not found.")

    # Check if nutrition already exists
    existing_nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )

    if existing_nutrition:
        # Update existing nutrition
        existing_nutrition.kcal = nutrition_data.kcal
        existing_nutrition.protein_g = nutrition_data.protein_g
        existing_nutrition.fat_g = nutrition_data.fat_g
        existing_nutrition.carbs_g = nutrition_data.carbs_g
        existing_nutrition.fiber_g = nutrition_data.fiber_g
        existing_nutrition.source = nutrition_data.source

        db.commit()
        db.refresh(existing_nutrition)
        return existing_nutrition
    else:
        # Create new nutrition
        new_nutrition = RecipeNutrition(
            recipe_id=recipe_id,
            kcal=nutrition_data.kcal,
            protein_g=nutrition_data.protein_g,
            fat_g=nutrition_data.fat_g,
            carbs_g=nutrition_data.carbs_g,
            fiber_g=nutrition_data.fiber_g,
            source=nutrition_data.source,
        )
        db.add(new_nutrition)
        db.commit()
        db.refresh(new_nutrition)
        return new_nutrition


def update_recipe_nutrition(
        db: Session, recipe_id: int, nutrition_data: RecipeNutritionUpdate
) -> RecipeNutrition:
    """Update existing nutrition information for a recipe.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.
        nutrition_data: Validated partial nutrition payload.

    Returns:
        The updated nutrition instance.

    Raises:
        ValueError: If the recipe or nutrition does not exist.
    """
    nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if nutrition is None:
        raise ValueError("Recipe nutrition not found.")

    # Update fields
    if nutrition_data.kcal is not None:
        nutrition.kcal = nutrition_data.kcal
    if nutrition_data.protein_g is not None:
        nutrition.protein_g = nutrition_data.protein_g
    if nutrition_data.fat_g is not None:
        nutrition.fat_g = nutrition_data.fat_g
    if nutrition_data.carbs_g is not None:
        nutrition.carbs_g = nutrition_data.carbs_g
    if nutrition_data.fiber_g is not None:
        nutrition.fiber_g = nutrition_data.fiber_g
    if nutrition_data.source is not None:
        nutrition.source = nutrition_data.source

    db.commit()
    db.refresh(nutrition)
    return nutrition


def delete_recipe_nutrition(db: Session, recipe_id: int) -> None:
    """Remove nutrition information from a recipe.

    Args:
        db: Active database session.
        recipe_id: Primary key of the recipe.

    Raises:
        ValueError: If the nutrition does not exist.
    """
    nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if nutrition is None:
        raise ValueError("Recipe nutrition not found.")

    db.delete(nutrition)
    db.commit()


# ------------------------------------------------------------------ #
# Utility Functions for AI Integration                               #
# ------------------------------------------------------------------ #

def get_recipes_by_available_ingredients(
        db: Session,
        available_food_item_ids: list[int],
        min_match_percentage: float = 0.7
) -> list[Recipe]:
    """Find recipes that can be made with available ingredients.

    This function is designed for AI integration to suggest recipes
    based on current kitchen inventory.

    Args:
        db: Database session.
        available_food_item_ids: List of food item IDs currently available.
        min_match_percentage: Minimum percentage of ingredients that must be available.

    Returns:
        A list of recipes that can be made with available ingredients.

    Note:
        This function can be integrated with inventory management to suggest
        recipes based on what's currently available in the kitchen.
    """
    # Subquery to count total ingredients per recipe
    total_ingredients_subq = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label("total_ingredients")
        )
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    # Subquery to count available ingredients per recipe
    available_ingredients_subq = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label("available_ingredients")
        )
        .where(RecipeIngredient.food_item_id.in_(available_food_item_ids))
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    # Main query to find recipes with sufficient ingredient matches
    stmt = (
        select(Recipe)
        .join(total_ingredients_subq, Recipe.id == total_ingredients_subq.c.recipe_id)
        .join(available_ingredients_subq, Recipe.id == available_ingredients_subq.c.recipe_id)
        .where(
            (available_ingredients_subq.c.available_ingredients.cast(float) /
             total_ingredients_subq.c.total_ingredients.cast(float)) >= min_match_percentage
        )
        .options(selectinload(Recipe.created_by_user))
        .order_by(
            (available_ingredients_subq.c.available_ingredients.cast(float) /
             total_ingredients_subq.c.total_ingredients.cast(float)).desc()
        )
    )

    return list(db.scalars(stmt).all())


def get_ai_generated_recipes(db: Session, limit: int = 50) -> list[Recipe]:
    """Get recently created AI-generated recipes.

    This function can be used to analyze AI recipe generation patterns
    and improve future AI prompts.

    Args:
        db: Database session.
        limit: Maximum number of recipes to return.

    Returns:
        A list of AI-generated recipes ordered by creation time.
    """
    stmt = (
        select(Recipe)
        .where(Recipe.is_ai_generated == True)
        .options(
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition),
        )
        .order_by(Recipe.id.desc())
        .limit(limit)
    )

    return list(db.scalars(stmt).all())
