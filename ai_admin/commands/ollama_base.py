import os
import json
from typing import Dict, Any, Optional

class OllamaConfig:
    """Configuration manager for Ollama settings."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize Ollama configuration.
        
        Args:
            config_path: Path to config file (optional)
        """
        self.config_path = config_path or "/app/config/config.json"
        self._config = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self._config is None:
            try:
                with open(self.config_path, 'r') as f:
                    self._config = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                self._config = {}
        return self._config
    
    def get_ollama_config(self) -> Dict[str, Any]:
        """Get Ollama-specific configuration."""
        config = self.load_config()
        return config.get('ollama', {})
    
    def get_models_cache_path(self) -> str:
        """Get models cache path from config or environment."""
        config = self.get_ollama_config()
        return config.get('models_cache_path') or os.getenv('OLLAMA_MODELS', '/app/models')
    
    def get_ollama_host(self) -> str:
        """Get Ollama host from config or environment."""
        config = self.get_ollama_config()
        return config.get('host') or os.getenv('OLLAMA_HOST', 'localhost')
    
    def get_ollama_port(self) -> int:
        """Get Ollama port from config or environment."""
        config = self.get_ollama_config()
        return int(config.get('port') or os.getenv('OLLAMA_PORT', '11434'))
    
    def get_ollama_timeout(self) -> int:
        """Get Ollama timeout from config."""
        config = self.get_ollama_config()
        return int(config.get('timeout', 30))
    
    def get_ollama_url(self) -> str:
        """Get full Ollama API URL."""
        host = self.get_ollama_host()
        port = self.get_ollama_port()
        return f"http://{host}:{port}"

# Global config instance
ollama_config = OllamaConfig() 