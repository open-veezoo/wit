"""HTML to markdown conversion for wit."""

from datetime import datetime, timezone
from typing import Any

from markdownify import markdownify as md, MarkdownConverter

from wit.utils import get_logger


class WitMarkdownConverter(MarkdownConverter):
    """Custom markdown converter with wit-specific options."""
    
    def __init__(self, **options):
        self.strip_links = options.pop("strip_links", False)
        self.include_images = options.pop("include_images", True)
        self.code_language = options.pop("code_language", "auto")
        super().__init__(**options)
    
    def convert_a(self, el, text, convert_as_inline):
        """Convert anchor tags, optionally stripping links."""
        if self.strip_links:
            return text
        return super().convert_a(el, text, convert_as_inline)
    
    def convert_img(self, el, text, convert_as_inline):
        """Convert image tags."""
        if not self.include_images:
            return ""
        return super().convert_img(el, text, convert_as_inline)
    
    def convert_pre(self, el, text, convert_as_inline):
        """Convert pre tags with optional language detection."""
        # Try to detect language from class
        code_el = el.find("code")
        lang = ""
        
        if code_el:
            classes = code_el.get("class", [])
            if isinstance(classes, str):
                classes = classes.split()
            
            for cls in classes:
                if cls.startswith("language-"):
                    lang = cls[9:]  # Remove "language-" prefix
                    break
                elif cls.startswith("lang-"):
                    lang = cls[5:]  # Remove "lang-" prefix
                    break
                elif cls in ("python", "javascript", "typescript", "java", "go", 
                           "rust", "ruby", "php", "csharp", "cpp", "c", "bash",
                           "shell", "sql", "json", "yaml", "xml", "html", "css"):
                    lang = cls
                    break
        
        # Get the code content
        if code_el:
            code_text = code_el.get_text()
        else:
            code_text = el.get_text()
        
        # Auto-detect language if enabled
        if not lang and self.code_language == "auto":
            lang = _detect_language(code_text)
        
        return f"\n```{lang}\n{code_text.strip()}\n```\n"


def html_to_markdown(html: str, options: dict) -> str:
    """Convert HTML to clean markdown.
    
    Args:
        html: HTML string to convert.
        options: Markdown conversion options:
            - heading_style: "atx" (#) or "setext" (underline)
            - strip_links: Remove hyperlinks
            - include_images: Include image references
            - code_language: "auto" to detect code languages
            
    Returns:
        Markdown string.
    """
    logger = get_logger()
    
    heading_style = options.get("heading_style", "atx")
    strip_links = options.get("strip_links", False)
    include_images = options.get("include_images", True)
    code_language = options.get("code_language", "auto")
    
    # Map heading style to markdownify format
    if heading_style == "setext":
        heading_style_md = "setext"
    else:
        heading_style_md = "atx"
    
    try:
        markdown = WitMarkdownConverter(
            heading_style=heading_style_md,
            strip_links=strip_links,
            include_images=include_images,
            code_language=code_language,
            bullets="-",
            autolinks=True,
            escape_asterisks=False,
            escape_underscores=False,
        ).convert(html)
    except Exception as e:
        logger.warning(f"Error during markdown conversion: {e}")
        # Fallback to basic conversion
        markdown = md(html, heading_style=heading_style_md)
    
    # Clean up the markdown
    markdown = _clean_markdown(markdown)
    
    return markdown


def add_metadata(
    markdown: str,
    url: str,
    title: str | None,
    metadata_config: dict
) -> str:
    """Add frontmatter/metadata to markdown.
    
    Args:
        markdown: Markdown content.
        url: Source URL of the content.
        title: Page title (optional).
        metadata_config: Metadata options:
            - include_source_url: Include source URL
            - include_timestamp: Include scrape timestamp
            - include_title: Include page title
            
    Returns:
        Markdown with frontmatter prepended.
    """
    include_source_url = metadata_config.get("include_source_url", True)
    include_timestamp = metadata_config.get("include_timestamp", True)
    include_title = metadata_config.get("include_title", True)
    
    frontmatter_lines = []
    
    if include_source_url:
        frontmatter_lines.append(f"source: {url}")
    
    if include_timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        frontmatter_lines.append(f"scraped_at: {timestamp}")
    
    if include_title and title:
        # Escape title for YAML
        escaped_title = title.replace('"', '\\"')
        frontmatter_lines.append(f'title: "{escaped_title}"')
    
    if frontmatter_lines:
        frontmatter = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n"
        return frontmatter + markdown
    
    return markdown


def _clean_markdown(markdown: str) -> str:
    """Clean up markdown output.
    
    Args:
        markdown: Raw markdown string.
        
    Returns:
        Cleaned markdown string.
    """
    # Split into lines for processing
    lines = markdown.split("\n")
    
    # Remove excessive blank lines (more than 2 consecutive)
    cleaned_lines = []
    blank_count = 0
    
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)
    
    markdown = "\n".join(cleaned_lines)
    
    # Strip leading/trailing whitespace
    markdown = markdown.strip()
    
    # Ensure file ends with newline
    markdown += "\n"
    
    return markdown


def _detect_language(code: str) -> str:
    """Try to detect the programming language of a code snippet.
    
    Args:
        code: Code snippet.
        
    Returns:
        Detected language or empty string.
    """
    code = code.strip()
    
    # Check for common patterns
    patterns = [
        # Python
        (r"^(import |from .+ import |def |class |if __name__|print\()", "python"),
        # JavaScript/TypeScript
        (r"^(const |let |var |function |import .+ from|export |=>)", "javascript"),
        # Java
        (r"^(public class |private |protected |package |import java\.)", "java"),
        # Go
        (r"^(package |func |import \(|var |type .+ struct)", "go"),
        # Rust
        (r"^(fn |let mut |use |pub |impl |struct |enum )", "rust"),
        # Ruby
        (r"^(require |def |class |module |end$|puts )", "ruby"),
        # PHP
        (r"^(<\?php|\$\w+ = |function |namespace |use )", "php"),
        # Shell/Bash
        (r"^(#!/bin/|#!.*bash|export |echo |if \[|\$\()", "bash"),
        # SQL
        (r"^(SELECT |INSERT |UPDATE |DELETE |CREATE |DROP |ALTER )", "sql"),
        # HTML
        (r"^<!DOCTYPE|^<html|^<head|^<body", "html"),
        # CSS
        (r"^(\.|#|@media|@import|body\s*\{)", "css"),
        # JSON
        (r'^\s*[\{\[].*[\}\]]\s*$', "json"),
        # YAML
        (r"^[a-zA-Z_]+:\s*$|^- [a-zA-Z]", "yaml"),
        # XML
        (r"^<\?xml|^<[a-zA-Z]+>", "xml"),
    ]
    
    import re
    
    for pattern, lang in patterns:
        if re.search(pattern, code, re.MULTILINE | re.IGNORECASE):
            return lang
    
    return ""
