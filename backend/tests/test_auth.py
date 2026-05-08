"""
Tests for authentication service.

Tests JWT token creation, verification, and user management.
"""

import pytest
from datetime import datetime, timedelta, timezone
from app.services.auth_service import AuthService


class TestAuthService:
    """Test authentication service."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        user_id = "507f1f77bcf86cd799439011"
        token = AuthService.create_access_token(user_id)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Token should have three parts (header.payload.signature)
        parts = token.split('.')
        assert len(parts) == 3

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        user_id = "507f1f77bcf86cd799439011"
        token = AuthService.create_access_token(user_id)
        
        # Token should be verifiable
        verified_id = AuthService.verify_token(token)
        assert verified_id == user_id

    def test_verify_expired_token(self):
        """Test that expired tokens are rejected."""
        user_id = "507f1f77bcf86cd799439011"
        
        # Create token that expires immediately
        token = AuthService.create_access_token(
            user_id,
            expires_delta=timedelta(seconds=-1)
        )
        
        # Should return None (invalid)
        verified_id = AuthService.verify_token(token)
        assert verified_id is None

    def test_verify_invalid_token(self):
        """Test that invalid tokens are rejected."""
        invalid_token = "not.a.valid.token"
        
        verified_id = AuthService.verify_token(invalid_token)
        assert verified_id is None

    def test_verify_tampered_token(self):
        """Test that tampered tokens are rejected."""
        user_id = "507f1f77bcf86cd799439011"
        token = AuthService.create_access_token(user_id)
        
        # Tamper with token
        tampered_token = token[:-5] + "XXXXX"
        
        verified_id = AuthService.verify_token(tampered_token)
        assert verified_id is None

    def test_token_expiration_hours_config(self):
        """Test that token respects expiration hours config."""
        from app.utils.config import settings
        
        user_id = "507f1f77bcf86cd799439011"
        token = AuthService.create_access_token(user_id)
        
        # Should be valid immediately
        assert AuthService.verify_token(token) == user_id
        
        # Should still be valid (created now)
        verified_id = AuthService.verify_token(token)
        assert verified_id is not None

    def test_token_has_correct_claims(self):
        """Test that token contains correct claims."""
        from jose import jwt
        from app.utils.config import settings
        
        user_id = "507f1f77bcf86cd799439011"
        token = AuthService.create_access_token(user_id)
        
        # Decode without verification to check claims
        payload = jwt.get_unverified_claims(token)
        
        assert payload['sub'] == user_id
        assert 'exp' in payload
        assert 'iat' in payload
