#!/usr/bin/env python3
"""
Build script for creating ADB Helper executables.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def build_executable():
    """Build standalone executable using PyInstaller."""
    
    # Ensure PyInstaller is available
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build configuration
    app_name = "ADBHelper"
    main_script = "app.py"
    
    # PyInstaller arguments
    args = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", app_name,
        "--add-data", "docs;docs",
        "--add-data", "resources;resources",
        "--hidden-import", "PyQt6.QtCore",
        "--hidden-import", "PyQt6.QtWidgets", 
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "cryptography",
        "--hidden-import", "keyring",
        main_script
    ]
    
    # Add icon if available
    icon_path = Path("resources/icon.ico")
    if icon_path.exists():
        args.extend(["--icon", str(icon_path)])
    
    print(f"Building {app_name} executable...")
    print(f"Command: {' '.join(args)}")
    
    try:
        subprocess.check_call(args)
        print(f"\n✅ Build completed successfully!")
        print(f"Executable: dist/{app_name}.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False
    
    return True


def create_installer():
    """Create installer package (placeholder)."""
    print("Installer creation not implemented yet.")
    print("Use the executable from dist/ folder for distribution.")


if __name__ == "__main__":
    if build_executable():
        create_installer()
