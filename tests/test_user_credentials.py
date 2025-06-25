"""Unit tests for user credentials functionality."""

import datetime
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import user_credentials as crud_user_credentials
from app.crud import user as crud_user
from app.models.user_credentials import UserCredentials
from app.schemas.user_credentials import UserCredentialsCreate, UserCredentialsUpdate
from app.schemas.user import UserCreate


class TestUserCredentialsCRUD:
    """Test cases for user credentials CRUD operations."""

    def test_get_user_credentials_by_user_id_not_found(self, db: Session):
        """Test retrieving non-existent credentials returns None."""
        credentials = crud_user_credentials.get_user_credentials_by_user_id(db, 999)
        assert credentials is None

    def test_get_user_credentials_by_email_not_found(self, db: Session):
        """Test retrieving credentials by non-existent email returns None."""
        credentials = crud_user_credentials.get_user_credentials_by_email(db, "nonexistent@example.com")
        assert credentials is None

    def test_create_user_credentials(self, db: Session):
        """Test creating new user credentials."""
        # First create a user
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123",
            first_name="John",
            last_name="Doe",
            city="New York",
            country="USA",
            phone="+1-555-0123"
        )

        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        assert credentials.user_id == user.id
        assert credentials.email == "user@example.com"
        assert credentials.password_hash == "hashed_password_123"
        assert credentials.first_name == "John"
        assert credentials.last_name == "Doe"
        assert credentials.city == "New York"
        assert credentials.country == "USA"
        assert credentials.phone == "+1-555-0123"
        assert credentials.created_at is not None
        assert credentials.updated_at is not None

    def test_create_credentials_for_nonexistent_user(self, db: Session):
        """Test creating credentials for non-existent user raises ValueError."""
        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123"
        )

        with pytest.raises(ValueError, match="User with ID 999 does not exist"):
            crud_user_credentials.create_user_credentials(
                db, user_id=999, credentials_data=credentials_data
            )

    def test_create_duplicate_credentials_raises_integrity_error(self, db: Session):
        """Test creating duplicate credentials raises IntegrityError."""
        # Create user and first credentials
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123"
        )

        crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        # Attempt to create duplicate credentials
        with pytest.raises(IntegrityError):
            crud_user_credentials.create_user_credentials(
                db, user_id=user.id, credentials_data=credentials_data
            )

    def test_create_duplicate_email_raises_integrity_error(self, db: Session):
        """Test creating credentials with duplicate email raises IntegrityError."""
        # Create first user and credentials
        user1_data = UserCreate(name="User 1", email="user1@example.com")
        user1 = crud_user.create_user(db, user1_data)

        credentials1_data = UserCredentialsCreate(
            email="shared@example.com",
            password_hash="hashed_password_123"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user1.id, credentials_data=credentials1_data
        )

        # Create second user and attempt duplicate email
        user2_data = UserCreate(name="User 2", email="user2@example.com")
        user2 = crud_user.create_user(db, user2_data)

        credentials2_data = UserCredentialsCreate(
            email="shared@example.com",  # Same email
            password_hash="hashed_password_456"
        )

        with pytest.raises(IntegrityError):
            crud_user_credentials.create_user_credentials(
                db, user_id=user2.id, credentials_data=credentials2_data
            )

    def test_update_existing_credentials(self, db: Session):
        """Test updating existing credentials."""
        # Create user and initial credentials
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        initial_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123",
            first_name="John"
        )
        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=initial_data
        )
        initial_updated_time = credentials.updated_at

        # Update credentials
        update_data = UserCredentialsUpdate(
            first_name="Jane",
            last_name="Smith",
            city="Los Angeles"
        )
        updated_credentials = crud_user_credentials.update_user_credentials(
            db, user_id=user.id, credentials_data=update_data
        )

        assert updated_credentials is not None
        assert updated_credentials.user_id == user.id
        assert updated_credentials.first_name == "Jane"  # Updated
        assert updated_credentials.last_name == "Smith"  # New field
        assert updated_credentials.city == "Los Angeles"  # New field
        assert updated_credentials.email == "user@example.com"  # Unchanged
        assert updated_credentials.updated_at > initial_updated_time

    def test_update_nonexistent_credentials_returns_none(self, db: Session):
        """Test updating non-existent credentials returns None."""
        update_data = UserCredentialsUpdate(first_name="John")
        result = crud_user_credentials.update_user_credentials(
            db, user_id=999, credentials_data=update_data
        )
        assert result is None

    def test_update_email_to_existing_email_raises_integrity_error(self, db: Session):
        """Test updating email to existing email raises IntegrityError."""
        # Create two users with credentials
        user1_data = UserCreate(name="User 1", email="user1@example.com")
        user1 = crud_user.create_user(db, user1_data)
        credentials1_data = UserCredentialsCreate(
            email="user1@example.com", password_hash="hash1"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user1.id, credentials_data=credentials1_data
        )

        user2_data = UserCreate(name="User 2", email="user2@example.com")
        user2 = crud_user.create_user(db, user2_data)
        credentials2_data = UserCredentialsCreate(
            email="user2@example.com", password_hash="hash2"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user2.id, credentials_data=credentials2_data
        )

        # Try to update user2's email to user1's email
        update_data = UserCredentialsUpdate(email="user1@example.com")

        with pytest.raises(IntegrityError):
            crud_user_credentials.update_user_credentials(
                db, user_id=user2.id, credentials_data=update_data
            )

    def test_delete_user_credentials(self, db: Session):
        """Test deleting user credentials."""
        # Create user and credentials
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        # Delete credentials
        success = crud_user_credentials.delete_user_credentials(db, user_id=user.id)
        assert success is True

        # Verify deletion
        credentials = crud_user_credentials.get_user_credentials_by_user_id(db, user_id=user.id)
        assert credentials is None

    def test_delete_nonexistent_credentials(self, db: Session):
        """Test deleting non-existent credentials returns False."""
        success = crud_user_credentials.delete_user_credentials(db, user_id=999)
        assert success is False

    def test_invalid_user_id_validation(self, db: Session):
        """Test that invalid user_id values raise ValueError."""
        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123"
        )

        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            crud_user_credentials.create_user_credentials(
                db, user_id=0, credentials_data=credentials_data
            )

        update_data = UserCredentialsUpdate(first_name="John")
        with pytest.raises(ValueError, match="user_id must be a positive integer"):
            crud_user_credentials.update_user_credentials(
                db, user_id=-1, credentials_data=update_data
            )

    def test_email_normalization(self, db: Session):
        """Test that emails are normalized to lowercase."""
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="USER@EXAMPLE.COM",
            password_hash="hashed_password_123"
        )
        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        assert credentials.email == "user@example.com"

        # Test retrieval by email is case-insensitive
        found_credentials = crud_user_credentials.get_user_credentials_by_email(
            db, "USER@EXAMPLE.COM"
        )
        assert found_credentials is not None
        assert found_credentials.user_id == user.id

    def test_full_name_property(self, db: Session):
        """Test full_name property calculation."""
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        # Test with both names
        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123",
            first_name="John",
            last_name="Doe"
        )
        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )
        assert credentials.full_name == "John Doe"

        # Test with only first name
        update_data = UserCredentialsUpdate(last_name=None)
        updated_credentials = crud_user_credentials.update_user_credentials(
            db, user_id=user.id, credentials_data=update_data
        )
        assert updated_credentials.full_name == "John"

    def test_full_address_property(self, db: Session):
        """Test full_address property calculation."""
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123",
            address="123 Main St",
            city="New York",
            postal_code="10001",
            country="USA"
        )
        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        expected_address = "123 Main St\n10001 New York\nUSA"
        assert credentials.full_address == expected_address

    def test_full_address_property_missing_fields(self, db: Session):
        """full_address returns None when no address components provided."""
        user_data = UserCreate(name="Test User", email="testuser@example.com")
        user = crud_user.create_user(db, user_data)

        credentials_data = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hashed_password_123",
        )
        credentials = crud_user_credentials.create_user_credentials(
            db, user_id=user.id, credentials_data=credentials_data
        )

        assert credentials.full_address is None

    def test_search_user_credentials(self, db: Session):
        """Test searching credentials by various criteria."""
        # Create multiple users with credentials
        user1_data = UserCreate(name="User 1", email="user1@example.com")
        user1 = crud_user.create_user(db, user1_data)
        credentials1_data = UserCredentialsCreate(
            email="john.doe@example.com",
            password_hash="hash1",
            first_name="John",
            last_name="Doe",
            city="New York",
            country="USA"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user1.id, credentials_data=credentials1_data
        )

        user2_data = UserCreate(name="User 2", email="user2@example.com")
        user2 = crud_user.create_user(db, user2_data)
        credentials2_data = UserCredentialsCreate(
            email="jane.smith@example.com",
            password_hash="hash2",
            first_name="Jane",
            last_name="Smith",
            city="Los Angeles",
            country="USA"
        )
        crud_user_credentials.create_user_credentials(
            db, user_id=user2.id, credentials_data=credentials2_data
        )

        # Test search by first name
        john_results = crud_user_credentials.search_user_credentials(
            db, first_name_contains="John"
        )
        assert len(john_results) == 1
        assert john_results[0].first_name == "John"

        # Test search by city
        ny_results = crud_user_credentials.search_user_credentials(
            db, city="New York"
        )
        assert len(ny_results) == 1
        assert ny_results[0].city == "New York"

        # Test search by email
        doe_results = crud_user_credentials.search_user_credentials(
            db, email_contains="doe"
        )
        assert len(doe_results) == 1
        assert "doe" in doe_results[0].email


