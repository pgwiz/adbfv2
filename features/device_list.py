"""
Device list management and monitoring.
"""

import logging
from typing import List, Optional, Dict, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from dataclasses import dataclass
from datetime import datetime

from adb_tools.adb import ADBWrapper, ADBDevice
from adb_tools.fastboot import FastbootWrapper, FastbootDevice


@dataclass
class DeviceSnapshot:
    """Snapshot of device state at a point in time."""
    timestamp: datetime
    adb_devices: List[ADBDevice]
    fastboot_devices: List[FastbootDevice]
    
    @property
    def total_devices(self) -> int:
        return len(self.adb_devices) + len(self.fastboot_devices)


class DeviceManager(QObject):
    """Manages device discovery and monitoring."""
    
    devices_changed = pyqtSignal(list, list)  # adb_devices, fastboot_devices
    device_connected = pyqtSignal(str, str)  # serial, type (adb/fastboot)
    device_disconnected = pyqtSignal(str, str)  # serial, type
    
    def __init__(self, adb_wrapper: Optional[ADBWrapper], fastboot_wrapper: Optional[FastbootWrapper]):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.fastboot_wrapper = fastboot_wrapper
        
        self.last_snapshot: Optional[DeviceSnapshot] = None
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        
        # Device info cache
        self._device_info_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timeout = 30  # seconds
    
    def start_monitoring(self, interval_ms: int = 3000):
        """Start automatic device monitoring."""
        self.refresh_timer.start(interval_ms)
        self.refresh_devices()  # Initial refresh
        self.logger.info(f"Device monitoring started (interval: {interval_ms}ms)")
    
    def stop_monitoring(self):
        """Stop automatic device monitoring."""
        self.refresh_timer.stop()
        self.logger.info("Device monitoring stopped")
    
    def refresh_devices(self):
        """Refresh device lists and detect changes."""
        try:
            adb_devices = []
            fastboot_devices = []
            
            # Get ADB devices
            if self.adb_wrapper and self.adb_wrapper.is_available():
                adb_devices = self.adb_wrapper.devices(long_output=True)
            
            # Get Fastboot devices
            if self.fastboot_wrapper and self.fastboot_wrapper.is_available():
                fastboot_devices = self.fastboot_wrapper.devices(long_output=True)
            
            # Create new snapshot
            new_snapshot = DeviceSnapshot(
                timestamp=datetime.now(),
                adb_devices=adb_devices,
                fastboot_devices=fastboot_devices
            )
            
            # Detect changes
            if self.last_snapshot:
                self._detect_device_changes(self.last_snapshot, new_snapshot)
            
            self.last_snapshot = new_snapshot
            self.devices_changed.emit(adb_devices, fastboot_devices)
            
        except Exception as e:
            self.logger.error(f"Device refresh failed: {e}")
    
    def _detect_device_changes(self, old_snapshot: DeviceSnapshot, new_snapshot: DeviceSnapshot):
        """Detect and emit device connection/disconnection events."""
        # Track ADB device changes
        old_adb_serials = {d.serial for d in old_snapshot.adb_devices}
        new_adb_serials = {d.serial for d in new_snapshot.adb_devices}
        
        for serial in new_adb_serials - old_adb_serials:
            self.device_connected.emit(serial, "adb")
        
        for serial in old_adb_serials - new_adb_serials:
            self.device_disconnected.emit(serial, "adb")
        
        # Track Fastboot device changes
        old_fb_serials = {d.serial for d in old_snapshot.fastboot_devices}
        new_fb_serials = {d.serial for d in new_snapshot.fastboot_devices}
        
        for serial in new_fb_serials - old_fb_serials:
            self.device_connected.emit(serial, "fastboot")
        
        for serial in old_fb_serials - new_fb_serials:
            self.device_disconnected.emit(serial, "fastboot")
    
    def get_device_info(self, serial: str, device_type: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get cached or fresh device information."""
        cache_key = f"{device_type}_{serial}"
        
        # Check cache
        if not force_refresh and cache_key in self._device_info_cache:
            cached_info, timestamp = self._device_info_cache[cache_key]
            age = (datetime.now() - timestamp).total_seconds()
            if age < self._cache_timeout:
                return cached_info
        
        # Fetch fresh info
        info = {}
        try:
            if device_type == "adb" and self.adb_wrapper:
                info = self.adb_wrapper.get_device_info(serial)
            elif device_type == "fastboot" and self.fastboot_wrapper:
                info = self.fastboot_wrapper.get_device_info(serial)
            
            # Cache the result
            self._device_info_cache[cache_key] = (info, datetime.now())
            
        except Exception as e:
            self.logger.error(f"Failed to get device info for {serial}: {e}")
        
        return info
    
    def clear_cache(self):
        """Clear device info cache."""
        self._device_info_cache.clear()
        self.logger.debug("Device info cache cleared")
    
    def get_current_devices(self) -> tuple[List[ADBDevice], List[FastbootDevice]]:
        """Get current device lists."""
        if self.last_snapshot:
            return self.last_snapshot.adb_devices, self.last_snapshot.fastboot_devices
        return [], []
