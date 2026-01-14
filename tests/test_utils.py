"""Tests for utils module."""

from pathlib import Path

import pytest

from wit.utils import (
    normalize_url,
    url_to_filepath,
    sanitize_filename,
    is_same_domain,
    matches_pattern,
    extract_path,
    format_commit_message,
)


class TestNormalizeUrl:
    """Tests for normalize_url function."""
    
    def test_relative_url_with_slash(self):
        """Test normalizing relative URL with leading slash."""
        result = normalize_url("/about", "https://example.com")
        assert result == "https://example.com/about"
    
    def test_relative_url_without_slash(self):
        """Test normalizing relative URL without leading slash."""
        result = normalize_url("about", "https://example.com")
        assert result == "https://example.com/about"
    
    def test_absolute_url(self):
        """Test normalizing absolute URL."""
        result = normalize_url("https://other.com/page", "https://example.com")
        assert result == "https://other.com/page"
    
    def test_base_url_with_path(self):
        """Test normalizing with base URL that has a path."""
        result = normalize_url("/docs/intro", "https://example.com/app")
        assert result == "https://example.com/docs/intro"


class TestUrlToFilepath:
    """Tests for url_to_filepath function."""
    
    def test_root_url(self):
        """Test converting root URL."""
        result = url_to_filepath(
            "https://example.com/",
            "https://example.com",
            Path("content")
        )
        assert result == Path("content/index.md")
    
    def test_simple_path(self):
        """Test converting simple path."""
        result = url_to_filepath(
            "https://example.com/about",
            "https://example.com",
            Path("content")
        )
        assert result == Path("content/about.md")
    
    def test_nested_path(self):
        """Test converting nested path."""
        result = url_to_filepath(
            "https://example.com/docs/getting-started",
            "https://example.com",
            Path("content")
        )
        assert result == Path("content/docs/getting-started.md")
    
    def test_deep_nested_path(self):
        """Test converting deeply nested path."""
        result = url_to_filepath(
            "https://example.com/blog/2024/01/post",
            "https://example.com",
            Path("output")
        )
        assert result == Path("output/blog/2024/01/post.md")
    
    def test_html_extension_removed(self):
        """Test that .html extension is removed."""
        result = url_to_filepath(
            "https://example.com/page.html",
            "https://example.com",
            Path("content")
        )
        assert result == Path("content/page.md")
    
    def test_trailing_slash(self):
        """Test path with trailing slash."""
        result = url_to_filepath(
            "https://example.com/docs/",
            "https://example.com",
            Path("content")
        )
        assert result == Path("content/docs/index.md")


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""
    
    def test_normal_filename(self):
        """Test sanitizing normal filename."""
        assert sanitize_filename("about") == "about"
    
    def test_filename_with_special_chars(self):
        """Test sanitizing filename with special characters."""
        result = sanitize_filename("file:name?test")
        assert ":" not in result
        assert "?" not in result
    
    def test_empty_filename(self):
        """Test sanitizing empty filename."""
        assert sanitize_filename("") == "unnamed"
    
    def test_filename_with_dashes(self):
        """Test sanitizing filename with multiple dashes."""
        result = sanitize_filename("file---name")
        assert result == "file-name"


class TestIsSameDomain:
    """Tests for is_same_domain function."""
    
    def test_same_domain(self):
        """Test URLs on same domain."""
        assert is_same_domain(
            "https://example.com/page",
            "https://example.com"
        ) is True
    
    def test_different_domain(self):
        """Test URLs on different domains."""
        assert is_same_domain(
            "https://other.com/page",
            "https://example.com"
        ) is False
    
    def test_relative_url(self):
        """Test relative URL (no netloc)."""
        assert is_same_domain("/page", "https://example.com") is True
    
    def test_subdomain(self):
        """Test subdomain is considered different."""
        assert is_same_domain(
            "https://www.example.com/page",
            "https://example.com"
        ) is False


class TestMatchesPattern:
    """Tests for matches_pattern function."""
    
    def test_exact_match(self):
        """Test exact path match."""
        assert matches_pattern("/about", "/about") is True
    
    def test_no_match(self):
        """Test non-matching path."""
        assert matches_pattern("/about", "/contact") is False
    
    def test_wildcard_match(self):
        """Test wildcard pattern match."""
        assert matches_pattern("/docs/intro", "/docs/*") is True
    
    def test_wildcard_no_match(self):
        """Test wildcard pattern non-match."""
        assert matches_pattern("/blog/post", "/docs/*") is False
    
    def test_deep_wildcard(self):
        """Test deep wildcard pattern."""
        assert matches_pattern("/docs/guide/intro", "/docs/*") is True


class TestExtractPath:
    """Tests for extract_path function."""
    
    def test_full_url(self):
        """Test extracting path from full URL."""
        assert extract_path("https://example.com/about") == "/about"
    
    def test_relative_path(self):
        """Test extracting from relative path."""
        assert extract_path("/about") == "/about"
    
    def test_root_path(self):
        """Test extracting root path."""
        assert extract_path("https://example.com") == ""
    
    def test_path_with_query(self):
        """Test extracting path ignoring query string."""
        assert extract_path("https://example.com/search?q=test") == "/search"


class TestFormatCommitMessage:
    """Tests for format_commit_message function."""
    
    def test_single_file(self):
        """Test formatting message with single file."""
        result = format_commit_message(
            "Update {changed_count} page(s): {changed_files}",
            ["about.md"]
        )
        assert "1 page(s)" in result
        assert "about.md" in result
    
    def test_multiple_files(self):
        """Test formatting message with multiple files."""
        result = format_commit_message(
            "Update {changed_count} page(s): {changed_files}",
            ["about.md", "contact.md", "pricing.md"]
        )
        assert "3 page(s)" in result
        assert "about.md" in result
        assert "pricing.md" in result
    
    def test_many_files_truncated(self):
        """Test formatting message with many files (truncated)."""
        files = [f"page{i}.md" for i in range(10)]
        result = format_commit_message(
            "Update {changed_count} page(s): {changed_files}",
            files
        )
        assert "10 page(s)" in result
        assert "+5 more" in result
