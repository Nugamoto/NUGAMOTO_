"""CRUD helper functions for the Recipe model."""

from __future__ import annotations

from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import Select

from app.models.core import Unit
from app.models.food import FoodItem
from app.models.recipe import (
    Recipe, RecipeIngredient, RecipeStep, RecipeNutrition, RecipeReview
)
from app.models.user import User
from app.schemas.recipe import (
    RecipeCreate, RecipeUpdate, RecipeIngredientCreate, RecipeIngredientUpdate,
    RecipeSearchParams, RecipeSummary, RecipeNutritionCreate, RecipeNutritionUpdate,
    RecipeReviewUpsert, RecipeReviewUpdate, RecipeRatingSummary
)


def create_recipe(db: Session, recipe_data: RecipeCreate) -> Recipe:
    """Create and persist a new recipe with all related data.

    Args:
        db: Database session.
        recipe_data: Validated recipe payload.

    Returns:
        The newly created, refreshed recipe instance.
    """
    food_item_ids = [ingredient.food_item_id for ingredient in recipe_data.ingredients]
    existing_food_items = db.scalars(
        select(FoodItem.id).where(FoodItem.id.in_(food_item_ids))
    ).all()

    if len(existing_food_items) != len(food_item_ids):
        missing_ids = set(food_item_ids) - set(existing_food_items)
        raise ValueError(f"Food items not found: {missing_ids}")

    original_unit_ids = [
        ingredient.original_unit_id
        for ingredient in recipe_data.ingredients
        if ingredient.original_unit_id is not None
    ]
    if original_unit_ids:
        existing_units = db.scalars(
            select(Unit.id).where(Unit.id.in_(original_unit_ids))
        ).all()
        if len(existing_units) != len(original_unit_ids):
            missing_unit_ids = set(original_unit_ids) - set(existing_units)
            raise ValueError(f"Units not found: {missing_unit_ids}")

    if recipe_data.created_by_user_id is not None:
        user_stmt = select(User).where(User.id == recipe_data.created_by_user_id)
        if db.scalar(user_stmt) is None:
            raise ValueError("User not found.")

    new_recipe = Recipe(
        title=recipe_data.title,
        is_ai_generated=recipe_data.is_ai_generated,
        created_by_user_id=recipe_data.created_by_user_id,
        difficulty=recipe_data.difficulty,
        servings=recipe_data.servings,
        tags=recipe_data.tags,
    )
    db.add(new_recipe)
    db.flush()

    for ingredient_data in recipe_data.ingredients:
        ingredient = RecipeIngredient(
            recipe_id=new_recipe.id,
            food_item_id=ingredient_data.food_item_id,
            amount_in_base_unit=ingredient_data.amount_in_base_unit,
            original_unit_id=ingredient_data.original_unit_id,
            original_amount=ingredient_data.original_amount,
        )
        db.add(ingredient)

    for step_data in recipe_data.steps:
        step = RecipeStep(
            recipe_id=new_recipe.id,
            step_number=step_data.step_number,
            instruction=step_data.instruction,
        )
        db.add(step)

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
        The matching recipe or None.
    """
    return db.scalar(select(Recipe).where(Recipe.id == recipe_id))


def get_recipe_with_details(db: Session, recipe_id: int) -> Recipe | None:
    """Get a recipe with all related data loaded.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.

    Returns:
        The recipe with all relationships loaded, or None.
    """
    return db.scalar(
        select(Recipe)
        .options(
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.food_item),
            joinedload(Recipe.ingredients).joinedload(RecipeIngredient.original_unit),
            joinedload(Recipe.steps),
            joinedload(Recipe.nutrition),
            joinedload(Recipe.created_by_user)
        )
        .where(Recipe.id == recipe_id)
    )


def get_all_recipes(
        db: Session,
        search_params: RecipeSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[Recipe]:
    """Get all recipes with optional filtering.

    Args:
        db: Database session.
        search_params: Optional search parameters.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of recipes matching the criteria.
    """
    query: Select = (
        select(Recipe)
        .options(joinedload(Recipe.created_by_user))
        .order_by(Recipe.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    if search_params:
        if search_params.title_contains is not None:
            query = query.where(Recipe.title.ilike(f"%{search_params.title_contains}%"))
        if search_params.is_ai_generated is not None:
            query = query.where(Recipe.is_ai_generated == search_params.is_ai_generated)
        if search_params.created_by_user_id is not None:
            query = query.where(Recipe.created_by_user_id == search_params.created_by_user_id)
        if search_params.has_nutrition is not None:
            if search_params.has_nutrition:
                query = query.join(RecipeNutrition)
            else:
                query = query.outerjoin(RecipeNutrition).where(RecipeNutrition.recipe_id.is_(None))
        if search_params.max_kcal is not None:
            query = query.join(RecipeNutrition).where(RecipeNutrition.kcal <= search_params.max_kcal)
        if search_params.min_protein_g is not None:
            query = query.join(RecipeNutrition).where(RecipeNutrition.protein_g >= search_params.min_protein_g)

    return list(db.scalars(query).all())


def update_recipe(db: Session, recipe_id: int, recipe_data: RecipeUpdate) -> Recipe | None:
    """Update an existing recipe.

    Args:
        db: Database session.
        recipe_id: Primary key of the recipe.
        recipe_data: Validated update data.

    Returns:
        The updated recipe if found, None otherwise.
    """
    recipe = get_recipe_by_id(db, recipe_id)
    if recipe is None:
        return None

    update_data = recipe_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recipe, field, value)

    db.commit()
    db.refresh(recipe)
    return recipe


def delete_recipe(db: Session, recipe_id: int) -> None:
    """Remove a recipe from the database.

    Args:
        db: Database session.
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
        Summary with counts of different recipe types.
    """
    total_recipes = db.scalar(select(func.count(Recipe.id))) or 0
    ai_generated_count = db.scalar(
        select(func.count(Recipe.id)).where(Recipe.is_ai_generated == True)
    ) or 0
    manual_count = total_recipes - ai_generated_count
    with_nutrition_count = db.scalar(
        select(func.count(Recipe.id)).join(RecipeNutrition)
    ) or 0

    return RecipeSummary(
        total_recipes=total_recipes,
        ai_generated_count=ai_generated_count,
        manual_count=manual_count,
        with_nutrition_count=with_nutrition_count
    )


def add_recipe_ingredient(
        db: Session,
        recipe_id: int,
        ingredient_data: RecipeIngredientCreate
) -> RecipeIngredient:
    """Add an ingredient to a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        ingredient_data: Validated ingredient data.

    Returns:
        The newly created ingredient.

    Raises:
        ValueError: If recipe or food item doesn't exist.
    """
    if not get_recipe_by_id(db, recipe_id):
        raise ValueError("Recipe not found")

    food_item = db.scalar(select(FoodItem).where(FoodItem.id == ingredient_data.food_item_id))
    if not food_item:
        raise ValueError("Food item not found")

    if ingredient_data.original_unit_id is not None:
        unit = db.scalar(select(Unit).where(Unit.id == ingredient_data.original_unit_id))
        if not unit:
            raise ValueError("Original unit not found")

    existing = get_recipe_ingredient(db, recipe_id, ingredient_data.food_item_id)
    if existing:
        raise ValueError("Ingredient already exists in this recipe")

    db_ingredient = RecipeIngredient(
        recipe_id=recipe_id,
        food_item_id=ingredient_data.food_item_id,
        amount_in_base_unit=ingredient_data.amount_in_base_unit,
        original_unit_id=ingredient_data.original_unit_id,
        original_amount=ingredient_data.original_amount,
    )

    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    return db_ingredient


def get_recipe_ingredient(
        db: Session,
        recipe_id: int,
        food_item_id: int
) -> RecipeIngredient | None:
    """Get a specific recipe ingredient.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        food_item_id: The ID of the food item.

    Returns:
        The ingredient if found, None otherwise.
    """
    return db.scalar(
        select(RecipeIngredient)
        .options(
            joinedload(RecipeIngredient.food_item),
            joinedload(RecipeIngredient.original_unit)
        )
        .where(
            and_(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.food_item_id == food_item_id
            )
        )
    )


def get_ingredients_for_recipe(db: Session, recipe_id: int) -> list[RecipeIngredient]:
    """Get all ingredients for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.

    Returns:
        A list of ingredients with related objects loaded.
    """
    return list(
        db.scalars(
            select(RecipeIngredient)
            .options(
                joinedload(RecipeIngredient.food_item),
                joinedload(RecipeIngredient.original_unit)
            )
            .where(RecipeIngredient.recipe_id == recipe_id)
            .order_by(RecipeIngredient.food_item_id)
        ).all()
    )


def update_recipe_ingredient(
        db: Session,
        recipe_id: int,
        food_item_id: int,
        ingredient_data: RecipeIngredientUpdate
) -> RecipeIngredient | None:
    """Update a recipe ingredient.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        food_item_id: The ID of the food item.
        ingredient_data: Validated update data.

    Returns:
        The updated ingredient if found, None otherwise.
    """
    ingredient = get_recipe_ingredient(db, recipe_id, food_item_id)
    if ingredient is None:
        return None

    if ingredient_data.original_unit_id is not None:
        unit = db.scalar(select(Unit).where(Unit.id == ingredient_data.original_unit_id))
        if not unit:
            raise ValueError("Original unit not found")

    update_data = ingredient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient, field, value)

    db.commit()
    db.refresh(ingredient)
    return ingredient


def delete_recipe_ingredient(db: Session, recipe_id: int, food_item_id: int) -> None:
    """Remove an ingredient from a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        food_item_id: The ID of the food item.

    Raises:
        ValueError: If the ingredient was not found.
    """
    ingredient = get_recipe_ingredient(db, recipe_id, food_item_id)
    if ingredient is None:
        raise ValueError("Ingredient not found.")

    db.delete(ingredient)
    db.commit()


def create_or_update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionCreate
) -> RecipeNutrition:
    """Create or update nutrition information for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        nutrition_data: Validated nutrition data.

    Returns:
        The created or updated nutrition record.

    Raises:
        ValueError: If recipe doesn't exist.
    """
    if not get_recipe_by_id(db, recipe_id):
        raise ValueError("Recipe not found")

    existing_nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )

    if existing_nutrition:
        for field, value in nutrition_data.model_dump().items():
            setattr(existing_nutrition, field, value)
        db.commit()
        db.refresh(existing_nutrition)
        return existing_nutrition
    else:
        nutrition = RecipeNutrition(
            recipe_id=recipe_id,
            kcal=nutrition_data.kcal,
            protein_g=nutrition_data.protein_g,
            fat_g=nutrition_data.fat_g,
            carbs_g=nutrition_data.carbs_g,
            fiber_g=nutrition_data.fiber_g,
            source=nutrition_data.source,
        )
        db.add(nutrition)
        db.commit()
        db.refresh(nutrition)
        return nutrition


def update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionUpdate
) -> RecipeNutrition | None:
    """Update existing nutrition information for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        nutrition_data: Validated update data.

    Returns:
        The updated nutrition record if found, None otherwise.
    """
    nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if nutrition is None:
        return None

    update_data = nutrition_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nutrition, field, value)

    db.commit()
    db.refresh(nutrition)
    return nutrition


def delete_recipe_nutrition(db: Session, recipe_id: int) -> None:
    """Delete nutrition information for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.

    Raises:
        ValueError: If nutrition was not found.
    """
    nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if nutrition is None:
        raise ValueError("Nutrition not found.")

    db.delete(nutrition)
    db.commit()


def get_recipes_by_available_ingredients(
        db: Session,
        food_item_ids: list[int],
        min_match_percentage: float = 0.7
) -> list[Recipe]:
    """Get recipes that can be made with available ingredients.

    Args:
        db: Database session.
        food_item_ids: List of available food item IDs.
        min_match_percentage: Minimum percentage of ingredients that must be available.

    Returns:
        A list of recipes ordered by ingredient match percentage.
    """
    if not food_item_ids:
        return []

    total_ingredients = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label("total_count")
        )
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    available_ingredients = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label("available_count")
        )
        .where(RecipeIngredient.food_item_id.in_(food_item_ids))
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    query = (
        select(Recipe)
        .join(total_ingredients, Recipe.id == total_ingredients.c.recipe_id)
        .join(available_ingredients, Recipe.id == available_ingredients.c.recipe_id)
        .where(
            (available_ingredients.c.available_count * 1.0 / total_ingredients.c.total_count) >= min_match_percentage
        )
        .order_by(
            (available_ingredients.c.available_count * 1.0 / total_ingredients.c.total_count).desc()
        )
    )

    return list(db.scalars(query).all())


def get_ai_generated_recipes(db: Session, skip: int = 0, limit: int = 100) -> list[Recipe]:
    """Get all AI-generated recipes.

    Args:
        db: Database session.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of AI-generated recipes.
    """
    query = (
        select(Recipe)
        .options(joinedload(Recipe.created_by_user))
        .where(Recipe.is_ai_generated == True)
        .order_by(Recipe.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(query).all())


def create_or_update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpsert
) -> RecipeReview:
    """Create or update a recipe review.

    Args:
        db: Database session.
        user_id: The ID of the user writing the review.
        recipe_id: The ID of the recipe being reviewed.
        review_data: Validated review data.

    Returns:
        The created or updated review.

    Raises:
        ValueError: If user or recipe doesn't exist.
    """
    if not db.scalar(select(User).where(User.id == user_id)):
        raise ValueError("User not found")
    if not get_recipe_by_id(db, recipe_id):
        raise ValueError("Recipe not found")

    existing_review = db.scalar(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    )

    if existing_review:
        existing_review.rating = review_data.rating
        existing_review.comment = review_data.comment
        db.commit()
        db.refresh(existing_review)
        return existing_review
    else:
        review = RecipeReview(
            user_id=user_id,
            recipe_id=recipe_id,
            rating=review_data.rating,
            comment=review_data.comment,
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review


def get_recipe_reviews(
        db: Session,
        recipe_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[RecipeReview]:
    """Get all reviews for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.
        skip: Number of records to skip.
        limit: Maximum number of records to return.

    Returns:
        A list of reviews with user information.
    """
    return list(
        db.scalars(
            select(RecipeReview)
            .options(joinedload(RecipeReview.user))
            .where(RecipeReview.recipe_id == recipe_id)
            .order_by(RecipeReview.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).all()
    )


def get_recipe_review_by_user(
        db: Session,
        user_id: int,
        recipe_id: int
) -> RecipeReview | None:
    """Get a specific user's review for a recipe.

    Args:
        db: Database session.
        user_id: The ID of the user.
        recipe_id: The ID of the recipe.

    Returns:
        The review if found, None otherwise.
    """
    return db.scalar(
        select(RecipeReview)
        .options(joinedload(RecipeReview.user))
        .where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    )


def update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpdate
) -> RecipeReview | None:
    """Update an existing recipe review.

    Args:
        db: Database session.
        user_id: The ID of the user.
        recipe_id: The ID of the recipe.
        review_data: Validated update data.

    Returns:
        The updated review if found, None otherwise.
    """
    review = get_recipe_review_by_user(db, user_id, recipe_id)
    if review is None:
        return None

    update_data = review_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review, field, value)

    db.commit()
    db.refresh(review)
    return review


def delete_recipe_review(db: Session, user_id: int, recipe_id: int) -> None:
    """Delete a recipe review.

    Args:
        db: Database session.
        user_id: The ID of the user.
        recipe_id: The ID of the recipe.

    Raises:
        ValueError: If the review was not found.
    """
    review = get_recipe_review_by_user(db, user_id, recipe_id)
    if review is None:
        raise ValueError("Review not found.")

    db.delete(review)
    db.commit()


def get_recipe_rating_summary(db: Session, recipe_id: int) -> RecipeRatingSummary:
    """Get rating summary for a recipe.

    Args:
        db: Database session.
        recipe_id: The ID of the recipe.

    Returns:
        Summary with average rating and distribution.
    """
    reviews = db.scalars(
        select(RecipeReview).where(RecipeReview.recipe_id == recipe_id)
    ).all()

    total_reviews = len(reviews)
    if total_reviews == 0:
        return RecipeRatingSummary(
            recipe_id=recipe_id,
            total_reviews=0,
            average_rating=None,
            rating_distribution={"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        )

    total_rating = sum(review.rating for review in reviews)
    average_rating = total_rating / total_reviews

    distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
    for review in reviews:
        distribution[str(review.rating)] += 1

    return RecipeRatingSummary(
        recipe_id=recipe_id,
        total_reviews=total_reviews,
        average_rating=round(average_rating, 2),
        rating_distribution=distribution
    )
