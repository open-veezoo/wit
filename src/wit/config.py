"""Configuration loading and validation for wit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
import yaml


def _get_default_selectors(custom: dict) -> dict:
    """Get selectors with defaults applied."""
    return {
        "content": custom.get("content", ["main", "article", ".content", "#main-content", "body"]),
        "remove": custom.get("remove", ["nav", "footer", "header", "script", "style", "noscript"]),
        "title": custom.get("title", "h1"),
    }


def _get_default_scraping(custom: dict) -> dict:
    """Get scraping config with defaults applied."""
    return {
        "delay": custom.get("delay", 1.0),
        "timeout": custom.get("timeout", 30),
        "user_agent": custom.get("user_agent", "wit/1.0 (+https://github.com/open-veezoo/wit)"),
        "javascript": custom.get("javascript", False),
        "retries": custom.get("retries", 3),
        "wait_until": custom.get("wait_until", "load"),
        "wait_delay": custom.get("wait_delay", 0),
    }


def _get_default_markdown(custom: dict) -> dict:
    """Get markdown config with defaults applied."""
    return {
        "heading_style": custom.get("heading_style", "atx"),
        "strip_links": custom.get("strip_links", False),
        "include_images": custom.get("include_images", True),
        "code_language": custom.get("code_language", "auto"),
    }


def _get_default_metadata(custom: dict) -> dict:
    """Get metadata config with defaults applied."""
    return {
        "include_source_url": custom.get("include_source_url", True),
        "include_timestamp": custom.get("include_timestamp", True),
        "include_title": custom.get("include_title", True),
    }


def _get_default_git(custom: dict) -> dict:
    """Get git config with defaults applied."""
    return {
        "author_name": custom.get("author_name", "wit[bot]"),
        "author_email": custom.get("author_email", "wit[bot]@users.noreply.github.com"),
        "message_template": custom.get("message_template", "Update {changed_count} page(s): {changed_files}"),
    }


def _derive_site_name(base_url: str) -> str:
    """Derive a site name from base URL."""
    parsed = urlparse(base_url)
    # Use domain without TLD as site name
    domain = parsed.netloc.split(":")[0]  # Remove port if present
    parts = domain.split(".")
    # Handle cases like "docs.example.com" -> "docs-example"
    if len(parts) > 2:
        return "-".join(parts[:-1])
    elif len(parts) == 2:
        return parts[0]
    return domain


@dataclass
class SiteConfig:
    """Configuration for a single site."""
    
    name: str
    base_url: str
    output_dir: Path = field(default_factory=lambda: Path("content"))
    pages: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    scraping: dict = field(default_factory=dict)
    markdown: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize site configuration."""
        # Ensure base_url doesn't have trailing slash
        self.base_url = self.base_url.rstrip("/")
        
        # Convert output_dir to Path if string
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Apply defaults
        self.selectors = _get_default_selectors(self.selectors)
        self.scraping = _get_default_scraping(self.scraping)
        self.markdown = _get_default_markdown(self.markdown)
        self.metadata = _get_default_metadata(self.metadata)


@dataclass
class WitConfig:
    """Configuration for wit scraper with multi-site support."""
    
    sites: list[SiteConfig] = field(default_factory=list)
    git: dict = field(default_factory=dict)
    
    # Legacy single-site fields (for backwards compatibility)
    base_url: str | None = None
    output_dir: Path | None = None
    pages: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    scraping: dict = field(default_factory=dict)
    markdown: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Apply git defaults
        self.git = _get_default_git(self.git)
        
        # Handle legacy single-site config
        if self.base_url and not self.sites:
            # Convert to single-site list for unified handling
            self.base_url = self.base_url.rstrip("/")
            if self.output_dir is None:
                self.output_dir = Path("content")
            elif isinstance(self.output_dir, str):
                self.output_dir = Path(self.output_dir)
            
            site = SiteConfig(
                name=_derive_site_name(self.base_url),
                base_url=self.base_url,
                output_dir=self.output_dir,
                pages=self.pages,
                selectors=self.selectors,
                scraping=self.scraping,
                markdown=self.markdown,
                metadata=self.metadata,
            )
            self.sites = [site]
    
    def get_site(self, name: str) -> SiteConfig | None:
        """Get a site by name.
        
        Args:
            name: Site name to look up.
            
        Returns:
            SiteConfig if found, None otherwise.
        """
        for site in self.sites:
            if site.name == name:
                return site
        return None
    
    def get_sites(self, names: list[str] | None = None) -> list[SiteConfig]:
        """Get sites, optionally filtered by name.
        
        Args:
            names: Optional list of site names to filter by.
            
        Returns:
            List of matching SiteConfig objects.
        """
        if names is None:
            return self.sites
        return [s for s in self.sites if s.name in names]
    
    @property
    def site_names(self) -> list[str]:
        """Get list of all site names."""
        return [s.name for s in self.sites]


