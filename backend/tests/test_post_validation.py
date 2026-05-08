"""
Tests for post service validation.

Tests post content validation and business logic.
"""

import pytest
from app.services.post_service import PostService


class TestPostValidation:
    """Test post content validation."""

    def test_valid_post_content(self):
        """Test that valid content passes validation."""
        content = "This is a valid post about automation"
        
        # Should not raise exception
        PostService.validate_post_content(content)

    def test_empty_content_rejected(self):
        """Test that empty content is rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            PostService.validate_post_content("")

    def test_whitespace_only_rejected(self):
        """Test that whitespace-only content is rejected."""
        with pytest.raises(ValueError, match="only whitespace"):
            PostService.validate_post_content("   \n\t   ")

    def test_too_short_content_rejected(self):
        """Test that very short content is rejected."""
        with pytest.raises(ValueError, match="at least 5 characters"):
            PostService.validate_post_content("Hi")

    def test_too_long_content_rejected(self):
        """Test that content exceeding 3000 chars is rejected."""
        long_content = "a" * 3001
        
        with pytest.raises(ValueError, match="exceeds 3000"):
            PostService.validate_post_content(long_content)

    def test_all_caps_spam_rejected(self):
        """Test that all-caps content is detected as spam."""
        spam_content = "THIS IS A TEST " * 10  # All caps
        
        with pytest.raises(ValueError, match="spam"):
            PostService.validate_post_content(spam_content)

    def test_too_many_urls_rejected(self):
        """Test that too many URLs are rejected."""
        content = "Check these http://url1.com http://url2.com http://url3.com http://url4.com"
        
        with pytest.raises(ValueError, match="too many URLs"):
            PostService.validate_post_content(content)

    def test_valid_content_with_urls(self):
        """Test that valid content with 1-3 URLs passes."""
        content = "Check this http://example.com for more info"
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_content_with_multiple_urls(self):
        """Test that content with up to 3 URLs passes."""
        content = "Links: http://url1.com http://url2.com http://url3.com more text"
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_content_with_mixed_case(self):
        """Test that mixed case content passes."""
        content = "This Is A Valid Post With Mixed Case Content"
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_content_with_hashtags(self):
        """Test that hashtags don't interfere with validation."""
        content = "Great day at work! #automation #python #tech"
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_content_with_emojis(self):
        """Test that emojis are allowed."""
        content = "Excited about this project 🚀 #automation"
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_max_length_content(self):
        """Test that content exactly at 3000 chars is accepted."""
        content = "a" * 3000
        PostService.validate_post_content(content)  # Should not raise

    def test_valid_content_just_over_minimum(self):
        """Test that content with 5 chars is accepted."""
        content = "valid"  # Exactly 5 chars
        PostService.validate_post_content(content)  # Should not raise

    def test_none_content_rejected(self):
        """Test that None content is rejected."""
        with pytest.raises((ValueError, AttributeError)):
            PostService.validate_post_content(None)


class TestPostEdgeCases:
    """Test edge cases in post validation."""

    def test_content_with_special_characters(self):
        """Test content with special characters."""
        content = "Testing with special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        PostService.validate_post_content(content)  # Should not raise

    def test_content_with_newlines(self):
        """Test that multi-line content is allowed."""
        content = "Line 1\nLine 2\nLine 3 with content that's valid"
        PostService.validate_post_content(content)  # Should not raise

    def test_content_with_tabs(self):
        """Test that tabs are allowed."""
        content = "Header\tValue\tAnother\tTest"
        PostService.validate_post_content(content)  # Should not raise

    def test_very_long_valid_content(self):
        """Test that very long but valid content passes."""
        # Content with varied case, no spam patterns
        content = (
            "This Is A Very Long Post That Discusses Various Topics "
            "Related To Automation And Technology. It Contains Multiple "
            "Sentences And Paragraphs But Maintains Proper Capitalization "
            "And Does Not Contain Any Spam Patterns Or Too Many URLs. " * 5
        )
        
        if len(content) <= 3000:
            PostService.validate_post_content(content)  # Should not raise
        else:
            with pytest.raises(ValueError):
                PostService.validate_post_content(content)
