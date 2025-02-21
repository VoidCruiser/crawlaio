###this version filters out unrelated keys (like url, max_concurrent, max_retries),
# ensuring only base_url, model, and embed_model are loaded into OllamaConfig.
###edit 2 Merged the new OllamaConfig logic into ollama_config.py, ensuring only
# relevant keys (base_url, model, embed_model) are loaded from config.json, missing 
# values are filled with defaults, and unnecessary keys are filtered out. Added logging 
# for warnings, errors, and automatic updates to config.json when needed.

import json
from dataclasses import dataclass
from pathlib import Path
from logger_config import get_logger

CONFIG_PATH = Path(__file__).parent / "config.json"

DEFAULT_OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "llama3.2:3b",
    "embed_model": "nomic-embed-text"
}

logger = get_logger(__name__)

@dataclass
class OllamaConfig:
    base_url: str
    model: str
    embed_model: str

    @classmethod
    def load_config(cls, path=CONFIG_PATH):
        """Load configuration from config.json, ensuring only relevant keys are kept."""
        if not path.exists():
            logger.warning(f"{path} not found. Using default Ollama configuration.")
            return cls(**DEFAULT_OLLAMA_CONFIG)

        try:
            with open(path, "r", encoding="utf-8") as file:
                config_data = json.load(file)

            # Only keep the necessary keys and fill in missing ones
            filtered_config = {key: config_data.get(key, DEFAULT_OLLAMA_CONFIG[key]) for key in DEFAULT_OLLAMA_CONFIG}

            # Avoid unnecessary overwrites
            if filtered_config != config_data:
                logger.info(f"Updating {path} with filtered Ollama configuration.")
                with open(path, "w", encoding="utf-8") as file:
                    json.dump(filtered_config, file, indent=2)

            return cls(**filtered_config)

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Invalid {path}: {e}. Using default Ollama configuration.")
            return cls(**DEFAULT_OLLAMA_CONFIG)

# Preloaded instance for global usage
ollama_config = OllamaConfig.load_config()

