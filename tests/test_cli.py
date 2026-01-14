"""Tests for CLI module."""

import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from wit.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file."""
    config = tmp_path / "wit.yaml"
    config.write_text("""
base_url: https://example.com
output_dir: content
pages:
  urls:
    - /
    - /about
""")
    return config


class TestInit:
    """Tests for init command."""
    
    def test_init_creates_config(self, runner, tmp_path):
        """Test that init creates a config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["init", "--base-url", "https://example.com"])
            
            assert result.exit_code == 0
            assert Path("wit.yaml").exists()
    
    def test_init_custom_output(self, runner, tmp_path):
        """Test init with custom output path."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, [
                "init", 
                "--base-url", "https://example.com",
                "--output", "custom.yaml"
            ])
            
            assert result.exit_code == 0
            assert Path("custom.yaml").exists()
    
    def test_init_overwrites_with_confirm(self, runner, tmp_path):
        """Test init overwrites existing file with confirmation."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("existing")
            
            result = runner.invoke(cli, [
                "init", 
                "--base-url", "https://example.com"
            ], input="y\n")
            
            assert result.exit_code == 0
            assert "https://example.com" in Path("wit.yaml").read_text()


class TestList:
    """Tests for list command."""
    
    def test_list_pages(self, runner, tmp_path):
        """Test listing pages."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
base_url: https://example.com
pages:
  urls:
    - /
    - /about
    - /contact
""")
            result = runner.invoke(cli, ["list"])
            
            assert result.exit_code == 0
            assert "3 pages" in result.output
            assert "https://example.com/" in result.output
            assert "https://example.com/about" in result.output
    
    def test_list_custom_config(self, runner, tmp_path):
        """Test list with custom config path."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("custom.yaml").write_text("""
base_url: https://example.com
pages:
  urls:
    - /
""")
            result = runner.invoke(cli, ["list", "--config", "custom.yaml"])
            
            assert result.exit_code == 0
    
    def test_list_missing_config(self, runner, tmp_path):
        """Test list with missing config file."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, ["list"])
            
            assert result.exit_code == 1
            assert "not found" in result.output


class TestScrapeUrl:
    """Tests for scrape-url command."""
    
    def test_scrape_url_missing_output(self, runner):
        """Test scrape-url without output option."""
        result = runner.invoke(cli, ["scrape-url", "https://example.com"])
        
        # Should fail because --output is required
        assert result.exit_code != 0


class TestVerboseQuiet:
    """Tests for verbose and quiet flags."""
    
    def test_verbose_flag(self, runner, tmp_path):
        """Test verbose flag."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
base_url: https://example.com
pages:
  urls:
    - /
""")
            result = runner.invoke(cli, ["-v", "list"])
            
            assert result.exit_code == 0
    
    def test_quiet_flag(self, runner, tmp_path):
        """Test quiet flag."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
base_url: https://example.com
pages:
  urls:
    - /
""")
            result = runner.invoke(cli, ["-q", "list"])
            
            assert result.exit_code == 0


class TestVersion:
    """Tests for version option."""
    
    def test_version(self, runner):
        """Test version option."""
        result = runner.invoke(cli, ["--version"])
        
        assert result.exit_code == 0
        assert "version" in result.output.lower() or "1.0" in result.output
