"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest

from wit.config import WitConfig, load_config, create_default_config


class TestWitConfig:
    """Tests for WitConfig dataclass."""
    
    def test_basic_config(self):
        """Test creating a basic config."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.base_url == "https://example.com"
        assert config.output_dir == Path("content")
        assert config.scraping["delay"] == 1.0
        assert config.scraping["javascript"] is False
    
    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from base_url."""
        config = WitConfig(base_url="https://example.com/")
        assert config.base_url == "https://example.com"
    
    def test_output_dir_string_to_path(self):
        """Test that output_dir is converted to Path."""
        config = WitConfig(base_url="https://example.com", output_dir="my-output")
        assert isinstance(config.output_dir, Path)
        assert config.output_dir == Path("my-output")
    
    def test_default_selectors(self):
        """Test default selectors are set."""
        config = WitConfig(base_url="https://example.com")
        
        assert "main" in config.selectors["content"]
        assert "article" in config.selectors["content"]
        assert "nav" in config.selectors["remove"]
        assert config.selectors["title"] == "h1"
    
    def test_custom_selectors(self):
        """Test custom selectors are preserved."""
        config = WitConfig(
            base_url="https://example.com",
            selectors={"content": [".custom-content"], "title": "h2"}
        )
        
        assert config.selectors["content"] == [".custom-content"]
        assert config.selectors["title"] == "h2"
    
    def test_default_git_settings(self):
        """Test default git settings."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.git["author_name"] == "wit[bot]"
        assert "wit[bot]" in config.git["author_email"]
    
    def test_default_metadata_settings(self):
        """Test default metadata settings."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.metadata["include_source_url"] is True
        assert config.metadata["include_timestamp"] is True
        assert config.metadata["include_title"] is True


class TestLoadConfig:
    """Tests for load_config function."""
    
    def test_load_basic_config(self, tmp_path):
        """Test loading a basic config file."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
base_url: https://example.com
output_dir: docs
""")
        
        config = load_config(config_file)
        
        assert config.base_url == "https://example.com"
        assert config.output_dir == Path("docs")
    
    def test_load_config_missing_file(self, tmp_path):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")
    
    def test_load_config_missing_base_url(self, tmp_path):
        """Test loading config without required base_url."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("output_dir: docs\n")
        
        with pytest.raises(ValueError, match="base_url"):
            load_config(config_file)
    
    def test_load_config_with_pages(self, tmp_path):
        """Test loading config with page discovery settings."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
base_url: https://example.com
pages:
  urls:
    - /
    - /about
  sitemap: /sitemap.xml
""")
        
        config = load_config(config_file)
        
        assert "/" in config.pages["urls"]
        assert config.pages["sitemap"] == "/sitemap.xml"
    
    def test_load_config_with_crawl(self, tmp_path):
        """Test loading config with crawl settings."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
base_url: https://example.com
pages:
  crawl:
    start: /docs
    max_depth: 3
    max_pages: 100
    include:
      - /docs/*
    exclude:
      - /docs/v1/*
""")
        
        config = load_config(config_file)
        
        assert config.pages["crawl"]["start"] == "/docs"
        assert config.pages["crawl"]["max_depth"] == 3
        assert "/docs/*" in config.pages["crawl"]["include"]
    
    def test_load_config_string_path(self, tmp_path):
        """Test loading config with string path."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("base_url: https://example.com\n")
        
        config = load_config(str(config_file))
        assert config.base_url == "https://example.com"


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""
    
    def test_create_default_config(self):
        """Test creating a default config."""
        config = create_default_config("https://example.com")
        
        assert "base_url: https://example.com" in config
        assert "output_dir: content" in config
        assert "selectors:" in config
        assert "scraping:" in config
        assert "git:" in config
    
    def test_default_config_is_valid_yaml(self, tmp_path):
        """Test that generated config is valid YAML."""
        config_content = create_default_config("https://example.com")
        
        config_file = tmp_path / "wit.yaml"
        config_file.write_text(config_content)
        
        # Should load without error
        config = load_config(config_file)
        assert config.base_url == "https://example.com"
