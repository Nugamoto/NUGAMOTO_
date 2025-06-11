"""Unit tests for user health profile functionality."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import user_health as crud_user_health
from app.schemas.user_health import UserHealthProfileCreate, UserHealthProfileUpdate


class TestUserHealthProfileCRUD:
    """Test cases for user health profile CRUD operations."""

    def test_get_user_health_profile_by_user_id_not_found(self, db: Session):
        """Test retrieving non-existent health profile returns None."""
        profile = crud_user_health.get_user_health_profile_by_user_id(db, 999)
        assert profile is None

    def test_create_user_health_profile(self, db: Session):
        """Test creating a new health profile."""
        profile_data = UserHealthProfileCreate(
            age=30,
            gender="male",
            height_cm=180,
            weight_kg=75.0,
            activity_level="moderately active",
            goal="maintain health"
        )

        profile = crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile_data
        )

        assert profile.user_id == 1
        assert profile.age == 30
        assert profile.gender == "male"
        assert profile.height_cm == 180
        assert profile.weight_kg == 75.0
        assert profile.activity_level == "moderately active"
        assert profile.goal == "maintain health"
        assert profile.last_updated is not None

    def test_create_duplicate_profile_raises_integrity_error(self, db: Session):
        """Test creating duplicate profile raises IntegrityError."""
        profile_data = UserHealthProfileCreate(age=30)

        # Create first profile
        crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile_data
        )

        # Attempt to create duplicate should raise IntegrityError
        with pytest.raises(IntegrityError):
            crud_user_health.create_user_health_profile(
                db, user_id=1, profile_data=profile_data
            )

    def test_update_existing_health_profile(self, db: Session):
        """Test updating an existing health profile."""
        # Create initial profile
        initial_data = UserHealthProfileCreate(age=25, weight_kg=70.0)
        profile = crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=initial_data
        )
        initial_update_time = profile.last_updated

        # Update profile
        update_data = UserHealthProfileUpdate(age=26, height_cm=175)
        updated_profile = crud_user_health.update_user_health_profile(
            db, user_id=1, profile_data=update_data
        )

        assert updated_profile is not None
        assert updated_profile.id == profile.id  # Same profile
        assert updated_profile.age == 26  # Updated
        assert updated_profile.weight_kg == 70.0  # Unchanged
        assert updated_profile.height_cm == 175  # New field
        assert updated_profile.last_updated > initial_update_time

    def test_update_non_existent_profile_returns_none(self, db: Session):
        """Test updating non-existent profile returns None."""
        update_data = UserHealthProfileUpdate(age=30)
        result = crud_user_health.update_user_health_profile(
            db, user_id=999, profile_data=update_data
        )
        assert result is None

    def test_delete_user_health_profile(self, db: Session):
        """Test deleting a health profile."""
        # Create profile
        profile_data = UserHealthProfileCreate(age=30)
        crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile_data
        )

        # Delete profile
        success = crud_user_health.delete_user_health_profile(db, user_id=1)
        assert success is True

        # Verify deletion
        profile = crud_user_health.get_user_health_profile_by_user_id(db, user_id=1)
        assert profile is None

    def test_delete_non_existent_profile(self, db: Session):
        """Test deleting a non-existent profile returns False."""
        success = crud_user_health.delete_user_health_profile(db, user_id=999)
        assert success is False

    def test_create_invalid_user_id(self, db: Session):
        """Test creating profile with invalid user_id raises ValueError."""
        profile_data = UserHealthProfileCreate(age=30)

        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            crud_user_health.create_user_health_profile(
                db, user_id=0, profile_data=profile_data
            )

    def test_update_invalid_user_id(self, db: Session):
        """Test updating profile with invalid user_id raises ValueError."""
        profile_data = UserHealthProfileUpdate(age=30)

        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            crud_user_health.update_user_health_profile(
                db, user_id=-1, profile_data=profile_data
            )

    def test_bmi_calculation(self, db: Session):
        """Test BMI calculation property."""
        profile_data = UserHealthProfileCreate(
            height_cm=180, weight_kg=80.0
        )
        profile = crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile_data
        )

        expected_bmi = 80.0 / (1.8 ** 2)  # ~24.69
        assert abs(profile.bmi - expected_bmi) < 0.01

    def test_bmi_calculation_missing_data(self, db: Session):
        """Test BMI calculation returns None when data is missing."""
        profile_data = UserHealthProfileCreate(height_cm=180)  # Missing weight
        profile = crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile_data
        )

        assert profile.bmi is None

    def test_is_complete_property(self, db: Session):
        """Test is_complete property."""
        # Incomplete profile
        incomplete_data = UserHealthProfileCreate(age=30, height_cm=180)
        incomplete_profile = crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=incomplete_data
        )
        assert incomplete_profile.is_complete is False

        # Complete profile - update the existing profile
        complete_data = UserHealthProfileUpdate(
            age=30,
            gender="male",
            height_cm=180,
            weight_kg=75.0,
            activity_level="moderately active"
        )
        complete_profile = crud_user_health.update_user_health_profile(
            db, user_id=1, profile_data=complete_data
        )
        assert complete_profile.is_complete is True

    def test_get_profiles_by_criteria(self, db: Session):
        """Test filtering profiles by criteria."""
        # Create test profiles
        profile1_data = UserHealthProfileCreate(
            age=25, gender="female", activity_level="very active"
        )
        profile2_data = UserHealthProfileCreate(
            age=35, gender="male", activity_level="sedentary"
        )

        crud_user_health.create_user_health_profile(
            db, user_id=1, profile_data=profile1_data
        )
        crud_user_health.create_user_health_profile(
            db, user_id=2, profile_data=profile2_data
        )

        # Test filtering
        female_profiles = crud_user_health.get_profiles_by_criteria(
            db, gender="female"
        )
        assert len(female_profiles) == 1
        assert female_profiles[0].user_id == 1

        young_profiles = crud_user_health.get_profiles_by_criteria(
            db, max_age=30
        )
        assert len(young_profiles) == 1
        assert young_profiles[0].user_id == 1


class TestUserHealthProfileValidation:
    """Test cases for schema validation."""

    def test_gender_validation(self):
        """Test gender field validation."""
        # Valid genders
        valid_data = UserHealthProfileCreate(gender="male")
        assert valid_data.gender == "male"

        valid_data = UserHealthProfileCreate(gender="FEMALE")
        assert valid_data.gender == "female"  # Should be lowercased

        # Invalid gender should raise validation error
        with pytest.raises(ValueError, match="Gender must be one of"):
            UserHealthProfileCreate(gender="invalid_gender")

    def test_activity_level_validation(self):
        """Test activity level field validation."""
        # Valid activity level
        valid_data = UserHealthProfileCreate(activity_level="moderately active")
        assert valid_data.activity_level == "moderately active"

        # Case insensitive
        valid_data = UserHealthProfileCreate(activity_level="SEDENTARY")
        assert valid_data.activity_level == "sedentary"

        # Invalid activity level should raise validation error
        with pytest.raises(ValueError, match="Activity level must be one of"):
            UserHealthProfileCreate(activity_level="super active")

    def test_age_validation(self):
        """Test age field validation."""
        # Valid age
        valid_data = UserHealthProfileCreate(age=30)
        assert valid_data.age == 30

        # Invalid ages should raise validation error
        with pytest.raises(ValueError):
            UserHealthProfileCreate(age=-1)

        with pytest.raises(ValueError):
            UserHealthProfileCreate(age=200)

    def test_height_validation(self):
        """Test height field validation."""
        # Valid height
        valid_data = UserHealthProfileCreate(height_cm=180)
        assert valid_data.height_cm == 180

        # Invalid heights should raise validation error
        with pytest.raises(ValueError):
            UserHealthProfileCreate(height_cm=0)

        with pytest.raises(ValueError):
            UserHealthProfileCreate(height_cm=400)

    def test_weight_validation(self):
        """Test weight field validation."""
        # Valid weight
        valid_data = UserHealthProfileCreate(weight_kg=75.5)
        assert valid_data.weight_kg == 75.5

        # Invalid weights should raise validation error
        with pytest.raises(ValueError):
            UserHealthProfileCreate(weight_kg=0)

        with pytest.raises(ValueError):
            UserHealthProfileCreate(weight_kg=1500)
