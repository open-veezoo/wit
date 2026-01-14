"""Tests for scraper module."""

import pytest

from wit.scraper import extract_content, ScrapingError


class TestExtractContent:
    """Tests for extract_content function."""
    
    def test_extract_from_main(self):
        """Test extracting content from main element."""
        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <main>
                    <h1>Title</h1>
                    <p>Content here.</p>
                </main>
                <footer>Footer</footer>
            </body>
        </html>
        """
        selectors = {
            "content": ["main"],
            "remove": ["nav", "footer"],
            "title": "h1"
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Content here." in content
        assert title == "Title"
        assert "Navigation" not in content
        assert "Footer" not in content
    
    def test_extract_from_article(self):
        """Test extracting content from article element."""
        html = """
        <html>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content.</p>
                </article>
            </body>
        </html>
        """
        selectors = {
            "content": ["article"],
            "remove": [],
            "title": "h1"
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Article content." in content
        assert title == "Article Title"
    
    def test_extract_with_class_selector(self):
        """Test extracting content with class selector."""
        html = """
        <html>
            <body>
                <div class="sidebar">Sidebar</div>
                <div class="content">
                    <h1>Main Content</h1>
                    <p>Text here.</p>
                </div>
            </body>
        </html>
        """
        selectors = {
            "content": [".content"],
            "remove": [".sidebar"],
            "title": "h1"
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Text here." in content
        assert "Sidebar" not in content
    
    def test_extract_with_id_selector(self):
        """Test extracting content with ID selector."""
        html = """
        <html>
            <body>
                <div id="main-content">
                    <h1>Title</h1>
                    <p>Important content.</p>
                </div>
            </body>
        </html>
        """
        selectors = {
            "content": ["#main-content"],
            "remove": [],
            "title": "h1"
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Important content." in content
    
    def test_remove_multiple_elements(self):
        """Test removing multiple element types."""
        html = """
        <html>
            <body>
                <main>
                    <nav>Nav</nav>
                    <p>Content</p>
                    <script>alert('hi')</script>
                    <style>.foo{}</style>
                    <div class="ads">Ads</div>
                </main>
            </body>
        </html>
        """
        selectors = {
            "content": ["main"],
            "remove": ["nav", "script", "style", ".ads"],
            "title": None
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Content" in content
        assert "Nav" not in content
        assert "alert" not in content
        assert ".foo" not in content
        assert "Ads" not in content
    
    def test_first_matching_selector(self):
        """Test that first matching selector is used."""
        html = """
        <html>
            <body>
                <main>Main content</main>
                <article>Article content</article>
            </body>
        </html>
        """
        selectors = {
            "content": ["main", "article"],  # main first
            "remove": [],
            "title": None
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Main content" in content
    
    def test_fallback_to_body(self):
        """Test fallback to body when no selector matches."""
        html = """
        <html>
            <body>
                <div>Some content here</div>
            </body>
        </html>
        """
        selectors = {
            "content": ["main", "article", ".content"],
            "remove": [],
            "title": None
        }
        
        content, title = extract_content(html, selectors)
        
        assert "Some content here" in content
    
    def test_title_extraction(self):
        """Test title extraction with custom selector."""
        html = """
        <html>
            <body>
                <h1 class="page-title">Page Title</h1>
                <h2>Subtitle</h2>
                <p>Content</p>
            </body>
        </html>
        """
        selectors = {
            "content": ["body"],
            "remove": [],
            "title": "h1.page-title"
        }
        
        content, title = extract_content(html, selectors)
        
        assert title == "Page Title"
    
    def test_no_title_found(self):
        """Test when title element doesn't exist."""
        html = "<body><p>Content without title</p></body>"
        selectors = {
            "content": ["body"],
            "remove": [],
            "title": "h1"
        }
        
        content, title = extract_content(html, selectors)
        
        assert title is None
        assert "Content without title" in content
    
    def test_default_selectors(self):
        """Test with default selector values."""
        html = """
        <html>
            <body>
                <nav>Nav</nav>
                <main><h1>Title</h1><p>Content</p></main>
                <footer>Footer</footer>
            </body>
        </html>
        """
        # Using defaults
        selectors = {}
        
        content, title = extract_content(html, selectors)
        
        # Should have found content using default selectors
        assert content  # Not empty
