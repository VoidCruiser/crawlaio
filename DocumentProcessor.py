import asyncio
import json
import re
import pathlib
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import List, Dict, Any
from dataclasses import dataclass
from logger_config import get_logger

logger = get_logger(__name__)

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

class DocumentProcessor:
    def __init__(self, ollama_client):
        self.ollama_client = ollama_client

    def chunk_text(self, text: str, chunk_size: int = 5000) -> List[str]:
        """Split text into manageable chunks, ensuring logical breaks."""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + chunk_size, text_length)
            chunk = text[start:end]

            # Attempt to break at natural boundaries
            last_code_block = chunk.rfind('```')
            last_paragraph_break = chunk.rfind('\n\n')
            last_sentence_break = chunk.rfind('. ')

            if last_code_block > chunk_size * 0.3:
                end = start + last_code_block
            elif last_paragraph_break > chunk_size * 0.3:
                end = start + last_paragraph_break
            elif last_sentence_break > chunk_size * 0.3:
                end = start + last_sentence_break + 1  # Include period

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = max(start + 1, end)  # Move to next chunk

        return chunks

    async def process_chunk(self, chunk: str, chunk_number: int, url: str) -> ProcessedChunk:
        """Process a single chunk by retrieving metadata from Ollama."""
        extracted = await self.ollama_client.get_title_and_summary(chunk, url)
        embedding = await self.ollama_client.get_embedding(chunk)

        metadata = {
            "source": url,
            "chunk_size": len(chunk),
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "url_path": urlparse(url).path
        }

        return ProcessedChunk(
            url=url,
            chunk_number=chunk_number,
            title=extracted['title'],
            summary=extracted['summary'],
            content=chunk,
            metadata=metadata,
            embedding=embedding
        )

    def sanitize_filename(self, url: str) -> str:
        """Generate a safe filename from a given URL."""
        parsed = urlparse(url)
        raw_name = f"{parsed.netloc}_{parsed.path.strip('/')}"
        safe_name = re.sub(r'[^a-zA-Z0-9]', '_', raw_name).strip('_')[:200]
        return safe_name

    def save_chunk_to_file(self, chunk: ProcessedChunk, output_dir: pathlib.Path):
        """Save processed chunk data as a JSON file."""
        try:
            filename = f"{self.sanitize_filename(chunk.url)}_chunk_{chunk.chunk_number}.json"
            output_dir.mkdir(parents=True, exist_ok=True)

            with open(output_dir / filename, 'w', encoding='utf-8') as f:
                json.dump(chunk.__dict__, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved chunk {chunk.chunk_number} for {chunk.url} to {filename}")

        except Exception as e:
            logger.error(f"Error saving chunk to file: {e}")

    async def process_and_store_document(self, url: str, markdown: str, output_dir: pathlib.Path):
        """Process the entire document, chunking and saving asynchronously."""
        chunks = self.chunk_text(markdown)
        tasks = [self.process_chunk(chunk, i, url) for i, chunk in enumerate(chunks)]
        processed_chunks = await asyncio.gather(*tasks)

        for chunk in processed_chunks:
            self.save_chunk_to_file(chunk, output_dir)
