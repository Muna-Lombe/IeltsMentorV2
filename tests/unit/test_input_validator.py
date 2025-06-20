import pytest
from utils.input_validator import InputValidator

def test_validate_user_id_valid():
    """Test that a valid user ID is returned as is."""
    assert InputValidator.validate_user_id(123456789) == 123456789

def test_validate_user_id_zero():
    """Test that a user ID of 0 is considered invalid."""
    assert InputValidator.validate_user_id(0) is None

def test_validate_user_id_negative():
    """Test that a negative user ID is considered invalid."""
    assert InputValidator.validate_user_id(-12345) is None

def test_validate_user_id_non_integer():
    """Test that a non-integer input is considered invalid."""
    assert InputValidator.validate_user_id("not_an_id") is None
    assert InputValidator.validate_user_id(None) is None
    assert InputValidator.validate_user_id(123.45) is None 