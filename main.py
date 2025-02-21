import asyncio
import sys
import pathlib
import psutil
from ArgumentHandler import ArgumentHandler
from ollama_config import ollama_config  # Use preloaded instance
from ollama_client import OllamaClient
from WebCrawler import WebCrawler, get_domain
from DocumentProcessor import DocumentProcessor
from ScrapyDiscovery import ScrapyDiscovery
from SitemapGenerator import SitemapGenerator
from logger_config import get_logger

logger = get_logger(__name__)

def check_memory_usage():
    """Monitor memory usage and print warning if over 1GB"""
    if psutil.Process().memory_info().rss > 1024**3:  # 1GB
        logger.warning("High memory usage detected")

class MainApp:
    def __init__(self):
        args = ArgumentHandler.get_arguments()
        self.args = vars(args)

        self.ollama_client = OllamaClient()
        self.document_processor = DocumentProcessor(self.ollama_client)
        self.output_dir = pathlib.Path(self.args['output_dir'])
        self.domain = get_domain(self.args['url'])
        self.sitemap = SitemapGenerator(self.domain, self.output_dir, self.args['url'])
        self.web_crawler = WebCrawler(
            self.args['url'],
            self.output_dir,
            self.args['max_concurrent'],
            self.args['max_retries'],
            self.document_processor,
            self.sitemap
        )
        self.scrapy_discovery = ScrapyDiscovery(self.args['url'], self.output_dir, self.sitemap)

    async def run(self):
        try:
            await self.ollama_client.validate_config()
        except ValueError as e:
            logger.error(f"Configuration error: {e}")
            sys.exit(1)

        logger.info(f"Starting discovery phase with Scrapy from: {self.args['url']}")
        self.scrapy_discovery.scrapy_crawl()

        discovered_urls = self.sitemap.load_urls()
        if not discovered_urls:
            logger.error("No URLs discovered in sitemap.xml")
            sys.exit(1)

        logger.info(f"Starting processing phase for {len(discovered_urls)} URLs")
        await self.web_crawler.crawl_parallel(list(discovered_urls))

if __name__ == "__main__":
    asyncio.run(MainApp().run())
