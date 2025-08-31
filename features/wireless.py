"""
Wireless ADB debugging management.
"""

import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from dataclasses import dataclass

from adb_tools.adb import ADBWrapper
from utils.secure_store import SecureStore


@dataclass
class WirelessDevice:
    """Represents a wireless ADB device."""
    ip: str
    port: int
    serial: Optional[str] = None
    name: Optional[str] = None
    paired: bool = False


class WirelessManager(QObject):
    """Manages wireless ADB connections and pairing."""
    
    pairing_progress = pyqtSignal(str)  # status message
    pairing_completed = pyqtSignal(bool, str)  # success, message
    connection_status = pyqtSignal(str, bool)  # device_id, connected
    
    def __init__(self, adb_wrapper: ADBWrapper, secure_store: SecureStore):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.secure_store = secure_store
        self.known_devices: List[WirelessDevice] = []
    
    def pair_device(self, ip: str, port: int, pairing_code: str) -> Tuple[bool, str]:
        """
        Pair with device using pairing code (Android 11+).
        
        Returns:
            (success, message)
        """
        try:
            self.pairing_progress.emit("Attempting to pair...")
            
            result = self.adb_wrapper.pair(ip, port, pairing_code)
            
            if result.success:
                # Extract connection info from output
                connection_info = self._parse_pairing_output(result.stdout)
                if connection_info:
                    device = WirelessDevice(
                        ip=ip,
                        port=connection_info.get('port', 5555),
                        paired=True
                    )
                    self.known_devices.append(device)
                
                message = "Device paired successfully!"
                self.pairing_completed.emit(True, message)
                return True, message
            else:
                error_msg = self._parse_error_message(result.stderr)
                self.pairing_completed.emit(False, error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Pairing failed: {str(e)}"
            self.logger.error(error_msg)
            self.pairing_completed.emit(False, error_msg)
            return False, error_msg
    
    def connect_device(self, ip: str, port: int = 5555) -> Tuple[bool, str]:
        """
        Connect to device over TCP/IP.
        
        Returns:
            (success, message)
        """
        try:
            result = self.adb_wrapper.connect(ip, port)
            
            if result.success:
                message = f"Connected to {ip}:{port}"
                self.connection_status.emit(f"{ip}:{port}", True)
                return True, message
            else:
                error_msg = self._parse_error_message(result.stderr)
                self.connection_status.emit(f"{ip}:{port}", False)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Connection failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def disconnect_device(self, ip: str, port: int = 5555) -> Tuple[bool, str]:
        """Disconnect from TCP/IP device."""
        try:
            result = self.adb_wrapper.disconnect(ip, port)
            
            if result.success:
                message = f"Disconnected from {ip}:{port}"
                self.connection_status.emit(f"{ip}:{port}", False)
                return True, message
            else:
                error_msg = self._parse_error_message(result.stderr)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Disconnection failed: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def enable_tcpip_mode(self, port: int = 5555, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Enable TCP/IP mode on USB-connected device."""
        try:
            result = self.adb_wrapper.tcpip(port, serial)
            
            if result.success:
                message = f"TCP/IP mode enabled on port {port}"
                return True, message
            else:
                error_msg = self._parse_error_message(result.stderr)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Failed to enable TCP/IP mode: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def discover_wireless_devices(self) -> List[WirelessDevice]:
        """Discover wireless ADB devices on network."""
        # TODO: Implement network scanning for ADB devices
        # This would involve scanning common ports on local network
        return self.known_devices
    
    def _parse_pairing_output(self, output: str) -> Optional[Dict[str, Any]]:
        """Parse pairing command output to extract connection info."""
        # Example output: "Successfully paired to 192.168.1.100:5555 [guid=adb-ABCD1234-EFGH56]"
        match = re.search(r'Successfully paired to ([\d.]+):(\d+)', output)
        if match:
            return {
                'ip': match.group(1),
                'port': int(match.group(2))
            }
        return None
    
    def _parse_error_message(self, stderr: str) -> str:
        """Parse error message and provide user-friendly description."""
        if "failed to authenticate" in stderr.lower():
            return "Authentication failed. Check pairing code and try again."
        elif "connection refused" in stderr.lower():
            return "Connection refused. Ensure wireless debugging is enabled."
        elif "no route to host" in stderr.lower():
            return "Cannot reach device. Check IP address and network connection."
        elif "timeout" in stderr.lower():
            return "Connection timed out. Device may be unreachable."
        else:
            return stderr.strip() or "Unknown error occurred"
