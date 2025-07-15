"""Recipe CRUD operations."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.food import FoodItem
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep, RecipeNutrition, RecipeReview
from app.schemas.recipe import (
    RecipeCreate, RecipeRead, RecipeUpdate, RecipeWithDetails,
    RecipeIngredientCreate, RecipeIngredientRead, RecipeIngredientUpdate,
    RecipeStepCreate, RecipeStepRead, RecipeStepUpdate,
    RecipeNutritionCreate, RecipeNutritionRead, RecipeNutritionUpdate,
    RecipeReviewUpsert, RecipeReviewRead, RecipeReviewUpdate,
    RecipeSearchParams, RecipeSummary, RecipeRatingSummary
)


# ================================================================== #
# Schema Builder Functions                                           #
# ================================================================== #

def build_recipe_read(recipe_orm: Recipe) -> RecipeRead:
    """Convert Recipe ORM to Read schema.

    Args:
        recipe_orm: Recipe ORM object with loaded relationships

    Returns:
        RecipeRead schema
    """
    return RecipeRead.model_validate(recipe_orm, from_attributes=True)


def build_recipe_with_details(recipe_orm: Recipe) -> RecipeWithDetails:
    """Convert Recipe ORM to WithDetails schema.

    Args:
        recipe_orm: Recipe ORM object with loaded relationships

    Returns:
        RecipeWithDetails schema
    """
    return RecipeWithDetails.model_validate(recipe_orm, from_attributes=True)


def build_recipe_ingredient_read(ingredient_orm: RecipeIngredient) -> RecipeIngredientRead:
    """Convert RecipeIngredient ORM to Read schema.

    Args:
        ingredient_orm: RecipeIngredient ORM object with loaded relationships

    Returns:
        RecipeIngredientRead schema
    """
    return RecipeIngredientRead.model_validate(ingredient_orm, from_attributes=True)


def build_recipe_step_read(step_orm: RecipeStep) -> RecipeStepRead:
    """Convert RecipeStep ORM to Read schema.

    Args:
        step_orm: RecipeStep ORM object

    Returns:
        RecipeStepRead schema
    """
    return RecipeStepRead.model_validate(step_orm, from_attributes=True)


def build_recipe_nutrition_read(nutrition_orm: RecipeNutrition) -> RecipeNutritionRead:
    """Convert RecipeNutrition ORM to Read schema.

    Args:
        nutrition_orm: RecipeNutrition ORM object

    Returns:
        RecipeNutritionRead schema
    """
    return RecipeNutritionRead.model_validate(nutrition_orm, from_attributes=True)


def build_recipe_review_read(review_orm: RecipeReview) -> RecipeReviewRead:
    """Convert RecipeReview ORM to Read schema.

    Args:
        review_orm: RecipeReview ORM object with loaded relationships

    Returns:
        RecipeReviewRead schema
    """
    return RecipeReviewRead.model_validate(review_orm, from_attributes=True)


# ================================================================== #
# Recipe CRUD Operations                                             #
# ================================================================== #

def create_recipe(db: Session, recipe_data: RecipeCreate) -> RecipeRead:
    """Create a new recipe with ingredients, steps, and optional nutrition."""
    # Create recipe
    recipe_orm = Recipe(
        title=recipe_data.title,
        description=recipe_data.description,
        cuisine_type=recipe_data.cuisine_type,
        prep_time_minutes=recipe_data.prep_time_minutes,
        cook_time_minutes=recipe_data.cook_time_minutes,
        total_time_minutes=recipe_data.total_time_minutes,
        is_ai_generated=recipe_data.is_ai_generated,
        created_by_user_id=recipe_data.created_by_user_id,
        difficulty=recipe_data.difficulty,
        servings=recipe_data.servings,
        tags=recipe_data.tags
    )
    db.add(recipe_orm)
    db.flush()  # Get the ID

    # Create ingredients
    for ingredient_data in recipe_data.ingredients:
        ingredient_orm = RecipeIngredient(
            recipe_id=recipe_orm.id,
            food_item_id=ingredient_data.food_item_id,
            amount_in_base_unit=ingredient_data.amount_in_base_unit,
            original_unit_id=ingredient_data.original_unit_id,
            original_amount=ingredient_data.original_amount
        )
        db.add(ingredient_orm)

    # Create steps
    for step_data in recipe_data.steps:
        step_orm = RecipeStep(
            recipe_id=recipe_orm.id,
            step_number=step_data.step_number,
            instruction=step_data.instruction
        )
        db.add(step_orm)

    # Create nutrition if provided
    if recipe_data.nutrition:
        nutrition_orm = RecipeNutrition(
            recipe_id=recipe_orm.id,
            kcal=recipe_data.nutrition.kcal,
            protein_g=recipe_data.nutrition.protein_g,
            fat_g=recipe_data.nutrition.fat_g,
            carbs_g=recipe_data.nutrition.carbs_g,
            fiber_g=recipe_data.nutrition.fiber_g,
            source=recipe_data.nutrition.source
        )
        db.add(nutrition_orm)

    db.commit()

    # Get the recipe with relationships and convert to RecipeRead
    recipe_with_relationships = get_recipe_orm_with_relationships(db, recipe_orm.id)
    return build_recipe_read(recipe_with_relationships)


def get_recipe_by_id(db: Session, recipe_id: int) -> RecipeRead | None:
    """Get a recipe by ID."""
    recipe_orm = get_recipe_orm_with_relationships(db, recipe_id)
    if not recipe_orm:
        return None
    return build_recipe_read(recipe_orm)


def get_recipe_with_details(db: Session, recipe_id: int) -> RecipeWithDetails | None:
    """Get a recipe with all details by ID."""
    recipe_orm = get_recipe_orm_with_relationships(db, recipe_id)
    if not recipe_orm:
        return None
    return build_recipe_with_details(recipe_orm)


def get_all_recipes(
        db: Session,
        search_params: RecipeSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[RecipeRead]:
    """Get all recipes with pagination and optional filtering."""
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user)
    )

    # Apply filters if search_params provided
    if search_params:
        if search_params.title_contains:
            query = query.where(Recipe.title.ilike(f"%{search_params.title_contains}%"))
        if search_params.is_ai_generated is not None:
            query = query.where(Recipe.is_ai_generated == search_params.is_ai_generated)
        if search_params.created_by_user_id is not None:
            query = query.where(Recipe.created_by_user_id == search_params.created_by_user_id)
        if search_params.difficulty:
            query = query.where(Recipe.difficulty == search_params.difficulty)
        if search_params.has_nutrition is not None:
            if search_params.has_nutrition:
                query = query.join(RecipeNutrition, Recipe.id == RecipeNutrition.recipe_id)
            else:
                query = query.outerjoin(RecipeNutrition, Recipe.id == RecipeNutrition.recipe_id).where(
                    RecipeNutrition.recipe_id.is_(None))
        if search_params.max_kcal is not None:
            query = query.join(RecipeNutrition, Recipe.id == RecipeNutrition.recipe_id).where(
                RecipeNutrition.kcal <= search_params.max_kcal)
        if search_params.min_protein_g is not None:
            query = query.join(RecipeNutrition, Recipe.id == RecipeNutrition.recipe_id).where(
                RecipeNutrition.protein_g >= search_params.min_protein_g)
        if search_params.tags_contains:
            for tag in search_params.tags_contains:
                query = query.where(Recipe.tags.op('JSON_EXTRACT')('$[*]').like(f'%{tag}%'))

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    recipes = result.scalars().all()

    return [build_recipe_read(recipe) for recipe in recipes]


def update_recipe(db: Session, recipe_id: int, recipe_data: RecipeUpdate) -> RecipeRead | None:
    """Update a recipe."""
    recipe_orm = db.get(Recipe, recipe_id)
    if not recipe_orm:
        return None

    # Update fields
    update_data = recipe_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recipe_orm, field, value)

    db.commit()

    # Get updated recipe with relationships and convert
    updated_recipe = get_recipe_orm_with_relationships(db, recipe_id)
    return build_recipe_read(updated_recipe)


def delete_recipe(db: Session, recipe_id: int) -> None:
    """Delete a recipe by ID."""
    recipe_orm = db.get(Recipe, recipe_id)
    if not recipe_orm:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    db.delete(recipe_orm)
    db.commit()


def get_recipe_summary(db: Session) -> RecipeSummary:
    """Get recipe statistics summary."""
    # Count total recipes
    total_recipes = db.scalar(select(func.count(Recipe.id)))

    # Count AI generated recipes
    ai_generated_count = db.scalar(
        select(func.count(Recipe.id)).where(Recipe.is_ai_generated == True)
    )

    # Count manual recipes
    manual_count = total_recipes - ai_generated_count

    # Count recipes with nutrition
    with_nutrition_count = db.scalar(
        select(func.count(Recipe.id)).join(RecipeNutrition)
    )

    # Count by difficulty
    difficulty_counts = db.execute(
        select(Recipe.difficulty, func.count(Recipe.id))
        .group_by(Recipe.difficulty)
    ).all()

    by_difficulty = {difficulty: count for difficulty, count in difficulty_counts}

    return RecipeSummary(
        total_recipes=total_recipes,
        ai_generated_count=ai_generated_count,
        manual_count=manual_count,
        with_nutrition_count=with_nutrition_count,
        by_difficulty=by_difficulty
    )


# ================================================================== #
# Recipe Ingredient CRUD Operations                                  #
# ================================================================== #


def add_recipe_ingredient(
        db: Session,
        recipe_id: int,
        ingredient_data: RecipeIngredientCreate
) -> RecipeIngredientRead:
    """Add a new ingredient to a recipe."""
    from app.services.conversions.unit_conversion_service import UnitConversionService

    # Auto-calculate amount_in_base_unit if not provided
    if ingredient_data.amount_in_base_unit is None:
        conversion_service = UnitConversionService(db)
        ingredient_data.amount_in_base_unit = conversion_service.convert_to_base_unit(
            food_item_id=ingredient_data.food_item_id,
            amount=ingredient_data.original_amount,
            from_unit_id=ingredient_data.original_unit_id
        )

    # Check if recipe exists
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise ValueError(f"Recipe with id {recipe_id} not found")

    # Check if ingredient already exists for this recipe
    existing_ingredient = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id,
        RecipeIngredient.food_item_id == ingredient_data.food_item_id
    ).first()

    if existing_ingredient:
        raise ValueError(f"Ingredient with food_item_id {ingredient_data.food_item_id} already exists for this recipe")

    # Create new ingredient
    db_ingredient = RecipeIngredient(
        recipe_id=recipe_id,
        food_item_id=ingredient_data.food_item_id,
        amount_in_base_unit=ingredient_data.amount_in_base_unit,
        original_unit_id=ingredient_data.original_unit_id,
        original_amount=ingredient_data.original_amount
    )

    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)

    # Return with relationships
    ingredient_with_relations = get_recipe_ingredient_orm_with_relationships(db, recipe_id,
                                                                             ingredient_data.food_item_id)
    return build_recipe_ingredient_read(ingredient_with_relations)


def get_ingredients_for_recipe(db: Session, recipe_id: int) -> list[RecipeIngredientRead]:
    """Get all ingredients for a recipe."""
    query = select(RecipeIngredient).options(
        selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
        selectinload(RecipeIngredient.original_unit)
    ).where(RecipeIngredient.recipe_id == recipe_id)

    result = db.execute(query)
    ingredients = result.scalars().all()

    return [build_recipe_ingredient_read(ingredient) for ingredient in ingredients]


def update_recipe_ingredient(
        db: Session,
        recipe_id: int,
        food_item_id: int,
        ingredient_data: RecipeIngredientUpdate
) -> RecipeIngredientRead:
    """Update an existing recipe ingredient."""
    from app.services.conversions.unit_conversion_service import UnitConversionService

    # Auto-calculate amount_in_base_unit if not provided but original values are
    if ingredient_data.amount_in_base_unit is None and ingredient_data.original_amount and ingredient_data.original_unit_id:
        conversion_service = UnitConversionService(db)
        ingredient_data.amount_in_base_unit = conversion_service.convert_to_base_unit(
            food_item_id=ingredient_data.food_item_id or food_item_id,
            amount=ingredient_data.original_amount,
            from_unit_id=ingredient_data.original_unit_id
        )

    # Get existing ingredient
    ingredient = db.query(RecipeIngredient).filter(
        RecipeIngredient.recipe_id == recipe_id,
        RecipeIngredient.food_item_id == food_item_id
    ).first()

    if not ingredient:
        raise ValueError(f"Ingredient with food_item_id {food_item_id} not found for recipe {recipe_id}")

    # Update fields
    update_data = ingredient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient, field, value)

    db.commit()
    db.refresh(ingredient)

    # Return with relationships
    ingredient_with_relations = get_recipe_ingredient_orm_with_relationships(db, recipe_id, food_item_id)
    return build_recipe_ingredient_read(ingredient_with_relations)


def delete_recipe_ingredient(db: Session, recipe_id: int, food_item_id: int) -> None:
    """Remove an ingredient from a recipe."""
    ingredient_orm = db.scalar(
        select(RecipeIngredient).where(
            and_(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.food_item_id == food_item_id
            )
        )
    )
    if not ingredient_orm:
        raise ValueError(f"Ingredient with food item ID {food_item_id} not found in recipe {recipe_id}")

    db.delete(ingredient_orm)
    db.commit()


# ================================================================== #
# Recipe Step CRUD Operations                                        #
# ================================================================== #

def add_recipe_step(
        db: Session,
        recipe_id: int,
        step_data: RecipeStepCreate
) -> RecipeStepRead:
    """Add a step to a recipe."""
    # Validate recipe exists
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    # Create step
    step_orm = RecipeStep(
        recipe_id=recipe_id,
        step_number=step_data.step_number,
        instruction=step_data.instruction
    )
    db.add(step_orm)
    db.commit()

    return build_recipe_step_read(step_orm)


def get_steps_for_recipe(db: Session, recipe_id: int, skip: int = 0, limit: int = 100) -> list[RecipeStepRead]:
    """Get all steps for a recipe."""
    query = select(RecipeStep).where(RecipeStep.recipe_id == recipe_id).order_by(RecipeStep.step_number).offset(
        skip).limit(limit)
    result = db.execute(query)
    steps = result.scalars().all()

    return [build_recipe_step_read(step) for step in steps]


def update_recipe_step(
        db: Session,
        recipe_id: int,
        step_id: int,
        step_data: RecipeStepUpdate
) -> RecipeStepRead | None:
    """Update a recipe step."""
    step_orm = db.scalar(
        select(RecipeStep).where(
            and_(
                RecipeStep.recipe_id == recipe_id,
                RecipeStep.id == step_id
            )
        )
    )
    if not step_orm:
        return None

    # Update fields
    update_data = step_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(step_orm, field, value)

    db.commit()

    return build_recipe_step_read(step_orm)


def delete_recipe_step(db: Session, recipe_id: int, step_id: int) -> None:
    """Delete a recipe step."""
    step_orm = db.scalar(
        select(RecipeStep).where(
            and_(
                RecipeStep.recipe_id == recipe_id,
                RecipeStep.id == step_id
            )
        )
    )
    if not step_orm:
        raise ValueError(f"Step with ID {step_id} not found in recipe {recipe_id}")

    db.delete(step_orm)
    db.commit()


# ================================================================== #
# Recipe Nutrition CRUD Operations                                   #
# ================================================================== #

def create_or_update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionCreate
) -> RecipeNutritionRead:
    """Create or update nutrition information for a recipe."""
    # Validate recipe exists
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    # Check if nutrition already exists
    existing_nutrition = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )

    if existing_nutrition:
        # Update existing nutrition
        for field, value in nutrition_data.model_dump(exclude_unset=True).items():
            setattr(existing_nutrition, field, value)
        db.commit()
        return build_recipe_nutrition_read(existing_nutrition)
    else:
        # Create new nutrition
        nutrition_orm = RecipeNutrition(
            recipe_id=recipe_id,
            kcal=nutrition_data.kcal,
            protein_g=nutrition_data.protein_g,
            fat_g=nutrition_data.fat_g,
            carbs_g=nutrition_data.carbs_g,
            fiber_g=nutrition_data.fiber_g,
            source=nutrition_data.source
        )
        db.add(nutrition_orm)
        db.commit()
        return build_recipe_nutrition_read(nutrition_orm)


def update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionUpdate
) -> RecipeNutritionRead | None:
    """Update nutrition information for a recipe."""
    nutrition_orm = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if not nutrition_orm:
        return None

    # Update fields
    update_data = nutrition_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nutrition_orm, field, value)

    db.commit()

    return build_recipe_nutrition_read(nutrition_orm)


def delete_recipe_nutrition(db: Session, recipe_id: int) -> None:
    """Delete nutrition information for a recipe."""
    nutrition_orm = db.scalar(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    )
    if not nutrition_orm:
        raise ValueError(f"Nutrition information for recipe {recipe_id} not found")

    db.delete(nutrition_orm)
    db.commit()


# ================================================================== #
# Recipe Advanced Query Operations                                   #
# ================================================================== #

def get_recipes_by_available_ingredients(
        db: Session,
        food_item_ids: list[int],
        min_match_percentage: float = 0.7
) -> list[RecipeRead]:
    """Get recipe suggestions based on available ingredients."""
    # Get recipes with their ingredient count
    subquery = select(
        RecipeIngredient.recipe_id,
        func.count(RecipeIngredient.food_item_id).label('total_ingredients'),
        func.sum(
            func.case(
                (RecipeIngredient.food_item_id.in_(food_item_ids), 1),
                else_=0
            )
        ).label('matching_ingredients')
    ).group_by(RecipeIngredient.recipe_id).subquery()

    # Calculate match percentage and filter
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user)
    ).join(
        subquery, Recipe.id == subquery.c.recipe_id
    ).where(
        (subquery.c.matching_ingredients / subquery.c.total_ingredients) >= min_match_percentage
    ).order_by(
        (subquery.c.matching_ingredients / subquery.c.total_ingredients).desc()
    )

    result = db.execute(query)
    recipes = result.scalars().all()

    return [build_recipe_read(recipe) for recipe in recipes]


def get_ai_generated_recipes(db: Session, skip: int = 0, limit: int = 100) -> list[RecipeRead]:
    """Get all AI-generated recipes."""
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user)
    ).where(Recipe.is_ai_generated == True).offset(skip).limit(limit)

    result = db.execute(query)
    recipes = result.scalars().all()

    return [build_recipe_read(recipe) for recipe in recipes]


# ================================================================== #
# Recipe Review CRUD Operations                                      #
# ================================================================== #

def create_or_update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpsert
) -> RecipeReviewRead:
    """Create or update a recipe review."""
    # Check if review already exists
    existing_review = db.scalar(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    )

    if existing_review:
        # Update existing review
        existing_review.rating = review_data.rating
        existing_review.comment = review_data.comment
        db.commit()

        # Get updated review with relationships and convert
        updated_review = get_recipe_review_orm_with_relationships(db, user_id, recipe_id)
        return build_recipe_review_read(updated_review)
    else:
        # Create new review
        review_orm = RecipeReview(
            user_id=user_id,
            recipe_id=recipe_id,
            rating=review_data.rating,
            comment=review_data.comment
        )
        db.add(review_orm)
        db.commit()

        # Get new review with relationships and convert
        new_review = get_recipe_review_orm_with_relationships(db, user_id, recipe_id)
        return build_recipe_review_read(new_review)


def get_recipe_reviews(db: Session, recipe_id: int, skip: int = 0, limit: int = 100) -> list[RecipeReviewRead]:
    """Get all reviews for a recipe."""
    query = select(RecipeReview).options(
        selectinload(RecipeReview.user)
    ).where(RecipeReview.recipe_id == recipe_id).offset(skip).limit(limit)

    result = db.execute(query)
    reviews = result.scalars().all()

    return [build_recipe_review_read(review) for review in reviews]


def update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpdate
) -> RecipeReviewRead | None:
    """Update a recipe review."""
    review_orm = db.scalar(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    )
    if not review_orm:
        return None

    # Update fields
    update_data = review_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review_orm, field, value)

    db.commit()

    # Get updated review with relationships and convert
    updated_review = get_recipe_review_orm_with_relationships(db, user_id, recipe_id)
    return build_recipe_review_read(updated_review)


def delete_recipe_review(db: Session, user_id: int, recipe_id: int) -> None:
    """Delete a recipe review."""
    review_orm = db.scalar(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    )
    if not review_orm:
        raise ValueError(f"Review for recipe {recipe_id} by user {user_id} not found")

    db.delete(review_orm)
    db.commit()


def get_recipe_rating_summary(db: Session, recipe_id: int) -> RecipeRatingSummary:
    """Get rating summary for a recipe."""
    # Get all ratings for the recipe
    ratings_query = select(RecipeReview.rating).where(RecipeReview.recipe_id == recipe_id)
    ratings = db.execute(ratings_query).scalars().all()

    if not ratings:
        return RecipeRatingSummary(
            recipe_id=recipe_id,
            total_reviews=0,
            average_rating=0.0,
            rating_distribution={1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        )

    # Calculate average
    average_rating = sum(ratings) / len(ratings)

    # Calculate distribution
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for rating in ratings:
        rating_distribution[rating] += 1

    return RecipeRatingSummary(
        recipe_id=recipe_id,
        total_reviews=len(ratings),
        average_rating=average_rating,
        rating_distribution=rating_distribution
    )


# ================================================================== #
# Helper Functions for ORM Objects with Relationships               #
# ================================================================== #

def get_recipe_orm_by_id(db: Session, recipe_id: int) -> Recipe | None:
    """Get a recipe ORM object by ID."""
    return db.get(Recipe, recipe_id)


def get_recipe_orm_with_relationships(db: Session, recipe_id: int) -> Recipe | None:
    """Get a recipe ORM object with all relationships loaded."""
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.original_unit),
        selectinload(Recipe.steps),
        selectinload(Recipe.nutrition)
    ).where(Recipe.id == recipe_id)

    result = db.execute(query)
    return result.scalar_one_or_none()


def get_recipe_ingredient_orm_with_relationships(db: Session, recipe_id: int,
                                                 food_item_id: int) -> RecipeIngredient | None:
    """Get a recipe ingredient ORM object with relationships."""
    query = select(RecipeIngredient).options(
        selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
        selectinload(RecipeIngredient.original_unit)
    ).where(
        and_(
            RecipeIngredient.recipe_id == recipe_id,
            RecipeIngredient.food_item_id == food_item_id
        )
    )

    result = db.execute(query)
    return result.scalar_one_or_none()


def get_recipe_review_orm_with_relationships(db: Session, user_id: int, recipe_id: int) -> RecipeReview | None:
    """Get a recipe review ORM object with relationships."""
    query = select(RecipeReview).options(
        selectinload(RecipeReview.user)
    ).where(
        and_(
            RecipeReview.user_id == user_id,
            RecipeReview.recipe_id == recipe_id
        )
    )

    result = db.execute(query)
    return result.scalar_one_or_none()