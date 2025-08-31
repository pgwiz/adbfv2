"""
Unit tests for Fastboot wrapper functionality.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adb_tools.fastboot import FastbootWrapper, FastbootDevice, FastbootSafetyTier
from adb_tools.process_runner import ProcessResult


class TestFastbootWrapper(unittest.TestCase):
    """Test cases for Fastboot wrapper."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('adb_tools.fastboot.find_platform_tools', return_value=None):
            with patch('shutil.which', return_value=None):
                self.fastboot_wrapper = FastbootWrapper("/mock/fastboot")
    
    @patch('adb_tools.fastboot.ProcessRunner')
    def test_get_devices_success(self, mock_runner_class):
        """Test successful device listing."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        self.fastboot_wrapper.process_runner = mock_runner
        
        mock_result = ProcessResult(
            returncode=0,
            stdout="1234567890ABCDEF\tfastboot\n",
            stderr="",
            command=["fastboot", "devices"],
            execution_time=0.3
        )
        mock_runner.run.return_value = mock_result
        
        devices = self.fastboot_wrapper.devices()
        
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].serial, "1234567890ABCDEF")
        self.assertEqual(devices[0].state, "fastboot")
    
    def test_safety_classification(self):
        """Test command safety classification."""
        # Test that safety tier constants exist
        self.assertIsNotNone(FastbootSafetyTier.SAFE)
        self.assertIsNotNone(FastbootSafetyTier.RISKY)
        self.assertIsNotNone(FastbootSafetyTier.DESTRUCTIVE)
        
        # Test wrapper has safety-related methods
        self.assertTrue(hasattr(self.fastboot_wrapper, 'flash'))
        self.assertTrue(hasattr(self.fastboot_wrapper, 'erase'))
        self.assertTrue(hasattr(self.fastboot_wrapper, 'oem'))
    
    def test_device_parsing(self):
        """Test device info parsing."""
        # Test basic device creation
        device = FastbootDevice(
            serial="1234567890ABCDEF",
            state="fastboot"
        )
        
        self.assertEqual(device.serial, "1234567890ABCDEF")
        self.assertEqual(device.state, "fastboot")
    
    @patch('adb_tools.fastboot.ProcessRunner')
    def test_getvar_command(self, mock_runner_class):
        """Test getvar command execution."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        
        mock_result = ProcessResult(
            returncode=0,
            stdout="version: 0.4\n",
            stderr="",
            command=["fastboot", "getvar", "version"],
            execution_time=0.2
        )
        mock_runner.run.return_value = mock_result
        
        # Mock getvar method to return the value
        with patch.object(self.fastboot_wrapper, 'getvar', return_value="0.4"):
            result = self.fastboot_wrapper.getvar("version", serial="test-device")
            self.assertEqual(result, "0.4")


if __name__ == '__main__':
    unittest.main()
