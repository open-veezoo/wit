"""Tests for config module."""

import tempfile
from pathlib import Path

import pytest

from wit.config import WitConfig, SiteConfig, load_config, create_default_config, _derive_site_name


class TestSiteConfig:
    """Tests for SiteConfig dataclass."""
    
    def test_basic_site_config(self):
        """Test creating a basic site config."""
        site = SiteConfig(name="example", base_url="https://example.com")
        
        assert site.name == "example"
        assert site.base_url == "https://example.com"
        assert site.output_dir == Path("content")
    
    def test_site_base_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from base_url."""
        site = SiteConfig(name="example", base_url="https://example.com/")
        assert site.base_url == "https://example.com"
    
    def test_site_default_selectors(self):
        """Test default selectors are set on site."""
        site = SiteConfig(name="example", base_url="https://example.com")
        
        assert "main" in site.selectors["content"]
        assert "nav" in site.selectors["remove"]


class TestDeriveSiteName:
    """Tests for site name derivation."""
    
    def test_simple_domain(self):
        """Test deriving name from simple domain."""
        assert _derive_site_name("https://example.com") == "example"
    
    def test_subdomain(self):
        """Test deriving name from subdomain."""
        assert _derive_site_name("https://docs.example.com") == "docs-example"
    
    def test_domain_with_port(self):
        """Test deriving name from domain with port."""
        assert _derive_site_name("https://localhost:8000") == "localhost"


class TestWitConfig:
    """Tests for WitConfig dataclass."""
    
    def test_basic_config(self):
        """Test creating a basic config (legacy single-site)."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.base_url == "https://example.com"
        assert len(config.sites) == 1
        assert config.sites[0].base_url == "https://example.com"
    
    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slashes are removed from base_url."""
        config = WitConfig(base_url="https://example.com/")
        assert config.base_url == "https://example.com"
        assert config.sites[0].base_url == "https://example.com"
    
    def test_output_dir_string_to_path(self):
        """Test that output_dir is converted to Path."""
        config = WitConfig(base_url="https://example.com", output_dir="my-output")
        assert isinstance(config.output_dir, Path)
        assert config.output_dir == Path("my-output")
        assert config.sites[0].output_dir == Path("my-output")
    
    def test_default_selectors(self):
        """Test default selectors are set (via site)."""
        config = WitConfig(base_url="https://example.com")
        
        # Check via site
        assert "main" in config.sites[0].selectors["content"]
        assert "article" in config.sites[0].selectors["content"]
        assert "nav" in config.sites[0].selectors["remove"]
        assert config.sites[0].selectors["title"] == "h1"
    
    def test_custom_selectors(self):
        """Test custom selectors are preserved."""
        config = WitConfig(
            base_url="https://example.com",
            selectors={"content": [".custom-content"], "title": "h2"}
        )
        
        assert config.sites[0].selectors["content"] == [".custom-content"]
        assert config.sites[0].selectors["title"] == "h2"
    
    def test_default_git_settings(self):
        """Test default git settings."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.git["author_name"] == "wit[bot]"
        assert "wit[bot]" in config.git["author_email"]
    
    def test_default_metadata_settings(self):
        """Test default metadata settings (via site)."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.sites[0].metadata["include_source_url"] is True
        assert config.sites[0].metadata["include_timestamp"] is True
        assert config.sites[0].metadata["include_title"] is True
    
    def test_default_scraping_wait_until(self):
        """Test default wait_until setting for JS rendering."""
        config = WitConfig(base_url="https://example.com")
        
        assert config.sites[0].scraping["wait_until"] == "load"
    
    def test_custom_scraping_wait_until(self):
        """Test custom wait_until setting is preserved."""
        config = WitConfig(
            base_url="https://example.com",
            scraping={"wait_until": "networkidle"}
        )
        
        assert config.sites[0].scraping["wait_until"] == "networkidle"
    
    def test_custom_scraping_wait_until_domcontentloaded(self):
        """Test domcontentloaded wait_until setting."""
        config = WitConfig(
            base_url="https://example.com",
            scraping={"wait_until": "domcontentloaded"}
        )
        
        assert config.sites[0].scraping["wait_until"] == "domcontentloaded"
    
    def test_multi_site_config(self):
        """Test creating a multi-site config directly."""
        sites = [
            SiteConfig(name="site1", base_url="https://site1.com"),
            SiteConfig(name="site2", base_url="https://site2.com"),
        ]
        config = WitConfig(sites=sites)
        
        assert len(config.sites) == 2
        assert config.site_names == ["site1", "site2"]
    
    def test_get_site(self):
        """Test getting a site by name."""
        sites = [
            SiteConfig(name="site1", base_url="https://site1.com"),
            SiteConfig(name="site2", base_url="https://site2.com"),
        ]
        config = WitConfig(sites=sites)
        
        site = config.get_site("site1")
        assert site is not None
        assert site.base_url == "https://site1.com"
        
        assert config.get_site("nonexistent") is None
    
    def test_get_sites_filtered(self):
        """Test getting filtered sites."""
        sites = [
            SiteConfig(name="site1", base_url="https://site1.com"),
            SiteConfig(name="site2", base_url="https://site2.com"),
            SiteConfig(name="site3", base_url="https://site3.com"),
        ]
        config = WitConfig(sites=sites)
        
        filtered = config.get_sites(["site1", "site3"])
        assert len(filtered) == 2
        assert filtered[0].name == "site1"
        assert filtered[1].name == "site3"
    
    def test_get_sites_all(self):
        """Test getting all sites when no filter."""
        sites = [
            SiteConfig(name="site1", base_url="https://site1.com"),
            SiteConfig(name="site2", base_url="https://site2.com"),
        ]
        config = WitConfig(sites=sites)
        
        all_sites = config.get_sites(None)
        assert len(all_sites) == 2


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
        # Check site was created
        assert len(config.sites) == 1
        assert config.sites[0].base_url == "https://example.com"
    
    def test_load_config_missing_file(self, tmp_path):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yaml")
    
    def test_load_config_missing_base_url(self, tmp_path):
        """Test loading config without required base_url or sites."""
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
        # Also check via site
        assert "/" in config.sites[0].pages["urls"]
    
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
    
    def test_load_config_with_wait_until(self, tmp_path):
        """Test loading config with custom wait_until setting."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