class TestUserCredentialsValidation:
    """Test cases for schema validation."""

    def test_email_validation(self):
        """Test email field validation and normalization."""
        # Valid email
        credentials = UserCredentialsCreate(
            email="USER@EXAMPLE.COM",
            password_hash="hash123"
        )
        assert credentials.email == "user@example.com"

    def test_phone_validation(self):
        """Test phone number validation."""
        # Valid phone numbers
        valid_phones = [
            "+1-555-0123",
            "(555) 123-4567",
            "555.123.4567",
            "+44 20 7946 0958",
            "5551234567"
        ]

        for phone in valid_phones:
            credentials = UserCredentialsCreate(
                email="user@example.com",
                password_hash="hash123",
                phone=phone
            )
            assert credentials.phone is not None

        # Invalid phone numbers
        invalid_phones = [
            "abc123",
            "123",  # Too short
            "12345678901234567890",  # Too long
            "555-ABC-1234"
        ]

        for phone in invalid_phones:
            with pytest.raises(ValueError):
                UserCredentialsCreate(
                    email="user@example.com",
                    password_hash="hash123",
                    phone=phone
                )

    def test_postal_code_normalization(self):
        """Test postal code validation and normalization."""
        credentials = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hash123",
            postal_code="  10001  "
        )
        assert credentials.postal_code == "10001"

    def test_text_field_normalization(self):
        """Test text field validation and normalization."""
        credentials = UserCredentialsCreate(
            email="user@example.com",
            password_hash="hash123",
            first_name="  john  ",
            last_name="  DOE  ",
            city="  new york  ",
            country="  usa  "
        )
        assert credentials.first_name == "John"
        assert credentials.last_name == "Doe"
        assert credentials.city == "New York"
        assert credentials.country == "Usa"