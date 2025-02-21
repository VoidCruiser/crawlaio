################################################################
#This module handles the discovery of domain-specific URLs via a Scrapy spider.
# Within the spider, URLs are processed by calling sitemap_generator.add_url 
# for each discovered URL, and once the crawl is finished, it calls sitemap_generator.save_sitemap.
################################################################

import threading
import scrapy
from scrapy.crawler import CrawlerProcess
from twisted.internet import defer
from urllib.parse import urlparse
from pathlib import Path
from utils import should_crawl_url

class ScrapyDiscovery:
    def __init__(self, start_url: str, output_dir: Path, sitemap):
        self.start_url = start_url
        self.output_dir = output_dir
        self.sitemap = sitemap
        # Create a single event object
        self.discovery_complete_event = threading.Event()

    def scrapy_crawl(self):
        """
        Use a scrapy spider to crawl the entire specified domain and generate a sitemap.xml.
        The sitemap file will be written to the provided output_dir.
        """
        allowed_domain = urlparse(self.start_url).netloc

        class SitemapSpider(scrapy.Spider):
            name = "sitemap_spider"
            custom_settings = {
                'ROBOTSTXT_OBEY': False,
            }
            
            def __init__(self, allowed_domains, start_urls, sitemap_generator, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.allowed_domains = allowed_domains
                self.start_urls = start_urls
                self.start_url = start_urls[0]
                self.sitemap_generator = sitemap_generator
                self.urls = set()
                # Accept and store the discovery event
                self.discovery_complete_event = kwargs.pop('discovery_event', threading.Event())
        
            def parse(self, response):
                try:
                    normalized_url = response.url.rstrip('/')
                    if normalized_url not in self.urls:
                        self.urls.add(normalized_url)
                        self.sitemap_generator.add_url(normalized_url)
                        links = set(response.css("a::attr(href)").getall())
                        for link in links:
                            try:
                                absolute_url = response.urljoin(link).rstrip('/')
                                if (should_crawl_url(absolute_url, self.start_url) and 
                                    absolute_url not in self.urls):
                                    yield scrapy.Request(
                                        url=absolute_url,
                                        callback=self.parse,
                                        errback=self.handle_error
                                    )
                            except Exception as e:
                                print(f"Error processing link {link}: {e}")
                except Exception as e:
                    print(f"Error parsing response from {response.url}: {e}")
                    
            def handle_error(self, failure):
                print(f"Request failed: {failure.request.url}")
            
            @defer.inlineCallbacks
            def closed(self, reason):
                self.sitemap_generator.save_sitemap()
                print(f"Discovery phase complete. Found {len(self.urls)} URLs")
                self.discovery_complete_event.set()
                yield None

        process = CrawlerProcess()
        process.crawl(SitemapSpider, 
                      allowed_domains=[allowed_domain], 
                      start_urls=[self.start_url], 
                      sitemap_generator=self.sitemap,
                      discovery_event=self.discovery_complete_event)
        process.start()
        
        # Wait for discovery to complete before proceeding
        self.discovery_complete_event.wait()
