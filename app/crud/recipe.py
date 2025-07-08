"""CRUD operations for recipes, ingredients, steps, nutrition, and reviews."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.models.food import FoodItem
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep, RecipeNutrition, RecipeReview
from app.schemas.recipe import (
    RecipeCreate, RecipeRead, RecipeUpdate, RecipeWithDetails,
    RecipeIngredientCreate, RecipeIngredientRead, RecipeIngredientUpdate,
    RecipeStepRead, RecipeNutritionCreate, RecipeNutritionRead, RecipeNutritionUpdate,
    RecipeReviewUpsert, RecipeReviewRead, RecipeReviewUpdate,
    RecipeSearchParams, RecipeSummary, RecipeRatingSummary
)
from app.schemas.user import UserRead


# ================================================================== #
# Schema Builder Functions                                           #
# ================================================================== #

def build_recipe_read(recipe_orm: Recipe) -> RecipeRead:
    """Build RecipeRead schema from Recipe ORM instance."""
    return RecipeRead.model_validate(recipe_orm, from_attributes=True)


def build_recipe_with_details(recipe_orm: Recipe) -> RecipeWithDetails:
    """Build RecipeWithDetails schema from Recipe ORM instance with relationships."""
    # Convert to base dict and add computed fields
    base_data = RecipeWithDetails.model_validate(recipe_orm, from_attributes=True)

    # Override relationships with properly built schemas
    base_data.ingredients = [
        build_recipe_ingredient_read(ingredient)
        for ingredient in recipe_orm.ingredients
    ]

    base_data.steps = [
        build_recipe_step_read(step)
        for step in recipe_orm.steps
    ]

    if recipe_orm.nutrition:
        base_data.nutrition = build_recipe_nutrition_read(recipe_orm.nutrition)

    if recipe_orm.created_by_user:
        base_data.created_by_user = UserRead.model_validate(recipe_orm.created_by_user, from_attributes=True)

    return base_data


def build_recipe_ingredient_read(ingredient_orm: RecipeIngredient) -> RecipeIngredientRead:
    """Build RecipeIngredientRead schema from RecipeIngredient ORM instance."""
    # Start with base validation
    base_data = RecipeIngredientRead.model_validate(ingredient_orm, from_attributes=True)

    # Add computed fields
    base_data.food_item_name = ingredient_orm.food_item.name
    base_data.base_unit_name = ingredient_orm.food_item.base_unit.name
    base_data.original_unit_name = ingredient_orm.original_unit.name if ingredient_orm.original_unit else None

    # Calculate display values
    base_data.display_amount = ingredient_orm.original_amount or ingredient_orm.amount_in_base_unit
    base_data.display_unit = (
        ingredient_orm.original_unit.name if ingredient_orm.original_unit
        else ingredient_orm.food_item.base_unit.name
    )

    return base_data


def build_recipe_step_read(step_orm: RecipeStep) -> RecipeStepRead:
    """Build RecipeStepRead schema from RecipeStep ORM instance."""
    return RecipeStepRead.model_validate(step_orm, from_attributes=True)


def build_recipe_nutrition_read(nutrition_orm: RecipeNutrition) -> RecipeNutritionRead:
    """Build RecipeNutritionRead schema from RecipeNutrition ORM instance."""
    # Start with base validation
    base_data = RecipeNutritionRead.model_validate(nutrition_orm, from_attributes=True)

    # Calculate computed fields
    base_data.has_complete_macros = all([
        nutrition_orm.protein_g is not None,
        nutrition_orm.fat_g is not None,
        nutrition_orm.carbs_g is not None
    ])

    if base_data.has_complete_macros:
        base_data.calculated_kcal = (
                (nutrition_orm.protein_g * 4) +
                (nutrition_orm.fat_g * 9) +
                (nutrition_orm.carbs_g * 4)
        )

    return base_data


def build_recipe_review_read(review_orm: RecipeReview) -> RecipeReviewRead:
    """Build RecipeReviewRead schema from RecipeReview ORM instance."""
    # Start with base validation
    base_data = RecipeReviewRead.model_validate(review_orm, from_attributes=True)

    # Add nested user data
    if review_orm.user:
        base_data.user = UserRead.model_validate(review_orm.user, from_attributes=True)

    return base_data


# ================================================================== #
# Recipe CRUD Operations                                             #
# ================================================================== #

def create_recipe(db: Session, recipe_data: RecipeCreate) -> Recipe:
    """Create a new recipe with ingredients, steps, and optional nutrition."""
    # Create recipe
    recipe_orm = Recipe(
        title=recipe_data.title,
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
    db.refresh(recipe_orm)

    # Load relationships for return
    return get_recipe_orm_with_relationships(db, recipe_orm.id)


def get_recipe_by_id(db: Session, recipe_id: int) -> Recipe | None:
    """Get a recipe by ID without relationships."""
    return get_recipe_orm_by_id(db, recipe_id)


def get_recipe_with_details(db: Session, recipe_id: int) -> Recipe | None:
    """Get a recipe with all details (ingredients, steps, nutrition)."""
    return get_recipe_orm_with_relationships(db, recipe_id)


def get_all_recipes(
        db: Session,
        search_params: RecipeSearchParams | None = None,
        skip: int = 0,
        limit: int = 100
) -> list[Recipe]:
    """Get all recipes with optional filtering and pagination."""
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user)
    )

    # Apply filters
    if search_params:
        if search_params.title_contains:
            query = query.where(Recipe.title.ilike(f"%{search_params.title_contains}%"))

        if search_params.is_ai_generated is not None:
            query = query.where(Recipe.is_ai_generated == search_params.is_ai_generated)

        if search_params.created_by_user_id:
            query = query.where(Recipe.created_by_user_id == search_params.created_by_user_id)

        if search_params.difficulty:
            query = query.where(Recipe.difficulty == search_params.difficulty)
        
        if search_params.has_nutrition is not None:
            if search_params.has_nutrition:
                query = query.join(RecipeNutrition)
            else:
                query = query.outerjoin(RecipeNutrition).where(RecipeNutrition.recipe_id.is_(None))

        if search_params.max_kcal:
            query = query.join(RecipeNutrition).where(RecipeNutrition.kcal <= search_params.max_kcal)

        if search_params.min_protein_g:
            query = query.join(RecipeNutrition).where(RecipeNutrition.protein_g >= search_params.min_protein_g)

        if search_params.tags_contains:
            for tag in search_params.tags_contains:
                # Fix: Use proper SQLAlchemy array contains syntax
                query = query.where(func.array_length(Recipe.tags, 1) > 0).where(
                    func.array_to_string(Recipe.tags, ',').contains(tag)
                )

    query = query.order_by(Recipe.created_at.desc()).offset(skip).limit(limit)

    return list(db.execute(query).scalars().all())


def update_recipe(db: Session, recipe_id: int, recipe_data: RecipeUpdate) -> Recipe | None:
    """Update an existing recipe."""
    recipe_orm = get_recipe_orm_by_id(db, recipe_id)
    if not recipe_orm:
        return None

    # Update fields
    update_data = recipe_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(recipe_orm, field, value)
    
    db.commit()
    db.refresh(recipe_orm)

    return get_recipe_orm_with_relationships(db, recipe_id)


def delete_recipe(db: Session, recipe_id: int) -> None:
    """Delete a recipe and all related data."""
    recipe_orm = get_recipe_orm_by_id(db, recipe_id)
    if not recipe_orm:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    db.delete(recipe_orm)
    db.commit()


def get_recipe_summary(db: Session) -> RecipeSummary:
    """Get recipe statistics summary."""
    total_query = select(func.count(Recipe.id))
    total_recipes = db.execute(total_query).scalar() or 0

    ai_query = select(func.count(Recipe.id)).where(Recipe.is_ai_generated == True)
    ai_generated_count = db.execute(ai_query).scalar() or 0
    
    manual_count = total_recipes - ai_generated_count

    nutrition_query = select(func.count(Recipe.id)).join(RecipeNutrition)
    with_nutrition_count = db.execute(nutrition_query).scalar() or 0

    # Count by difficulty
    difficulty_query = select(
        Recipe.difficulty,
        func.count(Recipe.id)
    ).group_by(Recipe.difficulty)

    difficulty_results = db.execute(difficulty_query).all()
    by_difficulty = {str(diff): count for diff, count in difficulty_results}
    
    return RecipeSummary(
        total_recipes=total_recipes,
        ai_generated_count=ai_generated_count,
        manual_count=manual_count,
        with_nutrition_count=with_nutrition_count,
        by_difficulty=by_difficulty
    )


# ================================================================== #
# Recipe Ingredient Operations                                       #
# ================================================================== #

def add_recipe_ingredient(
        db: Session,
        recipe_id: int,
        ingredient_data: RecipeIngredientCreate
) -> RecipeIngredient:
    """Add an ingredient to a recipe."""
    # Check if recipe exists
    recipe_orm = get_recipe_orm_by_id(db, recipe_id)
    if not recipe_orm:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    # Check if ingredient already exists
    existing = db.execute(
        select(RecipeIngredient).where(
            and_(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.food_item_id == ingredient_data.food_item_id
            )
        )
    ).scalar_one_or_none()
    
    if existing:
        raise ValueError("This ingredient is already in the recipe")

    ingredient_orm = RecipeIngredient(
        recipe_id=recipe_id,
        food_item_id=ingredient_data.food_item_id,
        amount_in_base_unit=ingredient_data.amount_in_base_unit,
        original_unit_id=ingredient_data.original_unit_id,
        original_amount=ingredient_data.original_amount
    )

    db.add(ingredient_orm)
    db.commit()
    db.refresh(ingredient_orm)

    return get_recipe_ingredient_orm_with_relationships(db, recipe_id, ingredient_data.food_item_id)


def get_ingredients_for_recipe(db: Session, recipe_id: int) -> list[RecipeIngredient]:
    """Get all ingredients for a recipe."""
    query = select(RecipeIngredient).options(
        selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
        selectinload(RecipeIngredient.original_unit)
    ).where(RecipeIngredient.recipe_id == recipe_id)

    return list(db.execute(query).scalars().all())


def update_recipe_ingredient(
        db: Session,
        recipe_id: int,
        food_item_id: int,
        ingredient_data: RecipeIngredientUpdate
) -> RecipeIngredient | None:
    """Update a recipe ingredient."""
    ingredient_orm = get_recipe_ingredient_orm_with_relationships(db, recipe_id, food_item_id)
    if not ingredient_orm:
        return None

    # Update fields
    update_data = ingredient_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(ingredient_orm, field, value)
    
    db.commit()
    db.refresh(ingredient_orm)

    return get_recipe_ingredient_orm_with_relationships(db, recipe_id, food_item_id)


def delete_recipe_ingredient(db: Session, recipe_id: int, food_item_id: int) -> None:
    """Remove an ingredient from a recipe."""
    ingredient_orm = db.execute(
        select(RecipeIngredient).where(
            and_(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.food_item_id == food_item_id
            )
        )
    ).scalar_one_or_none()

    if not ingredient_orm:
        raise ValueError("Ingredient not found in recipe")

    db.delete(ingredient_orm)
    db.commit()


# ================================================================== #
# Recipe Step CRUD Operations                                        #
# ================================================================== #

def add_recipe_step(
        db: Session,
        recipe_id: int,
        step_data: RecipeStepCreate,
        current_user_id: int | None = None
) -> RecipeStepRead:
    """
    Add a new step to a recipe.

    Args:
        db: Database session
        recipe_id: ID of the recipe
        step_data: Step data to create
        current_user_id: ID of the current user (for authorization)

    Returns:
        RecipeStepRead: The created step

    Raises:
        HTTPException: If recipe not found, step number already exists, or permission denied
    """
    from fastapi import HTTPException, status

    # Check if recipe exists and user has permission
    recipe = get_recipe_orm_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    # Check if user owns the recipe (if user authentication is enabled)
    if current_user_id is not None and recipe.created_by_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only add steps to your own recipes"
        )

    # Check if step number already exists for this recipe
    existing_step = db.query(RecipeStep).filter(
        RecipeStep.recipe_id == recipe_id,
        RecipeStep.step_number == step_data.step_number
    ).first()

    if existing_step:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Step number {step_data.step_number} already exists for this recipe"
        )

    # Create the new step
    db_step = RecipeStep(
        recipe_id=recipe_id,
        step_number=step_data.step_number,
        instruction=step_data.instruction
    )

    db.add(db_step)
    db.commit()
    db.refresh(db_step)

    return build_recipe_step_read(db_step)


def get_steps_for_recipe(
        db: Session,
        recipe_id: int,
        skip: int = 0,
        limit: int = 100
) -> list[RecipeStepRead]:
    """
    Get all steps for a specific recipe, ordered by step number.

    Args:
        db: Database session
        recipe_id: ID of the recipe
        skip: Number of steps to skip
        limit: Maximum number of steps to return

    Returns:
        list[RecipeStepRead]: List of recipe steps

    Raises:
        HTTPException: If recipe not found
    """
    from fastapi import HTTPException, status

    # Check if recipe exists
    recipe = get_recipe_orm_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    # Get steps ordered by step number
    steps = db.query(RecipeStep).filter(
        RecipeStep.recipe_id == recipe_id
    ).order_by(RecipeStep.step_number).offset(skip).limit(limit).all()

    return [build_recipe_step_read(step) for step in steps]


def update_recipe_step(
        db: Session,
        recipe_id: int,
        step_id: int,
        step_data: RecipeStepUpdate,
        current_user_id: int | None = None
) -> RecipeStepRead:
    """
    Update a specific recipe step.

    Args:
        db: Database session
        recipe_id: ID of the recipe
        step_id: ID of the step to update
        step_data: Updated step data
        current_user_id: ID of the current user (for authorization)

    Returns:
        RecipeStepRead: The updated step

    Raises:
        HTTPException: If recipe or step not found, step number conflict, or permission denied
    """
    from fastapi import HTTPException, status

    # Check if recipe exists and user has permission
    recipe = get_recipe_orm_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    # Check if user owns the recipe (if user authentication is enabled)
    if current_user_id is not None and recipe.created_by_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update steps in your own recipes"
        )

    # Get the step to update
    db_step = db.query(RecipeStep).filter(
        RecipeStep.id == step_id,
        RecipeStep.recipe_id == recipe_id
    ).first()

    if not db_step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step with ID {step_id} not found in recipe {recipe_id}"
        )

    # Check if step number is being changed and doesn't conflict
    if step_data.step_number is not None and step_data.step_number != db_step.step_number:
        existing_step = db.query(RecipeStep).filter(
            RecipeStep.recipe_id == recipe_id,
            RecipeStep.step_number == step_data.step_number,
            RecipeStep.id != step_id
        ).first()

        if existing_step:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Step number {step_data.step_number} already exists for this recipe"
            )

    # Update the step fields
    update_data = step_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_step, field, value)

    db.commit()
    db.refresh(db_step)

    return build_recipe_step_read(db_step)


def delete_recipe_step(
        db: Session,
        recipe_id: int,
        step_id: int,
        current_user_id: int | None = None
) -> dict[str, str]:
    """
    Delete a specific recipe step.

    Args:
        db: Database session
        recipe_id: ID of the recipe
        step_id: ID of the step to delete
        current_user_id: ID of the current user (for authorization)

    Returns:
        dict[str, str]: Success message

    Raises:
        HTTPException: If recipe or step not found, or permission denied
    """
    from fastapi import HTTPException, status

    # Check if recipe exists and user has permission
    recipe = get_recipe_orm_by_id(db, recipe_id)
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found"
        )

    # Check if user owns the recipe (if user authentication is enabled)
    if current_user_id is not None and recipe.created_by_user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete steps from your own recipes"
        )

    # Get the step to delete
    db_step = db.query(RecipeStep).filter(
        RecipeStep.id == step_id,
        RecipeStep.recipe_id == recipe_id
    ).first()

    if not db_step:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Step with ID {step_id} not found in recipe {recipe_id}"
        )

    # Delete the step
    db.delete(db_step)
    db.commit()

    return {"message": f"Step {step_id} successfully deleted from recipe {recipe_id}"}


def get_recipe_step_orm_with_relationships(
        db: Session,
        recipe_id: int,
        step_id: int
) -> RecipeStep | None:
    """
    Get a recipe step ORM object with relationships loaded.

    Args:
        db: Database session
        recipe_id: ID of the recipe
        step_id: ID of the step

    Returns:
        RecipeStep | None: The step ORM object or None if not found
    """
    return db.query(RecipeStep).filter(
        RecipeStep.id == step_id,
        RecipeStep.recipe_id == recipe_id
    ).first()


# ================================================================== #
# Recipe Nutrition Operations                                        #
# ================================================================== #

def create_or_update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionCreate
) -> RecipeNutrition:
    """Create or update nutrition information for a recipe."""
    # Check if recipe exists
    recipe_orm = get_recipe_orm_by_id(db, recipe_id)
    if not recipe_orm:
        raise ValueError(f"Recipe with ID {recipe_id} not found")

    # Check if nutrition already exists
    existing = db.execute(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    ).scalar_one_or_none()

    if existing:
        # Update existing
        update_data = nutrition_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing, field, value)
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
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
        db.refresh(nutrition_orm)
        return nutrition_orm


def update_recipe_nutrition(
        db: Session,
        recipe_id: int,
        nutrition_data: RecipeNutritionUpdate
) -> RecipeNutrition | None:
    """Update existing nutrition information."""
    nutrition_orm = db.execute(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    ).scalar_one_or_none()

    if not nutrition_orm:
        return None

    # Update fields
    update_data = nutrition_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nutrition_orm, field, value)
    
    db.commit()
    db.refresh(nutrition_orm)

    return nutrition_orm


def delete_recipe_nutrition(db: Session, recipe_id: int) -> None:
    """Delete nutrition information for a recipe."""
    nutrition_orm = db.execute(
        select(RecipeNutrition).where(RecipeNutrition.recipe_id == recipe_id)
    ).scalar_one_or_none()

    if not nutrition_orm:
        raise ValueError("Nutrition information not found")

    db.delete(nutrition_orm)
    db.commit()


# ================================================================== #
# Recipe Advanced Queries                                           #
# ================================================================== #

def get_recipes_by_available_ingredients(
        db: Session,
        food_item_ids: list[int],
        min_match_percentage: float = 0.7
) -> list[Recipe]:
    """Get recipes that can be made with available ingredients."""
    # Subquery to count total ingredients per recipe
    ingredient_counts = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label('total_ingredients')
        )
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    # Subquery to count matching ingredients per recipe
    matching_counts = (
        select(
            RecipeIngredient.recipe_id,
            func.count(RecipeIngredient.food_item_id).label('matching_ingredients')
        )
        .where(RecipeIngredient.food_item_id.in_(food_item_ids))
        .group_by(RecipeIngredient.recipe_id)
        .subquery()
    )

    # Main query with match percentage calculation
    query = (
        select(Recipe)
        .join(ingredient_counts, Recipe.id == ingredient_counts.c.recipe_id)
        .join(matching_counts, Recipe.id == matching_counts.c.recipe_id)
        .where(
            (matching_counts.c.matching_ingredients * 1.0 / ingredient_counts.c.total_ingredients)
            >= min_match_percentage
        )
        .options(selectinload(Recipe.created_by_user))
        .order_by(
            (matching_counts.c.matching_ingredients * 1.0 / ingredient_counts.c.total_ingredients).desc()
        )
    )

    return list(db.execute(query).scalars().all())


def get_ai_generated_recipes(db: Session, skip: int = 0, limit: int = 100) -> list[Recipe]:
    """Get all AI-generated recipes."""
    query = select(Recipe).options(
        selectinload(Recipe.created_by_user)
    ).where(Recipe.is_ai_generated == True).order_by(Recipe.created_at.desc()).offset(skip).limit(limit)

    return list(db.execute(query).scalars().all())


# ================================================================== #
# Recipe Review Operations                                           #
# ================================================================== #

def create_or_update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpsert
) -> RecipeReview:
    """Create or update a recipe review."""
    # Check if review already exists
    existing = db.execute(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    ).scalar_one_or_none()

    if existing:
        # Update existing
        existing.rating = review_data.rating
        existing.comment = review_data.comment
        
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new
        review_orm = RecipeReview(
            user_id=user_id,
            recipe_id=recipe_id,
            rating=review_data.rating,
            comment=review_data.comment
        )

        db.add(review_orm)
        db.commit()
        db.refresh(review_orm)

        return get_recipe_review_orm_with_relationships(db, user_id, recipe_id)


def get_recipe_reviews(db: Session, recipe_id: int, skip: int = 0, limit: int = 100) -> list[RecipeReview]:
    """Get all reviews for a recipe."""
    query = select(RecipeReview).options(
        selectinload(RecipeReview.user)
    ).where(RecipeReview.recipe_id == recipe_id).order_by(RecipeReview.created_at.desc()).offset(skip).limit(limit)

    return list(db.execute(query).scalars().all())


def update_recipe_review(
        db: Session,
        user_id: int,
        recipe_id: int,
        review_data: RecipeReviewUpdate
) -> RecipeReview | None:
    """Update an existing recipe review."""
    review_orm = get_recipe_review_orm_with_relationships(db, user_id, recipe_id)
    if not review_orm:
        return None

    # Update fields
    update_data = review_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(review_orm, field, value)
    
    db.commit()
    db.refresh(review_orm)

    return review_orm


def delete_recipe_review(db: Session, user_id: int, recipe_id: int) -> None:
    """Delete a recipe review."""
    review_orm = db.execute(
        select(RecipeReview).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    ).scalar_one_or_none()

    if not review_orm:
        raise ValueError("Review not found")

    db.delete(review_orm)
    db.commit()


def get_recipe_rating_summary(db: Session, recipe_id: int) -> RecipeRatingSummary:
    """Get rating summary for a recipe."""
    # Get basic stats
    stats_query = select(
        func.count(RecipeReview.rating).label('total_reviews'),
        func.avg(RecipeReview.rating).label('average_rating')
    ).where(RecipeReview.recipe_id == recipe_id)

    stats = db.execute(stats_query).first()
    total_reviews = stats.total_reviews or 0
    average_rating = float(stats.average_rating) if stats.average_rating else None

    # Get rating distribution
    distribution_query = select(
        RecipeReview.rating,
        func.count(RecipeReview.rating)
    ).where(RecipeReview.recipe_id == recipe_id).group_by(RecipeReview.rating)

    distribution_results = db.execute(distribution_query).all()
    rating_distribution = {str(rating): count for rating, count in distribution_results}
    
    return RecipeRatingSummary(
        recipe_id=recipe_id,
        total_reviews=total_reviews,
        average_rating=average_rating,
        rating_distribution=rating_distribution
    )


# ================================================================== #
# Helper Functions for ORM Access                                   #
# ================================================================== #

def get_recipe_orm_by_id(db: Session, recipe_id: int) -> Recipe | None:
    """Get Recipe ORM instance by ID without relationships."""
    return db.execute(
        select(Recipe).where(Recipe.id == recipe_id)
    ).scalar_one_or_none()


def get_recipe_orm_with_relationships(db: Session, recipe_id: int) -> Recipe | None:
    """Get Recipe ORM instance by ID with all relationships loaded."""
    return db.execute(
        select(Recipe).options(
            selectinload(Recipe.created_by_user),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
            selectinload(Recipe.ingredients).selectinload(RecipeIngredient.original_unit),
            selectinload(Recipe.steps),
            selectinload(Recipe.nutrition)
        ).where(Recipe.id == recipe_id)
    ).scalar_one_or_none()


def get_recipe_ingredient_orm_with_relationships(
        db: Session,
        recipe_id: int,
        food_item_id: int
) -> RecipeIngredient | None:
    """Get RecipeIngredient ORM instance with relationships."""
    return db.execute(
        select(RecipeIngredient).options(
            selectinload(RecipeIngredient.food_item).selectinload(FoodItem.base_unit),
            selectinload(RecipeIngredient.original_unit)
        ).where(
            and_(
                RecipeIngredient.recipe_id == recipe_id,
                RecipeIngredient.food_item_id == food_item_id
            )
        )
    ).scalar_one_or_none()


def get_recipe_review_orm_with_relationships(
        db: Session,
        user_id: int,
        recipe_id: int
) -> RecipeReview | None:
    """Get RecipeReview ORM instance with relationships."""
    return db.execute(
        select(RecipeReview).options(
            selectinload(RecipeReview.user)
        ).where(
            and_(
                RecipeReview.user_id == user_id,
                RecipeReview.recipe_id == recipe_id
            )
        )
    ).scalar_one_or_none()
