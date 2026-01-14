"""Configuration loading and validation for wit."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


@dataclass
class WitConfig:
    """Configuration for wit scraper."""
    
    base_url: str
    output_dir: Path = field(default_factory=lambda: Path("content"))
    pages: dict = field(default_factory=dict)
    selectors: dict = field(default_factory=dict)
    scraping: dict = field(default_factory=dict)
    markdown: dict = field(default_factory=dict)
    git: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate and normalize configuration."""
        # Ensure base_url doesn't have trailing slash
        self.base_url = self.base_url.rstrip("/")
        
        # Convert output_dir to Path if string
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        
        # Set defaults for selectors
        self.selectors = {
            "content": self.selectors.get("content", ["main", "article", ".content", "#main-content", "body"]),
            "remove": self.selectors.get("remove", ["nav", "footer", "header", "script", "style", "noscript"]),
            "title": self.selectors.get("title", "h1"),
        }
        
        # Set defaults for scraping
        self.scraping = {
            "delay": self.scraping.get("delay", 1.0),
            "timeout": self.scraping.get("timeout", 30),
            "user_agent": self.scraping.get("user_agent", "wit/1.0 (+https://github.com/open-veezoo/wit)"),
            "javascript": self.scraping.get("javascript", False),
            "retries": self.scraping.get("retries", 3),
        }
        
        # Set defaults for markdown
        self.markdown = {
            "heading_style": self.markdown.get("heading_style", "atx"),
            "strip_links": self.markdown.get("strip_links", False),
            "include_images": self.markdown.get("include_images", True),
            "code_language": self.markdown.get("code_language", "auto"),
        }
        
        # Set defaults for git
        self.git = {
            "author_name": self.git.get("author_name", "wit[bot]"),
            "author_email": self.git.get("author_email", "wit[bot]@users.noreply.github.com"),
            "message_template": self.git.get("message_template", "Update {changed_count} page(s): {changed_files}"),
        }
        
        # Set defaults for metadata
        self.metadata = {
            "include_source_url": self.metadata.get("include_source_url", True),
            "include_timestamp": self.metadata.get("include_timestamp", True),
            "include_title": self.metadata.get("include_title", True),
        }


def load_config(path: Path | str = Path("wit.yaml")) -> WitConfig:
    """Load and validate configuration file.
    
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
    
    # Validate required fields
    if "base_url" not in data:
        raise ValueError("Configuration must include 'base_url'")
    
    return WitConfig(
        base_url=data["base_url"],
        output_dir=Path(data.get("output_dir", "content")),
        pages=data.get("pages", {}),
        selectors=data.get("selectors", {}),
        scraping=data.get("scraping", {}),
        markdown=data.get("markdown", {}),
        git=data.get("git", {}),
        metadata=data.get("metadata", {}),
    )


def create_default_config(base_url: str) -> str:
    """Generate a default config file.
    
    Args:
        base_url: The base URL of the website to scrape.
        
    Returns:
        YAML string with default configuration.
    """
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