base_url: https://example.com
scraping:
  javascript: true
  wait_until: domcontentloaded
""")
        
        config = load_config(config_file)
        
        assert config.sites[0].scraping["javascript"] is True
        assert config.sites[0].scraping["wait_until"] == "domcontentloaded"
    
    def test_load_multi_site_config(self, tmp_path):
        """Test loading a multi-site config file."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites:
  - name: docs
    base_url: https://docs.example.com
    pages:
      urls:
        - /
        - /guide
  - name: blog
    base_url: https://blog.example.com
    output_dir: content/blog
    pages:
      sitemap: /sitemap.xml

git:
  author_name: custom-bot
""")
        
        config = load_config(config_file)
        
        assert len(config.sites) == 2
        assert config.site_names == ["docs", "blog"]
        
        docs_site = config.get_site("docs")
        assert docs_site.base_url == "https://docs.example.com"
        assert docs_site.output_dir == Path("content/docs")  # Auto-derived
        
        blog_site = config.get_site("blog")
        assert blog_site.base_url == "https://blog.example.com"
        assert blog_site.output_dir == Path("content/blog")
        
        # Check global git settings
        assert config.git["author_name"] == "custom-bot"
    
    def test_load_multi_site_with_global_settings(self, tmp_path):
        """Test that global settings are inherited by sites."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites:
  - base_url: https://site1.com
  - base_url: https://site2.com
    selectors:
      content: [".custom"]

selectors:
  content: [".global-content"]
  remove: [".global-remove"]

scraping:
  delay: 2.0
""")
        
        config = load_config(config_file)
        
        # Site 1 should inherit global settings
        site1 = config.sites[0]
        assert site1.selectors["content"] == [".global-content"]
        assert site1.scraping["delay"] == 2.0
        
        # Site 2 should override content but inherit remove
        site2 = config.sites[1]
        assert site2.selectors["content"] == [".custom"]
        assert site2.selectors["remove"] == [".global-remove"]
        assert site2.scraping["delay"] == 2.0
    
    def test_load_multi_site_auto_derive_name(self, tmp_path):
        """Test that site names are auto-derived from URLs."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites:
  - base_url: https://example.com
  - base_url: https://docs.another.org
""")
        
        config = load_config(config_file)
        
        assert config.sites[0].name == "example"
        assert config.sites[1].name == "docs-another"
    
    def test_load_multi_site_duplicate_name_error(self, tmp_path):
        """Test that duplicate site names raise an error."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites:
  - name: mysite
    base_url: https://site1.com
  - name: mysite
    base_url: https://site2.com
""")
        
        with pytest.raises(ValueError, match="Duplicate site name"):
            load_config(config_file)
    
    def test_load_multi_site_empty_sites_error(self, tmp_path):
        """Test that empty sites list raises an error."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites: []
""")
        
        with pytest.raises(ValueError, match="cannot be empty"):
            load_config(config_file)
    
    def test_load_multi_site_missing_base_url_error(self, tmp_path):
        """Test that site without base_url raises an error."""
        config_file = tmp_path / "wit.yaml"
        config_file.write_text("""
sites:
  - name: mysite
    pages:
      urls: ["/"]
""")
        
        with pytest.raises(ValueError, match="base_url"):
            load_config(config_file)


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""
    
    def test_create_default_config(self):
        """Test creating a default single-site config."""
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
    
    def test_create_multi_site_config(self):
        """Test creating a multi-site config."""
        config = create_default_config("https://docs.example.com", multi_site=True)
        
        assert "sites:" in config
        assert "base_url: https://docs.example.com" in config
        assert "content/docs-example" in config  # Auto-derived output dir
    
    def test_multi_site_config_is_valid_yaml(self, tmp_path):
        """Test that generated multi-site config is valid YAML."""
        config_content = create_default_config("https://example.com", multi_site=True)
        
        config_file = tmp_path / "wit.yaml"
        config_file.write_text(config_content)
        
        # Should load without error
        config = load_config(config_file)
        assert len(config.sites) >= 1
        assert config.sites[0].base_url == "https://example.com"
