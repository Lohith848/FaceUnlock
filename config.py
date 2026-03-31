"""
Configuration Module for FaceUnlock
Centralizes all settings and provides easy customization.
"""

import os
import json
from pathlib import Path

# ── Base Paths ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# ── File Paths ──────────────────────────────────────────────────────────
PROFILE_PATH = DATA_DIR / "profile.pkl"
CONFIG_PATH = DATA_DIR / "config.json"
LOG_FILE = LOGS_DIR / "faceunlock.log"

# ── Default Configuration ──────────────────────────────────────────────
DEFAULT_CONFIG = {
    # Face Recognition Settings
    "face_recognition": {
        "tolerance": 0.50,              # Lower = stricter (0.45-0.55 recommended)
        "model": "hog",                 # "hog" (faster) or "cnn" (more accurate, requires GPU)
        "num_jitters": 1,               # Number of times to re-sample face for encoding
    },
    
    # Liveness Detection Settings
    "liveness": {
        "enabled": True,                # Enable blink detection for liveness
        "ear_threshold": 0.21,          # Eye aspect ratio threshold for blink detection
        "consecutive_frames": 3,        # Frames below threshold to register blink
        "blink_cooldown": 0.5,          # Seconds between blinks to avoid double-counting
    },
    
    # Camera Settings
    "camera": {
        "device_id": 0,                 # Camera device ID (0 = default webcam)
        "width": 640,                   # Frame width
        "height": 480,                  # Frame height
        "fps": 30,                      # Target FPS
    },
    
    # Unlock Settings
    "unlock": {
        "timeout_seconds": 8,           # Seconds before giving up
        "poll_interval": 1.0,           # Seconds between lock screen checks
        "lock_screen_delay": 1.5,       # Seconds to wait after lock screen detected
        "auto_start": True,             # Auto-start unlock on lock screen detection
    },
    
    # Registration Settings
    "registration": {
        "num_captures": 60,             # Number of face captures for registration
        "min_captures": 20,             # Minimum captures required for valid profile
        "capture_delay": 0.1,           # Delay between captures (seconds)
    },
    
    # Security Settings
    "security": {
        "password": "",                 # Windows password (leave empty to prompt)
        "use_credential_manager": False, # Use Windows Credential Manager (more secure)
        "max_attempts": 3,              # Max unlock attempts before lockout
        "lockout_duration": 300,        # Lockout duration in seconds (5 minutes)
    },
    
    # Logging Settings
    "logging": {
        "level": "INFO",                # DEBUG, INFO, WARNING, ERROR, CRITICAL
        "file_logging": True,           # Enable logging to file
        "console_logging": True,        # Enable logging to console
        "max_log_size_mb": 10,          # Maximum log file size in MB
        "backup_count": 5,              # Number of backup log files to keep
    },
    
    # UI Settings
    "ui": {
        "show_preview": True,           # Show camera preview window
        "show_landmarks": False,        # Show face landmarks on preview
        "show_ear": True,               # Show EAR value on preview
        "window_name": "FaceUnlock",    # Preview window name
    }
}


class Config:
    """Configuration manager for FaceUnlock."""
    
    def __init__(self, config_path=CONFIG_PATH):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self):
        """Load configuration from file or create with defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults (user config takes precedence)
                return self._merge_configs(DEFAULT_CONFIG, user_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"[!] Warning: Could not load config file: {e}")
                print("[*] Using default configuration.")
                return DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()
    
    def _merge_configs(self, default, user):
        """Recursively merge user config with defaults."""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self, config=None):
        """Save configuration to file."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=4)
            print(f"[+] Configuration saved to {self.config_path}")
        except IOError as e:
            print(f"[!] Error saving config: {e}")
    
    def get(self, *keys):
        """
        Get configuration value by key path.
        
        Args:
            *keys: Key path (e.g., 'face_recognition', 'tolerance')
        
        Returns:
            Configuration value or None if not found
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        return value
    
    def set(self, *keys, value):
        """
        Set configuration value by key path.
        
        Args:
            *keys: Key path (e.g., 'face_recognition', 'tolerance')
            value: Value to set
        """
        if len(keys) == 0:
            return
        
        config = self.config
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value
        self.save_config()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = DEFAULT_CONFIG.copy()
        self.save_config()
        print("[+] Configuration reset to defaults.")
    
    def validate(self):
        """
        Validate configuration values.
        
        Returns:
            tuple: (is_valid: bool, errors: list)
        """
        errors = []
        
        # Validate face recognition settings
        tolerance = self.get('face_recognition', 'tolerance')
        if not (0.3 <= tolerance <= 0.7):
            errors.append(f"Face recognition tolerance {tolerance} out of range (0.3-0.7)")
        
        # Validate liveness settings
        ear_threshold = self.get('liveness', 'ear_threshold')
        if not (0.1 <= ear_threshold <= 0.35):
            errors.append(f"EAR threshold {ear_threshold} out of range (0.1-0.35)")
        
        # Validate camera settings
        device_id = self.get('camera', 'device_id')
        if device_id < 0:
            errors.append(f"Invalid camera device ID: {device_id}")
        
        # Validate timeout
        timeout = self.get('unlock', 'timeout_seconds')
        if timeout < 1 or timeout > 60:
            errors.append(f"Timeout {timeout} out of range (1-60 seconds)")
        
        return len(errors) == 0, errors
    
    def display(self):
        """Display current configuration."""
        print("\n" + "="*60)
        print("FaceUnlock Configuration")
        print("="*60)
        
        for section, values in self.config.items():
            print(f"\n[{section.upper()}]")
            if isinstance(values, dict):
                for key, value in values.items():
                    print(f"  {key}: {value}")
            else:
                print(f"  {values}")
        
        print("\n" + "="*60)


# Global configuration instance
config = Config()


# ── Convenience Functions ──────────────────────────────────────────────
def get_config(*keys):
    """Get configuration value."""
    return config.get(*keys)


def set_config(*keys, value):
    """Set configuration value."""
    config.set(*keys, value=value)


def validate_config():
    """Validate configuration."""
    return config.validate()


def display_config():
    """Display configuration."""
    config.display()


if __name__ == "__main__":
    # Display current configuration when run directly
    display_config()
    
    # Validate configuration
    is_valid, errors = validate_config()
    if is_valid:
        print("\n[✓] Configuration is valid!")
    else:
        print("\n[✗] Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
