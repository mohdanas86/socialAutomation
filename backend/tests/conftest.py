"""
Pytest configuration and fixtures.

Sets up test environment and provides common fixtures.
"""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_user_id():
    """Return a mock MongoDB user ID."""
    return "507f1f77bcf86cd799439011"


@pytest.fixture
def mock_user_data():
    """Return mock user data."""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "email": "test@example.com",
        "name": "Test User",
        "linkedin_id": "DXgd1234567",
        "linkedin_access_token": "token_test_12345",
        "token_expiry": "2026-06-08T10:00:00",
        "created_at": "2026-05-08T10:00:00",
        "updated_at": "2026-05-08T10:00:00",
    }


@pytest.fixture
def mock_post_data():
    """Return mock post data."""
    return {
        "_id": "507f1f77bcf86cd799439012",
        "user_id": "507f1f77bcf86cd799439011",
        "content": "This is a test post about automation",
        "scheduled_time": "2026-05-08T15:00:00",
        "platform": "linkedin",
        "status": "scheduled",
        "retry_count": 0,
        "created_at": "2026-05-08T10:00:00",
    }


def pytest_configure(config):
    """Configure pytest."""
    # Set test environment
    os.environ['APP_ENV'] = 'test'
    os.environ['DEBUG'] = 'true'
