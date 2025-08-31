#!/usr/bin/env python3
"""
Advanced ADB + Fastboot Desktop App
Application bootstrap and main entry point.
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt, QDir
from PyQt6.QtGui import QIcon

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow
from utils.config import Config
from utils.logger import setup_logging, get_logger
from utils.platform_paths import get_app_data_dir, find_adb_binary, find_fastboot_binary
from adb_tools.adb import ADBWrapper
from adb_tools.fastboot import FastbootWrapper


def setup_app_environment():
    """Setup application environment and directories."""
    # Ensure app data directory exists
    app_data_dir = get_app_data_dir()
    app_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup logging
    log_file = app_data_dir / "adb_helper.log"
    setup_logging(log_file)
    
    # Initialize config
    config = Config()
    
    return config


def check_dependencies():
    """Check for required dependencies and ADB/Fastboot binaries."""
    try:
        from adb_tools.adb import ADBWrapper
        from adb_tools.fastboot import FastbootWrapper
        
        adb = ADBWrapper()
        fastboot = FastbootWrapper()
        
        adb_available = adb.find_binary() is not None
        fastboot_available = fastboot.find_binary() is not None
        
        return adb_available, fastboot_available
    except ImportError as e:
        logging.error(f"Missing dependencies: {e}")
        return False, False


def show_dependency_warning(adb_available, fastboot_available):
    """Show warning dialog for missing dependencies."""
    if not adb_available and not fastboot_available:
        title = "ADB and Fastboot Not Found"
        message = """Neither ADB nor Fastboot were found on your system.

Please install Android SDK Platform Tools:
• Download from: https://developer.android.com/studio/releases/platform-tools
• Extract to a folder and add to your system PATH
• Or install Android Studio which includes these tools

The app will continue to run but functionality will be limited."""
    elif not adb_available:
        title = "ADB Not Found"
        message = """ADB (Android Debug Bridge) was not found on your system.

Please install Android SDK Platform Tools to use ADB features.
Fastboot functionality will still be available."""
    elif not fastboot_available:
        title = "Fastboot Not Found"
        message = """Fastboot was not found on your system.

Please install Android SDK Platform Tools to use Fastboot features.
ADB functionality will still be available."""
    else:
        return  # Both available
    
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Icon.Warning)
    msg_box.setWindowTitle(title)
    msg_box.setText(message)
    msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg_box.exec()


def main():
    """Main application entry point."""
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("ADB Helper")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ADB Helper")
    app.setOrganizationDomain("adbhelper.local")
    
    # Set application icon if available
    icon_path = Path(__file__).parent / "resources" / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Setup environment
    try:
        config = setup_app_environment()
        logging.info("ADB Helper starting up...")
        
        # Check dependencies
        adb_available, fastboot_available = check_dependencies()
        if not (adb_available or fastboot_available):
            show_dependency_warning(adb_available, fastboot_available)
        
        # Create and show main window
        main_window = MainWindow(config, adb_available, fastboot_available)
        main_window.show()
        
        # Start event loop
        return app.exec()
        
    except Exception as e:
        logging.critical(f"Failed to start application: {e}")
        QMessageBox.critical(
            None,
            "Startup Error",
            f"Failed to start ADB Helper:\n\n{str(e)}\n\nCheck the log file for details."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
