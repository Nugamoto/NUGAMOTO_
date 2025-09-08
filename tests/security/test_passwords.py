import pytest

from backend.security.passwords import hash_password, verify_password, is_password_hashed


@pytest.mark.parametrize("password", [
    "password123",
    "",
    "pässwörd!",
])
def test_hash_and_verify_password(password):
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password(password + "x", hashed) is False


@pytest.mark.parametrize("value, expected", [
    (hash_password("example"), True),
    ("plain", False),
    (None, False),
])
def test_is_password_hashed(value, expected):
    assert is_password_hashed(value) is expected
