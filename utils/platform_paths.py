"""
Cross-platform path utilities for application data and configuration.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_app_data_dir() -> Path:
    """Get the application data directory for the current platform."""
    if sys.platform == "win32":
        # Windows: %APPDATA%\ADB Helper
        base = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        return Path(base) / "ADB Helper"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/ADB Helper
        return Path.home() / "Library" / "Application Support" / "ADB Helper"
    else:
        # Linux/Unix: ~/.config/adb-helper
        xdg_config = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return Path(xdg_config) / "adb-helper"


def get_cache_dir() -> Path:
    """Get the cache directory for the current platform."""
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\ADB Helper\Cache
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        return Path(base) / "ADB Helper" / "Cache"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Caches/ADB Helper
        return Path.home() / "Library" / "Caches" / "ADB Helper"
    else:
        # Linux/Unix: ~/.cache/adb-helper
        xdg_cache = os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache"))
        return Path(xdg_cache) / "adb-helper"


def get_logs_dir() -> Path:
    """Get the logs directory for the current platform."""
    if sys.platform == "win32":
        # Windows: %LOCALAPPDATA%\ADB Helper\Logs
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
        return Path(base) / "ADB Helper" / "Logs"
    elif sys.platform == "darwin":
        # macOS: ~/Library/Logs/ADB Helper
        return Path.home() / "Library" / "Logs" / "ADB Helper"
    else:
        # Linux/Unix: ~/.local/share/adb-helper/logs
        xdg_data = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))
        return Path(xdg_data) / "adb-helper" / "logs"


def find_android_sdk_paths() -> list[Path]:
    """Find common Android SDK installation paths."""
    paths = []
    
    if sys.platform == "win32":
        # Windows common paths
        possible_paths = [
            Path.home() / "AppData" / "Local" / "Android" / "Sdk",
            Path("C:") / "Android" / "Sdk",
            Path("C:") / "Program Files" / "Android" / "Sdk",
            Path("C:") / "Program Files (x86)" / "Android" / "Sdk",
        ]
    elif sys.platform == "darwin":
        # macOS common paths
        possible_paths = [
            Path.home() / "Library" / "Android" / "sdk",
            Path("/Applications/Android Studio.app/Contents/sdk"),
            Path("/usr/local/android-sdk"),
        ]
    else:
        # Linux common paths
        possible_paths = [
            Path.home() / "Android" / "Sdk",
            Path("/opt/android-sdk"),
            Path("/usr/local/android-sdk"),
            Path.home() / ".android-sdk",
        ]
    
    # Add ANDROID_HOME if set
    android_home = os.environ.get("ANDROID_HOME")
    if android_home:
        possible_paths.insert(0, Path(android_home))
    
    # Filter to existing paths
    for path in possible_paths:
        if path.exists() and path.is_dir():
            paths.append(path)
    
    return paths


def find_platform_tools() -> Optional[Path]:
    """Find platform-tools directory containing ADB and Fastboot."""
    # Check PATH first
    adb_in_path = None
    try:
        import shutil
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            return Path(adb_in_path).parent
    except Exception:
        pass
    
    # Check SDK paths
    for sdk_path in find_android_sdk_paths():
        platform_tools = sdk_path / "platform-tools"
        if platform_tools.exists():
            adb_exe = platform_tools / ("adb.exe" if sys.platform == "win32" else "adb")
            if adb_exe.exists():
                return platform_tools
    
    return None


def find_adb_binary() -> Optional[Path]:
    """Find ADB binary path."""
    platform_tools = find_platform_tools()
    if platform_tools:
        adb_exe = platform_tools / ("adb.exe" if sys.platform == "win32" else "adb")
        if adb_exe.exists():
            return adb_exe
    
    # Check PATH
    try:
        import shutil
        adb_path = shutil.which("adb")
        if adb_path:
            return Path(adb_path)
    except Exception:
        pass
    
    return None


def find_fastboot_binary() -> Optional[Path]:
    """Find Fastboot binary path."""
    platform_tools = find_platform_tools()
    if platform_tools:
        fastboot_exe = platform_tools / ("fastboot.exe" if sys.platform == "win32" else "fastboot")
        if fastboot_exe.exists():
            return fastboot_exe
    
    # Check PATH
    try:
        import shutil
        fastboot_path = shutil.which("fastboot")
        if fastboot_path:
            return Path(fastboot_path)
    except Exception:
        pass
    
    return None
