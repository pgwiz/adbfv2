#!/usr/bin/env python3
"""
Advanced ADB + Fastboot Desktop App
Entry point for the application.
"""

import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import main

if __name__ == "__main__":
    main()
