"""
Configuration management for Precog API client
"""

import os
import json
from typing import Dict, Any, Optional


class PrecogConfig:
    """Configuration manager for Precog API client"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_file: Path to config file (defaults to ~/.precog/config.json)
        """
        self.config_file = config_file or os.path.expanduser("~/.precog/config.json")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with defaults"""
        defaults = {
            "wallet_name": None,
            "token_file": os.path.expanduser("~/.precog/tokens.json")
        }
        
        # Try to load from config file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    defaults.update(file_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
        
        return defaults
    
    def save_config(self):
        """Save current configuration to file"""
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value
    
    def get_wallet_name(self) -> Optional[str]:
        """Get wallet name"""
        return self.get("wallet_name")
    
    
    def get_token_file(self) -> str:
        """Get token file path"""
        return self.get("token_file")
    
    def is_configured(self) -> bool:
        """Check if basic configuration is present"""
        return self.get_wallet_name() is not None
    
    def show_config(self):
        """Display current configuration"""
        print("Current configuration:")
        print(f"  Wallet name: {self.get_wallet_name() or 'Not set'}")
        print(f"  Token file: {self.get_token_file()}")
        print(f"  Config file: {self.config_file}")


# Global config instance
_config = None

def get_config() -> PrecogConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = PrecogConfig()
    return _config