def load_config(path: Path | str = Path("wit.yaml")) -> WitConfig:
    """Load and validate configuration file.
    
    Supports two formats:
    1. Single-site (legacy): Top-level base_url with other settings
    2. Multi-site: List of sites under 'sites' key
    
    Args:
        path: Path to the configuration file.
        
    Returns:
        WitConfig instance with loaded configuration.
        
    Raises:
        FileNotFoundError: If config file doesn't exist.
        ValueError: If configuration is invalid.
    """
    if isinstance(path, str):
        path = Path(path)
    
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    
    # Get global settings (shared across all sites)
    global_git = data.get("git", {})
    global_selectors = data.get("selectors", {})
    global_scraping = data.get("scraping", {})
    global_markdown = data.get("markdown", {})
    global_metadata = data.get("metadata", {})
    
    # Check for multi-site format
    if "sites" in data:
        sites_data = data["sites"]
        if not isinstance(sites_data, list):
            raise ValueError("'sites' must be a list of site configurations")
        
        if not sites_data:
            raise ValueError("'sites' list cannot be empty")
        
        sites = []
        seen_names = set()
        
        for i, site_data in enumerate(sites_data):
            if not isinstance(site_data, dict):
                raise ValueError(f"Site at index {i} must be a dictionary")
            
            if "base_url" not in site_data:
                raise ValueError(f"Site at index {i} must include 'base_url'")
            
            base_url = site_data["base_url"]
            
            # Get or derive site name
            name = site_data.get("name", _derive_site_name(base_url))
            if name in seen_names:
                raise ValueError(f"Duplicate site name: '{name}'. Use explicit 'name' field to disambiguate.")
            seen_names.add(name)
            
            # Determine output directory (default: content/{site_name})
            output_dir = site_data.get("output_dir", f"content/{name}")
            
            # Merge global settings with site-specific settings (site wins)
            site_selectors = {**global_selectors, **site_data.get("selectors", {})}
            site_scraping = {**global_scraping, **site_data.get("scraping", {})}
            site_markdown = {**global_markdown, **site_data.get("markdown", {})}
            site_metadata = {**global_metadata, **site_data.get("metadata", {})}
            
            site = SiteConfig(
                name=name,
                base_url=base_url,
                output_dir=Path(output_dir),
                pages=site_data.get("pages", {}),
                selectors=site_selectors,
                scraping=site_scraping,
                markdown=site_markdown,
                metadata=site_metadata,
            )
            sites.append(site)
        
        return WitConfig(sites=sites, git=global_git)
    
    # Single-site (legacy) format
    if "base_url" not in data:
        raise ValueError("Configuration must include 'base_url' or 'sites'")
    
    return WitConfig(
        base_url=data["base_url"],
        output_dir=Path(data.get("output_dir", "content")),
        pages=data.get("pages", {}),
        selectors=data.get("selectors", {}),
        scraping=data.get("scraping", {}),
        markdown=data.get("markdown", {}),
        git=global_git,
        metadata=data.get("metadata", {}),
    )


def create_default_config(base_url: str, multi_site: bool = False) -> str:
    """Generate a default config file.
    
    Args:
        base_url: The base URL of the website to scrape.
        multi_site: If True, generate a multi-site config template.
        
    Returns:
        YAML string with default configuration.
    """
    if multi_site:
        return _create_multi_site_config(base_url)
    return _create_single_site_config(base_url)


