"""
Configuration management for ADB Helper.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

from .platform_paths import get_app_data_dir


@dataclass
class AppConfig:
    """Application configuration settings."""
    # UI Settings
    window_geometry: Optional[str] = None
    window_state: Optional[str] = None
    theme: str = "system"  # system, light, dark
    
    # ADB/Fastboot Settings
    adb_path: Optional[str] = None
    fastboot_path: Optional[str] = None
    auto_detect_binaries: bool = True
    
    # Safety Settings
    require_confirmations: bool = True
    enable_dev_mode: bool = False
    store_pairing_codes: bool = False
    
    # Network Settings
    default_adb_port: int = 5555
    connection_timeout: int = 10
    
    # Logging
    log_level: str = "INFO"
    max_log_files: int = 5
    
    # Feature Flags
    enable_wireless_debugging: bool = True
    enable_fastboot_features: bool = True
    enable_advanced_features: bool = False


class Config:
    """Configuration manager with automatic persistence."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_file = get_app_data_dir() / "config.json"
        self._config = AppConfig()
        self.load()
    
    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_file.exists():
            self.logger.info("No config file found, using defaults")
            self.save()  # Create default config
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update config with loaded data
            for key, value in data.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            self.logger.info("Using default configuration")
    
    def save(self) -> None:
        """Save configuration to file."""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Save config
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self._config), f, indent=2)
            
            self.logger.debug("Configuration saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            self.save()
        else:
            self.logger.warning(f"Unknown config key: {key}")
    
    def get_config(self) -> AppConfig:
        """Get the full configuration object."""
        return self._config
    
    def update_config(self, **kwargs) -> None:
        """Update multiple configuration values."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                self.logger.warning(f"Unknown config key: {key}")
        self.save()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults."""
        self._config = AppConfig()
        self.save()
        self.logger.info("Configuration reset to defaults")
