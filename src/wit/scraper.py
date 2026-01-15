"""Core scraping logic for wit."""

import time
from typing import Callable

import requests
from bs4 import BeautifulSoup

from wit.utils import get_logger


class ScrapingError(Exception):
    """Exception raised during scraping."""
    pass


def fetch_page(
    url: str, 
    scraping_config: dict,
    fetch_func: Callable | None = None,
) -> str:
    """Fetch page HTML, optionally with JS rendering.
    
    Args:
        url: URL to fetch.
        scraping_config: Scraping configuration dict with:
            - timeout: Request timeout in seconds
            - user_agent: User agent string
            - javascript: Whether to use JS rendering
            - retries: Number of retry attempts
            - wait_until: When to consider navigation complete (JS only).
              Options: "load" (default), "domcontentloaded", "networkidle", "commit"
        fetch_func: Optional custom fetch function for testing.
        
    Returns:
        HTML content as string.
        
    Raises:
        ScrapingError: If fetching fails after retries.
    """
    logger = get_logger()
    
    if fetch_func:
        return fetch_func(url)
    
    timeout = scraping_config.get("timeout", 30)
    user_agent = scraping_config.get("user_agent", "wit/1.0")
    use_javascript = scraping_config.get("javascript", False)
    retries = scraping_config.get("retries", 3)
    
    if use_javascript:
        wait_until = scraping_config.get("wait_until", "load")
        return _fetch_with_javascript(url, timeout, retries, wait_until)
    else:
        return _fetch_static(url, timeout, user_agent, retries)


def _fetch_static(url: str, timeout: int, user_agent: str, retries: int) -> str:
    """Fetch page using requests (no JS rendering).
    
    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.
        user_agent: User agent string.
        retries: Number of retry attempts.
        
    Returns:
        HTML content.
        
    Raises:
        ScrapingError: If fetching fails.
    """
    logger = get_logger()
    headers = {"User-Agent": user_agent}
    
    last_error = None
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                logger.warning(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
                continue
            
            # Handle server errors with retry
            if response.status_code >= 500:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.warning(f"Server error {response.status_code}, retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            
            # Handle 404
            if response.status_code == 404:
                raise ScrapingError(f"Page not found: {url}")
            
            response.raise_for_status()
            return response.text
            
        except requests.exceptions.Timeout as e:
            last_error = e
            wait_time = 2 ** attempt
            logger.warning(f"Timeout fetching {url}, retrying in {wait_time}s (attempt {attempt + 1}/{retries})")
            time.sleep(wait_time)
            
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Error fetching {url}: {e}, retrying in {wait_time}s")
                time.sleep(wait_time)
    
    raise ScrapingError(f"Failed to fetch {url} after {retries} attempts: {last_error}")


def _fetch_with_javascript(url: str, timeout: int, retries: int, wait_until: str = "load") -> str:
    """Fetch page with JavaScript rendering using Playwright.
    
    Args:
        url: URL to fetch.
        timeout: Page load timeout in seconds.
        retries: Number of retry attempts.
        wait_until: When to consider navigation complete. Options:
            - "load": Wait for load event (default, most reliable)
            - "domcontentloaded": Wait for DOMContentLoaded event
            - "networkidle": Wait until no network connections for 500ms
            - "commit": Wait for network response and document loading
        
    Returns:
        Rendered HTML content.
        
    Raises:
        ScrapingError: If fetching fails.
    """
    logger = get_logger()
    
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        raise ScrapingError(
            "JavaScript rendering requires playwright. "
            "Install with: pip install 'wit[js]' && playwright install chromium"
        )
    
    last_error = None
    
    for attempt in range(retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                
                # Set timeout (playwright uses milliseconds)
                page.set_default_timeout(timeout * 1000)
                
                page.goto(url, wait_until=wait_until)
                html = page.content()
                
                browser.close()
                return html
                
        except PlaywrightTimeout as e:
            last_error = e
            wait_time = 2 ** attempt
            logger.warning(f"Timeout rendering {url}, retrying in {wait_time}s")
            time.sleep(wait_time)
            
        except Exception as e:
            last_error = e
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                logger.warning(f"Error rendering {url}: {e}, retrying in {wait_time}s")
                time.sleep(wait_time)
    
    raise ScrapingError(f"Failed to render {url} after {retries} attempts: {last_error}")


def extract_content(html: str, selectors: dict) -> tuple[str, str | None]:
    """Extract main content and optional title using selectors.
    
    Args:
        html: HTML content to extract from.
        selectors: Dict with:
            - content: List of CSS selectors for main content
            - remove: List of CSS selectors to remove
            - title: CSS selector for title
            
    Returns:
        Tuple of (content_html, title).
        Content is the extracted HTML string.
        Title is the extracted title text or None.
    """
    logger = get_logger()
    
    soup = BeautifulSoup(html, "lxml")
    
    # Remove unwanted elements first
    remove_selectors = selectors.get("remove", [])
    for selector in remove_selectors:
        for element in soup.select(selector):
            element.decompose()
    
    # Extract title
    title = None
    title_selector = selectors.get("title", "h1")
    if title_selector:
        title_elem = soup.select_one(title_selector)
        if title_elem:
            title = title_elem.get_text(strip=True)
    
    # Extract main content (first matching selector wins)
    content_selectors = selectors.get("content", ["main", "article", ".content", "body"])
    content_html = None
    
    for selector in content_selectors:
        content_elem = soup.select_one(selector)
        if content_elem:
            content_html = str(content_elem)
            logger.debug(f"Found content using selector: {selector}")
            break
    
    if not content_html:
        # Fallback to body
        body = soup.find("body")
        if body:
            content_html = str(body)
            logger.debug("Using body as fallback content")
        else:
            content_html = str(soup)
            logger.debug("Using full document as fallback content")
    
    return content_html, title
