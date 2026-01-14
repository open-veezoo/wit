"""wit - Website in Git. Scrape websites to markdown."""

__version__ = "1.0.0"

from wit.config import WitConfig, load_config, create_default_config
from wit.scraper import fetch_page, extract_content
from wit.converter import html_to_markdown, add_metadata
from wit.discovery import discover_pages
from wit.git import has_changes, get_changed_files, commit_changes

__all__ = [
    "__version__",
    "WitConfig",
    "load_config",
    "create_default_config",
    "fetch_page",
    "extract_content",
    "html_to_markdown",
    "add_metadata",
    "discover_pages",
    "has_changes",
    "get_changed_files",
    "commit_changes",
]