def _create_single_site_config(base_url: str) -> str:
    """Generate a single-site config file."""
    config = f"""# wit configuration file
# Website in Git - Scrape websites to markdown

# Required: base URL of the website
base_url: {base_url}

# Output directory for markdown files
output_dir: content

# How to discover pages (choose one or combine)
pages:
  # Option 1: explicit list of URLs
  urls:
    - /
    - /about
  
  # Option 2: sitemap (uncomment to use)
  # sitemap: /sitemap.xml
  
  # Option 3: crawl from start page (uncomment to use)
  # crawl:
  #   start: /
  #   max_depth: 2
  #   max_pages: 50
  #   include:
  #     - /docs/*
  #     - /blog/*
  #   exclude:
  #     - /admin/*
  #     - /api/*

# Content extraction selectors
selectors:
  # Main content (first match wins)
  content:
    - main
    - article
    - .content
    - .post-body
    - "#main-content"
  
  # Elements to remove before conversion
  remove:
    - nav
    - footer
    - header
    - script
    - style
    - .ads
    - .sidebar
    - .comments
    - "#cookie-banner"
  
  # Title selector
  title: h1

# Scraping behavior
scraping:
  delay: 1.0              # seconds between requests
  timeout: 30             # request timeout in seconds
  user_agent: "wit/1.0"   # custom user agent
  javascript: false       # enable JS rendering (requires playwright)
  wait_until: load        # JS only: load, domcontentloaded, networkidle, commit
  wait_delay: 0           # JS only: extra delay (seconds) after page load

# Markdown conversion options
markdown:
  heading_style: atx      # atx (#) or setext (underline)
  strip_links: false      # remove hyperlinks
  include_images: true    # include image references
  code_language: auto     # try to detect code block languages

# Git commit settings (used with --commit flag)
git:
  author_name: wit[bot]
  author_email: wit[bot]@users.noreply.github.com
  message_template: "Update {{changed_count}} page(s): {{changed_files}}"

# Metadata to include in markdown frontmatter
metadata:
  include_source_url: true
  include_timestamp: true
  include_title: true
"""
    return config


def _create_multi_site_config(base_url: str) -> str:
    """Generate a multi-site config file."""
    site_name = _derive_site_name(base_url)
    config = f"""# wit configuration file - Multi-site
# Website in Git - Scrape multiple websites to markdown

# Define multiple sites to track
sites:
  # First site
  - name: {site_name}  # optional: derived from URL if not specified
    base_url: {base_url}
    output_dir: content/{site_name}  # each site gets its own directory
    pages:
      urls:
        - /
        - /about
      # Or use sitemap/crawl (see below)
    
    # Site-specific overrides (optional)
    # selectors:
    #   content: [".custom-content"]
  
  # Example: Add more sites
  # - name: docs
  #   base_url: https://docs.example.com
  #   output_dir: content/docs
  #   pages:
  #     sitemap: /sitemap.xml
  
  # - name: blog
  #   base_url: https://blog.example.com
  #   output_dir: content/blog
  #   pages:
  #     crawl:
  #       start: /
  #       max_depth: 2

# Global settings (apply to all sites unless overridden)
selectors:
  content:
    - main
    - article
    - .content
    - "#main-content"
  remove:
    - nav
    - footer
    - header
    - script
    - style
    - .ads
    - .sidebar
  title: h1

scraping:
  delay: 1.0
  timeout: 30
  user_agent: "wit/1.0"
  javascript: false
  wait_until: load        # JS only: load, domcontentloaded, networkidle, commit
  wait_delay: 0           # JS only: extra delay (seconds) after page load

markdown:
  heading_style: atx
  strip_links: false
  include_images: true

metadata:
  include_source_url: true
  include_timestamp: true
  include_title: true

git:
  author_name: wit[bot]
  author_email: wit[bot]@users.noreply.github.com
  message_template: "Update {{changed_count}} page(s): {{changed_files}}"
"""
    return config
