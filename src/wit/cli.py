"""CLI entry point for wit."""

import sys
import time
from pathlib import Path

import click

from wit.config import WitConfig, load_config, create_default_config
from wit.converter import html_to_markdown, add_metadata
from wit.discovery import discover_pages
from wit.git import commit_changes, get_changed_files, has_changes, is_git_repo
from wit.scraper import ScrapingError, fetch_page, extract_content
from wit.utils import format_commit_message, get_logger, setup_logging, url_to_filepath


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose (debug) output")
@click.option("-q", "--quiet", is_flag=True, help="Only show warnings and errors")
@click.version_option(package_name="wit")
@click.pass_context
def cli(ctx: click.Context, verbose: bool, quiet: bool):
    """wit - Website in Git. Scrape websites to markdown."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    setup_logging(verbose=verbose, quiet=quiet)


@cli.command()
@click.option("--config", "-c", default="wit.yaml", help="Config file path")
@click.option("--commit", is_flag=True, help="Commit changes to git")
@click.pass_context
def scrape(ctx: click.Context, config: str, commit: bool):
    """Scrape website and save as markdown."""
    logger = get_logger()
    
    # Load config
    try:
        logger.info(f"Loading config from {config}")
        cfg = load_config(Path(config))
    except FileNotFoundError:
        logger.error(f"Config file not found: {config}")
        logger.info("Run 'wit init' to create a default config file")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid config: {e}")
        sys.exit(1)
    
    # Check git repo if committing
    if commit and not is_git_repo():
        logger.error("Not in a git repository. Cannot commit changes.")
        sys.exit(1)
    
    # Discover pages
    logger.info("Discovering pages to scrape...")
    try:
        urls = discover_pages(cfg)
    except Exception as e:
        logger.error(f"Failed to discover pages: {e}")
        sys.exit(1)
    
    logger.info(f"Discovered {len(urls)} pages to scrape")
    
    if not urls:
        logger.warning("No pages to scrape")
        sys.exit(0)
    
    # Create output directory
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Scrape pages
    scraped_count = 0
    changed_count = 0
    failed_count = 0
    changed_files = []
    
    delay = cfg.scraping.get("delay", 1.0)
    
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay)
        
        filepath = url_to_filepath(url, cfg.base_url, cfg.output_dir)
        logger.info(f"Scraping {url} -> {filepath}")
        
        try:
            # Fetch page
            html = fetch_page(url, cfg.scraping)
            
            # Extract content
            content_html, title = extract_content(html, cfg.selectors)
            
            # Convert to markdown
            markdown = html_to_markdown(content_html, cfg.markdown)
            
            # Add metadata
            markdown = add_metadata(markdown, url, title, cfg.metadata)
            
            # Check if content changed
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            content_changed = True
            if filepath.exists():
                existing = filepath.read_text(encoding="utf-8")
                # Compare ignoring timestamp line
                existing_body = _strip_timestamp(existing)
                new_body = _strip_timestamp(markdown)
                content_changed = existing_body != new_body
            
            if content_changed:
                filepath.write_text(markdown, encoding="utf-8")
                changed_count += 1
                changed_files.append(str(filepath))
            
            scraped_count += 1
            
        except ScrapingError as e:
            logger.warning(f"Skipping {url} ({e})")
            failed_count += 1
        except Exception as e:
            logger.warning(f"Failed to scrape {url}: {e}")
            failed_count += 1
    
    # Summary
    logger.info(f"Scraping complete: {scraped_count} pages, {changed_count} changed, {failed_count} failed")
    
    # Commit if requested
    if commit and changed_count > 0:
        try:
            message = format_commit_message(cfg.git["message_template"], changed_files)
            sha = commit_changes(
                message=message,
                author_name=cfg.git["author_name"],
                author_email=cfg.git["author_email"],
            )
            if sha:
                logger.info(f'Committed: {sha} "{message}"')
        except Exception as e:
            logger.error(f"Failed to commit: {e}")
            sys.exit(1)
    elif commit and changed_count == 0:
        logger.info("No changes to commit")


@cli.command("scrape-url")
@click.argument("url")
@click.option("--output", "-o", required=True, help="Output file path")
@click.option("--javascript", "-j", is_flag=True, help="Enable JavaScript rendering")
@click.pass_context
def scrape_url(ctx: click.Context, url: str, output: str, javascript: bool):
    """Scrape a single URL (ad-hoc, no config needed)."""
    logger = get_logger()
    
    # Default config for ad-hoc scraping
    scraping_config = {
        "delay": 0,
        "timeout": 30,
        "user_agent": "wit/1.0",
        "javascript": javascript,
        "retries": 3,
    }
    
    selectors = {
        "content": ["main", "article", ".content", "#main-content", "body"],
        "remove": ["nav", "footer", "header", "script", "style", "noscript"],
        "title": "h1",
    }
    
    markdown_options = {
        "heading_style": "atx",
        "strip_links": False,
        "include_images": True,
        "code_language": "auto",
    }
    
    metadata_config = {
        "include_source_url": True,
        "include_timestamp": True,
        "include_title": True,
    }
    
    logger.info(f"Scraping {url}")
    
    try:
        # Fetch page
        html = fetch_page(url, scraping_config)
        
        # Extract content
        content_html, title = extract_content(html, selectors)
        
        # Convert to markdown
        markdown = html_to_markdown(content_html, markdown_options)
        
        # Add metadata
        markdown = add_metadata(markdown, url, title, metadata_config)
        
        # Write output
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        
        logger.info(f"Saved to {output}")
        
    except ScrapingError as e:
        logger.error(f"Failed to scrape: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


@cli.command()
@click.option("--base-url", prompt="Website base URL", help="Website base URL")
@click.option("--output", "-o", default="wit.yaml", help="Output config file path")
@click.pass_context
def init(ctx: click.Context, base_url: str, output: str):
    """Create a default wit.yaml config file."""
    logger = get_logger()
    
    output_path = Path(output)
    
    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            logger.info("Aborted")
            sys.exit(0)
    
    config_content = create_default_config(base_url)
    output_path.write_text(config_content, encoding="utf-8")
    
    logger.info(f"Created {output}")
    logger.info("Edit the config file to customize scraping settings")
    logger.info("Then run 'wit scrape' to start scraping")


@cli.command("list")
@click.option("--config", "-c", default="wit.yaml", help="Config file path")
@click.pass_context
def list_pages(ctx: click.Context, config: str):
    """List all pages that would be scraped (dry run)."""
    logger = get_logger()
    
    # Load config
    try:
        cfg = load_config(Path(config))
    except FileNotFoundError:
        logger.error(f"Config file not found: {config}")
        sys.exit(1)
    except ValueError as e:
        logger.error(f"Invalid config: {e}")
        sys.exit(1)
    
    # Discover pages
    try:
        urls = discover_pages(cfg)
    except Exception as e:
        logger.error(f"Failed to discover pages: {e}")
        sys.exit(1)
    
    # Print pages
    click.echo(f"Found {len(urls)} pages:\n")
    
    for url in urls:
        filepath = url_to_filepath(url, cfg.base_url, cfg.output_dir)
        click.echo(f"  {url}")
        click.echo(f"    -> {filepath}")
        click.echo()


def _strip_timestamp(markdown: str) -> str:
    """Strip timestamp line from markdown for comparison.
    
    This allows detecting actual content changes vs just timestamp updates.
    """
    lines = markdown.split("\n")
    filtered = [line for line in lines if not line.startswith("scraped_at:")]
    return "\n".join(filtered)


def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
