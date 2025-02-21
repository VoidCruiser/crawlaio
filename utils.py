from urllib.parse import urlparse

def is_valid_url(url: str) -> bool:
    """Check if a URL starts with http:// or https://"""
    return url.startswith(('http://', 'https://'))

def get_domain(url: str) -> str:
    """Extract the domain from a URL."""
    return urlparse(url).netloc

def should_crawl_url(url: str, start_url: str) -> bool:
    """Determine if a URL should be crawled based on the start_url domain and path."""
    start_parsed = urlparse(start_url)
    url_parsed = urlparse(url)
    return start_parsed.netloc == url_parsed.netloc and url_parsed.path.startswith(start_parsed.path)