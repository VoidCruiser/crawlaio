##############################################################################
# Executes asynchronous, parallel web crawling with controlled concurrency.
# Uses an asynchronous crawler to process URLs in parallel, applies helper 
# functions to validate crawl eligibility, tracks progress, retries failed 
# requests, processes and stores documents via a provided processor, and updates 
# the sitemap with newly discovered links.
############################################################################## 
import asyncio
from typing import List
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from tqdm import tqdm
from utils import get_domain, should_crawl_url  # Imported from utils.py
from logger_config import get_logger

logger = get_logger(__name__)

class CrawlProgress:
    """Progress tracking for crawl operations"""
    def __init__(self, total_urls):
        self.pbar = tqdm(total=total_urls)
        
    def update(self):
        self.pbar.update(1)
        
    def close(self):
        self.pbar.close()

class WebCrawler:
    def __init__(self, start_url: str, output_dir: Path, max_concurrent: int,
                 max_retries: int, document_processor, sitemap):
        self.start_url = start_url
        self.output_dir = output_dir
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.document_processor = document_processor
        self.sitemap = sitemap
        self.processed_urls = set()
        self.queued_urls = set()
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def crawl_parallel(self, urls: List[str]):
        """Crawl multiple URLs in parallel with depth and retry limits."""
        print(f"Restricting crawl to domain and path: {self.start_url}")
        browser_config = BrowserConfig(
            headless=True,
            verbose=False,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )
        crawl_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=200,
            excluded_tags=["script", "style"],
            exclude_external_links=True,
            exclude_domains=[d for d in [get_domain(url) for url in urls] if d != get_domain(self.start_url)],
            check_robots_txt=True,
            mean_delay=1.0,
            max_range=0.3
        )
        crawler = AsyncWebCrawler(config=browser_config)
        await crawler.start()
        urls_to_process = asyncio.Queue()
        for url in urls:
            await urls_to_process.put(url)
        progress = CrawlProgress(len(urls))
        
        async def process_worker():
            while True:
                try:
                    url = await urls_to_process.get()
                    if url not in self.processed_urls:
                        await process_url(url)
                    urls_to_process.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    urls_to_process.task_done()
        
        async def process_url(url: str, retry_count: int = 0):
            if url in self.processed_urls or url in self.queued_urls or not should_crawl_url(url, self.start_url):
                return
            self.queued_urls.add(url)
            async with self.semaphore:
                try:
                    result = await crawler.arun(
                        url=url,
                        config=crawl_config,
                        session_id="session1"
                    )
                    if result.success:
                        logger.info(f"Successfully crawled: {url}")
                        self.processed_urls.add(url)
                        self.sitemap.add_url(url)
                        progress.update()
                        await self.document_processor.process_and_store_document(url, result.markdown_v2.raw_markdown, self.output_dir)
                        if hasattr(result.markdown_v2, 'links'):
                            for link in result.markdown_v2.links:
                                link_url = link.get('href', '')
                                if (link_url and 
                                    get_domain(link_url) == get_domain(self.start_url) and 
                                    link_url not in self.processed_urls and
                                    link_url not in self.queued_urls):
                                    await urls_to_process.put(link_url)
                                    logger.info(f"Added to queue: {link_url}")
                        if hasattr(result, 'cleaned_html'):
                            soup = BeautifulSoup(result.cleaned_html, 'html.parser')
                            for a_tag in soup.find_all('a', href=True):
                                link_url = a_tag['href']
                                if link_url.startswith('/'):
                                    link_url = urljoin(url, link_url)
                                if (link_url and 
                                    get_domain(link_url) == get_domain(self.start_url) and 
                                    link_url not in self.processed_urls and
                                    link_url not in self.queued_urls):
                                    await urls_to_process.put(link_url)
                                    logger.debug(f"Added to queue: {link_url}")
                    else:
                        logger.error(f"Failed: {url} - Error: {result.error_message}")
                        if retry_count < self.max_retries:
                            logger.warning(f"Retrying {url} (attempt {retry_count + 1}/{self.max_retries})")
                            await asyncio.sleep(1)
                            await process_url(url, retry_count + 1)
                except Exception as e:
                    logger.error(f"Error processing {url}: {e}")
                    if retry_count < self.max_retries:
                        logger.warning(f"Retrying {url} (attempt {retry_count + 1}/{self.max_retries})")
                        await asyncio.sleep(1)
                        await process_url(url, retry_count + 1)
        
        workers = [asyncio.create_task(process_worker()) for _ in range(self.max_concurrent)]
        try:
            await urls_to_process.join()
        except Exception as e:
            print(f"Error during processing: {e}")
        finally:
            for worker in workers:
                worker.cancel()
            progress.close()
        self.sitemap.save_sitemap()
        await crawler.close()
