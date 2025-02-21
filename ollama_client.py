############################################################
#updated ollama_client.py to handle API responses correctly, 
# preventing TypeError: string indices must be integers, ensuring 
# proper dictionary checks, and managing JSON decoding errors effectively
############################################################

import asyncio
import httpx
import json
from typing import Dict, List
from logger_config import get_logger
from ollama_config import ollama_config

logger = get_logger(__name__)

class OllamaClient:
    def __init__(self):
        self.config = ollama_config  # Use the centralized configuration

    async def validate_config(self):
        """Validate Ollama configuration by checking API connection."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.config.base_url}/api/version")
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Invalid Ollama configuration: {e}")
                raise ValueError(f"Invalid Ollama configuration: {e}")

    async def get_title_and_summary(self, text: str, url: str) -> Dict[str, str]:
        """Extract title and summary using Ollama."""
        system_prompt = (
            "You are an AI that extracts titles and summaries from documentation chunks.\n"
            "You must respond with ONLY a JSON object in this exact format:\n"
            '{"title": "brief title here", "summary": "brief summary here"}\n'
            "For the title: If this seems like the start of a document, extract its title."
            " If it's a middle chunk, derive a descriptive title.\n"
            "For the summary: Create a concise summary of the main points in this chunk."
            " Keep both title and summary concise but informative."
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/generate",
                    json={
                        "model": self.config.model,
                        "prompt": f"{system_prompt}\n\nURL: {url}\n\nContent:\n{text[:1000]}...",
                        "stream": False
                    }
                )
                response.raise_for_status()
                
                try:
                    data = response.json().get("response")
                    if isinstance(data, dict):
                        return data
                    else:
                        return json.loads(data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from Ollama response for URL {url}. Content snippet: {text[:200]}...")
                    return {"title": "Error processing title", "summary": "Error processing summary"}

        except Exception as e:
            logger.error(f"Error getting title and summary for URL {url}: {e}")
            return {"title": "Error processing title", "summary": "Error processing summary"}

    async def get_embedding(self, text: str) -> List[float]:
        """Get embedding vector from Ollama with retry."""
        async def _get_embedding():
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.config.base_url}/api/embeddings",
                    json={"model": self.config.embed_model, "prompt": text}
                )
                response.raise_for_status()
                return response.json().get("embedding", [0] * 768)
        try:
            return await self.retry_with_backoff(_get_embedding)
        except Exception as e:
            logger.error(f"Error getting embedding after retries: {e}")
            return [0] * 768
    
    @staticmethod
    async def retry_with_backoff(func, max_retries=3):
        """Execute a function with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Max retries reached. Error: {e}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s due to error: {e}")
                await asyncio.sleep(wait_time)
