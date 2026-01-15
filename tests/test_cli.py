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
    
    def test_init_multi_site(self, runner, tmp_path):
        """Test init with --multi-site flag."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(cli, [
                "init", 
                "--base-url", "https://example.com",
                "--multi-site"
            ])
            
            assert result.exit_code == 0
            config_content = Path("wit.yaml").read_text()
            assert "sites:" in config_content


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
    
    def test_list_multi_site(self, runner, tmp_path):
        """Test listing pages from multiple sites."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
sites:
  - name: docs
    base_url: https://docs.example.com
    pages:
      urls:
        - /
        - /guide
  - name: blog
    base_url: https://blog.example.com
    pages:
      urls:
        - /
""")
            result = runner.invoke(cli, ["list"])
            
            assert result.exit_code == 0
            assert "docs" in result.output
            assert "blog" in result.output
            assert "Total: 3 pages" in result.output
    
    def test_list_site_filter(self, runner, tmp_path):
        """Test listing pages with site filter."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
sites:
  - name: docs
    base_url: https://docs.example.com
    pages:
      urls:
        - /
        - /guide
  - name: blog
    base_url: https://blog.example.com
    pages:
      urls:
        - /
""")
            result = runner.invoke(cli, ["list", "--site", "docs"])
            
            assert result.exit_code == 0
            assert "docs.example.com" in result.output
            # Should only show docs site pages
            assert "2 pages" in result.output
    
    def test_list_invalid_site_filter(self, runner, tmp_path):
        """Test listing with invalid site filter."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
sites:
  - name: docs
    base_url: https://docs.example.com
    pages:
      urls:
        - /
""")
            result = runner.invoke(cli, ["list", "--site", "nonexistent"])
            
            assert result.exit_code == 1
            assert "No sites found" in result.output


class TestSites:
    """Tests for sites command."""
    
    def test_list_sites(self, runner, tmp_path):
        """Test listing configured sites."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
sites:
  - name: docs
    base_url: https://docs.example.com
    output_dir: content/docs
  - name: blog
    base_url: https://blog.example.com
    output_dir: content/blog
""")
            result = runner.invoke(cli, ["sites"])
            
            assert result.exit_code == 0
            assert "docs" in result.output
            assert "blog" in result.output
            assert "https://docs.example.com" in result.output
            assert "https://blog.example.com" in result.output
    
    def test_list_sites_single_site(self, runner, tmp_path):
        """Test listing sites for single-site config."""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path("wit.yaml").write_text("""
base_url: https://example.com
output_dir: content
""")
            result = runner.invoke(cli, ["sites"])
            
            assert result.exit_code == 0
            assert "https://example.com" in result.output


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
