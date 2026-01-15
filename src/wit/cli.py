"""CLI entry point for wit."""

import sys
import time
from pathlib import Path

import click

from wit.config import SiteConfig, WitConfig, load_config, create_default_config
from wit.converter import html_to_markdown, add_metadata
from wit.discovery import discover_pages_for_site
from wit.git import commit_changes, get_changed_files, has_changes, is_git_repo
from wit.scraper import ScrapingError, fetch_page, extract_content
from wit.utils import format_commit_message, get_logger, setup_logging, url_to_filepath


class SiteParamType(click.ParamType):
    """Custom parameter type for site filtering."""
    name = "site"

    def convert(self, value, param, ctx):
        if value is None:
            return None
        # Allow comma-separated site names
        return [s.strip() for s in value.split(",") if s.strip()]


SITE_TYPE = SiteParamType()


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
@click.option("--site", "-s", type=SITE_TYPE, help="Site(s) to scrape (comma-separated names, default: all)")
@click.pass_context
def scrape(ctx: click.Context, config: str, commit: bool, site: list[str] | None):
    """Scrape website(s) and save as markdown."""
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
    
    # Get sites to scrape
    sites = cfg.get_sites(site)
    
    if not sites:
        if site:
            logger.error(f"No sites found matching: {', '.join(site)}")
            logger.info(f"Available sites: {', '.join(cfg.site_names)}")
        else:
            logger.error("No sites configured")
        sys.exit(1)
    
    # Log what we're scraping
    if len(sites) > 1:
        logger.info(f"Scraping {len(sites)} sites: {', '.join(s.name for s in sites)}")
    
    # Track overall stats
    total_scraped = 0
    total_changed = 0
    total_failed = 0
    all_changed_files = []
    
    # Scrape each site
    for site_config in sites:
        scraped, changed, failed, changed_files = _scrape_site(site_config, logger)
        total_scraped += scraped
        total_changed += changed
        total_failed += failed
        all_changed_files.extend(changed_files)
    
    # Summary
    if len(sites) > 1:
        logger.info(f"Total: {total_scraped} pages, {total_changed} changed, {total_failed} failed")
    
    # Commit if requested
    if commit and total_changed > 0:
        try:
            message = format_commit_message(cfg.git["message_template"], all_changed_files)
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
    elif commit and total_changed == 0:
        logger.info("No changes to commit")


def _scrape_site(site: SiteConfig, logger) -> tuple[int, int, int, list[str]]:
    """Scrape a single site.
    
    Args:
        site: Site configuration.
        logger: Logger instance.
        
    Returns:
        Tuple of (scraped_count, changed_count, failed_count, changed_files).
    """
    logger.info(f"[{site.name}] Discovering pages from {site.base_url}...")
    
    try:
        urls = discover_pages_for_site(site)
    except Exception as e:
        logger.error(f"[{site.name}] Failed to discover pages: {e}")
        return 0, 0, 0, []
    
    logger.info(f"[{site.name}] Discovered {len(urls)} pages")
    
    if not urls:
        logger.warning(f"[{site.name}] No pages to scrape")
        return 0, 0, 0, []
    
    # Create output directory
    site.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Scrape pages
    scraped_count = 0
    changed_count = 0
    failed_count = 0
    changed_files = []
    
    delay = site.scraping.get("delay", 1.0)
    
    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(delay)
        
        filepath = url_to_filepath(url, site.base_url, site.output_dir)
        logger.info(f"[{site.name}] Scraping {url} -> {filepath}")
        
        try:
            # Fetch page
            html = fetch_page(url, site.scraping)
            
            # Extract content
            content_html, title = extract_content(html, site.selectors)
            
            # Convert to markdown
            markdown = html_to_markdown(content_html, site.markdown)
            
            # Add metadata
            markdown = add_metadata(markdown, url, title, site.metadata)
            
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
            logger.warning(f"[{site.name}] Skipping {url} ({e})")
            failed_count += 1
        except Exception as e:
            logger.warning(f"[{site.name}] Failed to scrape {url}: {e}")
            failed_count += 1
    
    # Summary for this site
    logger.info(f"[{site.name}] Complete: {scraped_count} pages, {changed_count} changed, {failed_count} failed")
    
    return scraped_count, changed_count, failed_count, changed_files


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
@click.option("--multi-site", is_flag=True, help="Create a multi-site config template")
@click.pass_context
def init(ctx: click.Context, base_url: str, output: str, multi_site: bool):
    """Create a default wit.yaml config file."""
    logger = get_logger()
    
    output_path = Path(output)
    
    if output_path.exists():
        if not click.confirm(f"{output} already exists. Overwrite?"):
            logger.info("Aborted")
            sys.exit(0)
    
    config_content = create_default_config(base_url, multi_site=multi_site)
    output_path.write_text(config_content, encoding="utf-8")
    
    logger.info(f"Created {output}")
    if multi_site:
        logger.info("Multi-site config created. Add more sites under the 'sites' key.")
    logger.info("Edit the config file to customize scraping settings")
    logger.info("Then run 'wit scrape' to start scraping")


@cli.command("list")
@click.option("--config", "-c", default="wit.yaml", help="Config file path")
@click.option("--site", "-s", type=SITE_TYPE, help="Site(s) to list (comma-separated names, default: all)")
@click.pass_context
def list_pages(ctx: click.Context, config: str, site: list[str] | None):
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
    
    # Get sites to list
    sites = cfg.get_sites(site)
    
    if not sites:
        if site:
            logger.error(f"No sites found matching: {', '.join(site)}")
            logger.info(f"Available sites: {', '.join(cfg.site_names)}")
        else:
            logger.error("No sites configured")
        sys.exit(1)
    
    total_pages = 0
    
    for site_config in sites:
        # Discover pages for this site
        try:
            urls = discover_pages_for_site(site_config)
        except Exception as e:
            logger.error(f"[{site_config.name}] Failed to discover pages: {e}")
            continue
        
        total_pages += len(urls)
        
        # Print site header
        if len(sites) > 1:
            click.echo(f"\n{site_config.name} ({site_config.base_url}):")
            click.echo(f"  Found {len(urls)} pages\n")
        else:
            click.echo(f"Found {len(urls)} pages:\n")
        
        for url in urls:
            filepath = url_to_filepath(url, site_config.base_url, site_config.output_dir)
            click.echo(f"  {url}")
            click.echo(f"    -> {filepath}")
            click.echo()
    
    if len(sites) > 1:
        click.echo(f"\nTotal: {total_pages} pages across {len(sites)} sites")


@cli.command("sites")
@click.option("--config", "-c", default="wit.yaml", help="Config file path")
@click.pass_context
def list_sites(ctx: click.Context, config: str):
    """List all configured sites."""
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
    
    if not cfg.sites:
        click.echo("No sites configured")
        sys.exit(0)
    
    click.echo(f"Configured sites ({len(cfg.sites)}):\n")
    
    for site in cfg.sites:
        click.echo(f"  {site.name}")
        click.echo(f"    URL:    {site.base_url}")
        click.echo(f"    Output: {site.output_dir}")
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
