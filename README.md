# crawlaio



# It's full of bugs. I know. Fuck you


Web Crawler with Ollama Integration
Overview

This web crawler is designed for efficient content discovery, extraction, and processing. It leverages Scrapy for URL discovery, an asynchronous parallel crawler for fast processing, and Ollama AI for metadata enrichment. The extracted content is embedded into vector-ready JSON files, making it suitable for AI-driven applications such as search indexing, retrieval-augmented generation (RAG), and document analysis.
Key Features

    Scrapy-based URL discovery: Identifies and collects all links within the target domain.
    Asynchronous parallel crawling: Extracts content from multiple pages efficiently with controlled concurrency.
    Document processing: Cleans, structures, and segments extracted web content.
    Ollama AI Integration:
        Retrieves titles and summaries from extracted text.
        Generates embeddings for AI-based content understanding.
    Automated sitemap generation: Creates a sitemap.xml with all discovered URLs.
    Vector-ready output: Processes extracted text, embeds it using Ollama, and saves structured JSON files with embeddings for seamless AI integration.
    Logging and error handling: Tracks failures, retries problematic pages, and logs system behavior for debugging.

# Installation

  Clone the repository or move all files to a working directory.


  Configure .env
  

  Install dependencies:

    pip install -r requirements.txt

Configure the crawler:

    Modify config.json to adjust settings:

    {
      "base_url": "http://localhost:11434",
      "model": "llama3.2:3b",
      "embed_model": "nomic-embed-text"
    }

Run the crawler:

    python main.py

View logs:

    Logs are stored in the logs/ directory:
        combined.log: Full logs (DEBUG level).
        debug.log: Debug-specific logs.
    Console logs display warnings and errors.
