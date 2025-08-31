"""
Unit tests for ADB wrapper functionality.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adb_tools.adb import ADBWrapper, ADBDevice, ADBState
from adb_tools.process_runner import ProcessResult


class TestADBWrapper(unittest.TestCase):
    """Test cases for ADB wrapper."""
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('adb_tools.adb.find_platform_tools', return_value=None):
            with patch('shutil.which', return_value=None):
                self.adb_wrapper = ADBWrapper("/mock/adb")
    
    @patch('adb_tools.adb.ProcessRunner')
    def test_get_devices_success(self, mock_runner_class):
        """Test successful device listing."""
        # Mock process runner
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        self.adb_wrapper.process_runner = mock_runner
        
        # Mock successful result
        mock_result = ProcessResult(
            returncode=0,
            stdout="List of devices attached\nemulator-5554\tdevice\n192.168.1.100:5555\tdevice\n",
            stderr="",
            command=["adb", "devices"],
            execution_time=0.5
        )
        mock_runner.run.return_value = mock_result
        
        # Test
        devices = self.adb_wrapper.devices()
        
        # Verify
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].serial, "emulator-5554")
        self.assertEqual(devices[0].state, ADBState.DEVICE)
        self.assertEqual(devices[1].serial, "192.168.1.100:5555")
        self.assertEqual(devices[1].state, ADBState.DEVICE)
    
    @patch('adb_tools.adb.ProcessRunner')
    def test_get_devices_empty(self, mock_runner_class):
        """Test empty device list."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        self.adb_wrapper.process_runner = mock_runner
        
        mock_result = ProcessResult(
            returncode=0,
            stdout="List of devices attached\n\n",
            stderr="",
            command=["adb", "devices"],
            execution_time=0.1
        )
        mock_runner.run.return_value = mock_result
        
        devices = self.adb_wrapper.devices()
        self.assertEqual(len(devices), 0)
    
    @patch('adb_tools.adb.ProcessRunner')
    def test_install_apk_success(self, mock_runner_class):
        """Test successful APK installation."""
        mock_runner = Mock()
        mock_runner_class.return_value = mock_runner
        self.adb_wrapper.process_runner = mock_runner
        
        mock_result = ProcessResult(
            returncode=0,
            stdout="Success\n",
            stderr="",
            command=["adb", "install"],
            execution_time=5.0
        )
        mock_runner.run.return_value = mock_result
        
        result = self.adb_wrapper.install("/path/to/app.apk", serial="test-device")
        
        self.assertTrue(result.success)
        self.assertIn("Success", result.stdout)
    
    def test_device_parsing(self):
        """Test device info parsing."""
        # Test basic device creation
        device = ADBDevice(
            serial="emulator-5554",
            state=ADBState.DEVICE,
            product="sdk_gphone64_x86_64",
            model="sdk_gphone64_x86_64",
            device="emulator64_x86_64_arm64"
        )
        
        self.assertEqual(device.serial, "emulator-5554")
        self.assertEqual(device.state, ADBState.DEVICE)
        self.assertEqual(device.product, "sdk_gphone64_x86_64")
        self.assertEqual(device.model, "sdk_gphone64_x86_64")
        self.assertEqual(device.device, "emulator64_x86_64_arm64")


if __name__ == '__main__':
    unittest.main()
