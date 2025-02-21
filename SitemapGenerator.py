#################################################################
## This module is solely responsible for managing the sitemap.
# It contains methods to add URLs (add_url), save the sitemap 
# (save_sitemap), and load URLs (load_urls).
##################################################################

from pathlib import Path
from datetime import datetime, timezone
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from utils import get_domain, should_crawl_url  # Updated import

from logger_config import get_logger  #  Import centralized logger
logger = get_logger(__name__)  #  Uses the correct logging setup


class SitemapGenerator:
    def __init__(self, domain: str, output_dir: Path, start_url: str):
        self.domain = domain
        self.start_url = start_url  # Store the original start URL for comparison
        self.urls = set()
        self.output_dir = output_dir
        self.sitemap_path = self.output_dir / "sitemap.xml"
        
    def add_url(self, url: str):
        """Add a URL to the sitemap if it belongs to the target domain."""
        if get_domain(url) == self.domain:
            self.urls.add(url)
    
    def save_sitemap(self):
        """Generate and save the sitemap.xml file."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(self.sitemap_path, "w", encoding="utf-8") as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
                for url in sorted(self.urls):
                    try:
                        f.write("  <url>\n")
                        f.write(f"    <loc>{url}</loc>\n")
                        f.write(f"    <lastmod>{datetime.now(timezone.utc).strftime('%Y-%m-%d')}</lastmod>\n")
                        f.write("  </url>\n")
                    except Exception as e:
                        print(f"Error writing URL {url} to sitemap: {e}")
                f.write("</urlset>\n")
            logger.info(f"Sitemap saved to {self.sitemap_path}")
        except Exception as e:
            logger.error(f"Error saving sitemap: {e}")
    
    def load_urls(self) -> set:
        """Load URLs from an existing sitemap.xml file."""
        urls = set()
        try:
            if not self.sitemap_path.exists():
                print(f"No existing sitemap found at {self.sitemap_path}")
                return urls
            with open(self.sitemap_path, "r", encoding="utf-8") as f:
                try:
                    soup = BeautifulSoup(f, "xml")
                    for url in soup.find_all("loc"):
                        normalized_url = url.text.rstrip('/')
                        if should_crawl_url(normalized_url, self.start_url):
                            urls.add(normalized_url)
                except Exception as e:
                    print(f"Error parsing sitemap XML: {e}")
            print(f"Loaded {len(urls)} URLs from existing sitemap")
        except Exception as e:
            print(f"Error loading sitemap: {e}")
        return urls
