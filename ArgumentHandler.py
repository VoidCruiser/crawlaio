#################################################################################
#Fixes Applied:
#
#    Ensures all expected keys exist, even if the config file is incomplete or missing.
#    Logs warnings for missing keys and errors for corrupted JSON.
#    Prevents {} from being returned.

import argparse
import sys
import json
import os
from logger_config import get_logger

CONFIG_FILE = "config.json"

# Define default configuration values
DEFAULT_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "embed_model": "nomic-embed-text",
    "url": "https://example.com",
    "max_concurrent": 5,
    "max_retries": 3,
    "output_dir": "crawled_data"
}

logger = get_logger(__name__)

def load_config():
    """Load configuration from config.json, ensuring missing keys get default values in memory only."""
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"{CONFIG_FILE} not found. Using default configuration.")
        return DEFAULT_CONFIG.copy()  # Return a copy to prevent accidental mutation

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config_data = json.load(f)

        # Fill missing keys in-memory without modifying config.json
        updated_config = {key: config_data.get(key, DEFAULT_CONFIG[key]) for key in DEFAULT_CONFIG}

        return updated_config  # This copy prevents overwriting the file

    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Invalid {CONFIG_FILE}: {e}. Using default configuration.")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Save configuration back to config.json, only if the user explicitly changes values."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Failed to save {CONFIG_FILE}: {e}")

class ArgumentHandler:
    @staticmethod
    def prompt_for_arguments() -> argparse.Namespace:
        """Prompt user for crawler and Ollama configuration interactively, without saving defaults."""
        config = load_config()

        print("\n=== Web Crawler Configuration ===")
        url = input(f"Enter the starting URL to crawl [{config['url']}]: ").strip() or config["url"]

        max_concurrent = input(f"Enter maximum concurrent crawls [{config['max_concurrent']}]: ").strip()
        max_concurrent = int(max_concurrent) if max_concurrent.isdigit() else config["max_concurrent"]

        max_retries = input(f"Enter maximum retry attempts [{config['max_retries']}]: ").strip()
        max_retries = int(max_retries) if max_retries.isdigit() else config["max_retries"]

        output_dir = input(f"Enter output directory [{config['output_dir']}]: ").strip() or config["output_dir"]

        print("\n=== Ollama Configuration ===")
        ollama_url = input(f"Enter Ollama API base URL [{config['base_url']}]: ").strip() or config["base_url"]
        model = input(f"Enter Ollama model for text generation [{config['model']}]: ").strip() or config["model"]
        embed_model = input(f"Enter Ollama model for embeddings [{config['embed_model']}]: ").strip() or config["embed_model"]

        # Create a new config dictionary that only includes **non-default** user changes
        updated_config = {
            "url": url if url != DEFAULT_CONFIG["url"] else config["url"],
            "max_concurrent": max_concurrent if max_concurrent != DEFAULT_CONFIG["max_concurrent"] else config["max_concurrent"],
            "max_retries": max_retries if max_retries != DEFAULT_CONFIG["max_retries"] else config["max_retries"],
            "output_dir": output_dir if output_dir != DEFAULT_CONFIG["output_dir"] else config["output_dir"],
            "base_url": ollama_url if ollama_url != DEFAULT_CONFIG["base_url"] else config["base_url"],
            "model": model if model != DEFAULT_CONFIG["model"] else config["model"],
            "embed_model": embed_model if embed_model != DEFAULT_CONFIG["embed_model"] else config["embed_model"]
        }

        # Only save if user changes values from default
        if updated_config != DEFAULT_CONFIG:
            save_config(updated_config)

        return argparse.Namespace(**updated_config)

    @staticmethod
    def parse_arguments() -> argparse.Namespace:
        """Parse command-line arguments, using config.json for defaults."""
        config = load_config()
        
        parser = argparse.ArgumentParser(description='Web crawler for documentation sites')
        parser.add_argument('url', nargs='?', default=config.get("url"), help='Starting URL to crawl')
        parser.add_argument('--max-retries', type=int, default=config.get("max_retries"), help='Max retry attempts (default: 3)')
        parser.add_argument('--max-concurrent', type=int, default=config.get("max_concurrent"), help='Max concurrent crawls (default: 5)')
        parser.add_argument('--ollama-url', default=config.get("base_url"), help='Ollama API URL')
        parser.add_argument('--ollama-model', default=config.get("model"), help='Ollama model for text generation')
        parser.add_argument('--ollama-embed-model', default=config.get("embed_model"), help='Ollama model for embeddings')
        parser.add_argument('--output-dir', default=config.get("output_dir"), help='Output directory')

        args = parser.parse_args()

        return args

    @staticmethod
    def get_arguments() -> argparse.Namespace:
        """Determine whether to use command-line arguments or interactive input."""
        if len(sys.argv) > 1:
            return ArgumentHandler.parse_arguments()
        else:
            return ArgumentHandler.prompt_for_arguments()

