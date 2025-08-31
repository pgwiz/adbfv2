"""
Fastboot wrapper with safety-first design and comprehensive command support.
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
from utils.platform_paths import find_platform_tools
from adb_tools.process_runner import ProcessRunner, ProcessResult


class FastbootSafetyTier(Enum):
    """Safety tiers for fastboot operations."""
    SAFE = "safe"           # Standard confirmation
    RISKY = "risky"         # Confirmation dialog
    DESTRUCTIVE = "destructive"  # Device serial + "I UNDERSTAND" typed


@dataclass
class FastbootDevice:
    """Represents a Fastboot device."""
    serial: str
    state: str = "fastboot"
    
    
@dataclass
class SafetyInfo:
    """Safety information for fastboot commands."""
    tier: FastbootSafetyTier
    warning_message: str
    requires_serial: bool = False
    requires_typed_confirmation: bool = False


class FastbootWrapper:
    """Comprehensive Fastboot wrapper with safety-first design."""
    
    # Safety classification for commands
    SAFETY_MAP = {
        # DESTRUCTIVE - Require device serial + "I UNDERSTAND"
        "flashing unlock": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ CRITICAL: This will UNLOCK the bootloader and ERASE ALL DATA!\n"
            "This action is IRREVERSIBLE and will:\n"
            "• Delete all user data, apps, and settings\n"
            "• Void warranty on most devices\n"
            "• Make device vulnerable to tampering\n"
            "• May permanently brick your device if interrupted",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        "flashing lock": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ CRITICAL: This will LOCK the bootloader!\n"
            "This may BRICK your device if:\n"
            "• Custom recovery is installed\n"
            "• System partition is modified\n"
            "• Boot image is not stock\n"
            "Only proceed if you're certain the device has stock firmware!",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        "flashing unlock_critical": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ CRITICAL: This will unlock CRITICAL partitions!\n"
            "This is EXTREMELY DANGEROUS and can permanently brick your device.\n"
            "Only proceed if you are an experienced developer and know exactly what you're doing.",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        "erase": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ DESTRUCTIVE: This will PERMANENTLY ERASE the specified partition!\n"
            "Erasing critical partitions (bootloader, recovery, system) can brick your device.\n"
            "Make sure you have backups and recovery plan!",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        "format": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ DESTRUCTIVE: This will FORMAT the specified partition!\n"
            "All data on the partition will be permanently lost.\n"
            "Ensure you have proper backups before proceeding!",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        "wipe_super": SafetyInfo(
            FastbootSafetyTier.DESTRUCTIVE,
            "⚠️ DESTRUCTIVE: This will WIPE the super partition!\n"
            "This will destroy all logical partitions (system, vendor, product).\n"
            "Your device will be completely unusable until you flash new firmware!",
            requires_serial=True,
            requires_typed_confirmation=True
        ),
        
        # RISKY - Require confirmation dialog
        "flashall": SafetyInfo(
            FastbootSafetyTier.RISKY,
            "⚠️ RISKY: This will flash all partitions from $ANDROID_PRODUCT_OUT.\n"
            "Ensure you have the correct firmware files for your exact device model."
        ),
        "update": SafetyInfo(
            FastbootSafetyTier.RISKY,
            "⚠️ RISKY: This will flash the update.zip package.\n"
            "Ensure the package is compatible with your device model and current firmware."
        ),
        "flash": SafetyInfo(
            FastbootSafetyTier.RISKY,
            "⚠️ RISKY: This will flash the specified partition.\n"
            "Flashing wrong firmware can brick your device. Verify compatibility first."
        ),
        "oem": SafetyInfo(
            FastbootSafetyTier.RISKY,
            "⚠️ RISKY: OEM commands are manufacturer-specific and can be dangerous.\n"
            "Only use OEM commands if you know exactly what they do."
        ),
        "set_active": SafetyInfo(
            FastbootSafetyTier.RISKY,
            "⚠️ RISKY: Changing active slot can make device unbootable.\n"
            "Ensure the target slot has working firmware before switching."
        ),
    }
    
    def __init__(self, fastboot_path: Optional[str] = None, timeout: int = 60):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.process_runner = ProcessRunner(timeout)
        self._fastboot_path: Optional[Path] = None
        
        if fastboot_path:
            self._fastboot_path = Path(fastboot_path)
        else:
            self._fastboot_path = self.find_binary()
    
    def find_binary(self) -> Optional[Path]:
        """Find Fastboot binary in common locations."""
        if self._fastboot_path and self._fastboot_path.exists():
            return self._fastboot_path
        
        binary_name = "fastboot.exe" if sys.platform == "win32" else "fastboot"
        
        # Check PATH
        fastboot_in_path = shutil.which("fastboot")
        if fastboot_in_path:
            self._fastboot_path = Path(fastboot_in_path)
            self.logger.info(f"Found Fastboot in PATH: {self._fastboot_path}")
            return self._fastboot_path
        
        # Check platform-tools directory
        platform_tools = find_platform_tools()
        if platform_tools:
            fastboot_path = platform_tools / binary_name
            if fastboot_path.exists():
                self._fastboot_path = fastboot_path
                self.logger.info(f"Found Fastboot in platform-tools: {self._fastboot_path}")
                return self._fastboot_path
        
        self.logger.warning("Fastboot binary not found")
        return None
    
    def _run_fastboot(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        input_data: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """Run Fastboot command with given arguments."""
        if not self._fastboot_path:
            raise RuntimeError("Fastboot binary not found. Please install Android SDK Platform Tools.")
        
        command = [str(self._fastboot_path)] + args
        return self.process_runner.run(
            command=command,
            timeout=timeout or self.timeout,
            input_data=input_data,
            progress_callback=progress_callback
        )
    
    def get_safety_info(self, command: str) -> SafetyInfo:
        """Get safety information for a command."""
        return self.SAFETY_MAP.get(command, SafetyInfo(
            FastbootSafetyTier.SAFE,
            "This is a standard fastboot operation."
        ))
    
    # Core Commands
    
    def devices(self, long_output: bool = False) -> List[FastbootDevice]:
        """List devices in fastboot mode."""
        args = ["devices"]
        if long_output:
            args.append("-l")
        
        result = self._run_fastboot(args)
        devices = []
        
        if result.success:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        serial = parts[0]
                        state = parts[1]
                        devices.append(FastbootDevice(serial=serial, state=state))
        
        return devices
    
    def getvar(self, name: str, serial: Optional[str] = None) -> Optional[str]:
        """Get bootloader variable."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["getvar", name])
        
        result = self._run_fastboot(args)
        if result.success:
            # Fastboot outputs to stderr for getvar
            for line in result.stderr.split('\n'):
                if f"{name}:" in line:
                    return line.split(':', 1)[1].strip()
        return None
    
    def reboot(self, mode: Optional[str] = None, serial: Optional[str] = None) -> ProcessResult:
        """
        Reboot device.
        
        Args:
            mode: Reboot mode (bootloader, recovery, fastboot)
            serial: Device serial number
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("reboot")
        if mode:
            args.append(mode)
        
        return self._run_fastboot(args)
    
    # Flashing Operations (DESTRUCTIVE)
    
    def update(self, zip_file: Union[str, Path], serial: Optional[str] = None, skip_reboot: bool = False) -> ProcessResult:
        """Flash update.zip package."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("update")
        if skip_reboot:
            args.append("-n")
        args.append(str(zip_file))
        
        return self._run_fastboot(args)
    
    def flashall(
        self,
        serial: Optional[str] = None,
        skip_secondary: bool = False,
        skip_reboot: bool = False
    ) -> ProcessResult:
        """Flash all partitions from $ANDROID_PRODUCT_OUT."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("flashall")
        if skip_secondary:
            args.append("--skip-secondary")
        if skip_reboot:
            args.append("--skip-reboot")
        
        return self._run_fastboot(args)
    
    def flash(
        self,
        partition: str,
        filename: Optional[Union[str, Path]] = None,
        serial: Optional[str] = None,
        slot: Optional[str] = None
    ) -> ProcessResult:
        """Flash specific partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        if slot:
            args.extend(["--slot", slot])
        
        args.extend(["flash", partition])
        if filename:
            args.append(str(filename))
        
        return self._run_fastboot(args)
    
    # Partition Management (DESTRUCTIVE)
    
    def erase(self, partition: str, serial: Optional[str] = None) -> ProcessResult:
        """Erase partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["erase", partition])
        
        return self._run_fastboot(args)
    
    def format(
        self,
        partition: str,
        fs_type: Optional[str] = None,
        size: Optional[str] = None,
        serial: Optional[str] = None
    ) -> ProcessResult:
        """Format partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["format", partition])
        if fs_type:
            args.append(fs_type)
        if size:
            args.append(size)
        
        return self._run_fastboot(args)
    
    def wipe_super(self, super_empty: Optional[Union[str, Path]] = None, serial: Optional[str] = None) -> ProcessResult:
        """Wipe super partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("wipe-super")
        if super_empty:
            args.append(str(super_empty))
        
        return self._run_fastboot(args)
    
    # Bootloader Security (CRITICAL)
    
    def flashing_lock(self, serial: Optional[str] = None) -> ProcessResult:
        """Lock bootloader."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["flashing", "lock"])
        
        return self._run_fastboot(args)
    
    def flashing_unlock(self, serial: Optional[str] = None) -> ProcessResult:
        """Unlock bootloader."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["flashing", "unlock"])
        
        return self._run_fastboot(args)
    
    def flashing_lock_critical(self, serial: Optional[str] = None) -> ProcessResult:
        """Lock critical partitions."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["flashing", "lock_critical"])
        
        return self._run_fastboot(args)
    
    def flashing_unlock_critical(self, serial: Optional[str] = None) -> ProcessResult:
        """Unlock critical partitions."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["flashing", "unlock_critical"])
        
        return self._run_fastboot(args)
    
    def flashing_get_unlock_ability(self, serial: Optional[str] = None) -> Optional[bool]:
        """Check if bootloader can be unlocked."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["flashing", "get_unlock_ability"])
        
        result = self._run_fastboot(args)
        if result.success:
            # Parse output to determine unlock ability
            output = result.stderr.lower()  # Fastboot often uses stderr
            if "1" in output or "true" in output:
                return True
            elif "0" in output or "false" in output:
                return False
        return None
    
    # A/B Slot Management
    
    def set_active(self, slot: str, serial: Optional[str] = None) -> ProcessResult:
        """
        Set active slot.
        
        Args:
            slot: Slot to activate ('a', 'b', 'all', 'other')
            serial: Device serial number
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["set_active", slot])
        
        return self._run_fastboot(args)
    
    def get_current_slot(self, serial: Optional[str] = None) -> Optional[str]:
        """Get current active slot."""
        slot_suffix = self.getvar("current-slot", serial)
        if slot_suffix:
            return slot_suffix.replace("_", "")  # Remove underscore prefix
        return None
    
    # Advanced Features
    
    def oem(self, *commands: str, serial: Optional[str] = None) -> ProcessResult:
        """Execute OEM-specific commands."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("oem")
        args.extend(commands)
        
        return self._run_fastboot(args)
    
    def boot(
        self,
        kernel: Union[str, Path],
        ramdisk: Optional[Union[str, Path]] = None,
        second: Optional[Union[str, Path]] = None,
        serial: Optional[str] = None,
        **boot_options
    ) -> ProcessResult:
        """Boot from RAM without flashing."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["boot", str(kernel)])
        
        if ramdisk:
            args.append(str(ramdisk))
        if second:
            args.append(str(second))
        
        # Add boot options
        for key, value in boot_options.items():
            args.extend([f"--{key}", str(value)])
        
        return self._run_fastboot(args)
    
    def flash_raw(
        self,
        partition: str,
        kernel: Union[str, Path],
        ramdisk: Optional[Union[str, Path]] = None,
        second: Optional[Union[str, Path]] = None,
        serial: Optional[str] = None
    ) -> ProcessResult:
        """Flash raw kernel image."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["flash:raw", partition, str(kernel)])
        
        if ramdisk:
            args.append(str(ramdisk))
        if second:
            args.append(str(second))
        
        return self._run_fastboot(args)
    
    # Logical Partitions
    
    def create_logical_partition(self, name: str, size: str, serial: Optional[str] = None) -> ProcessResult:
        """Create logical partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["create-logical-partition", name, size])
        
        return self._run_fastboot(args)
    
    def delete_logical_partition(self, name: str, serial: Optional[str] = None) -> ProcessResult:
        """Delete logical partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["delete-logical-partition", name])
        
        return self._run_fastboot(args)
    
    def resize_logical_partition(self, name: str, size: str, serial: Optional[str] = None) -> ProcessResult:
        """Resize logical partition."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["resize-logical-partition", name, size])
        
        return self._run_fastboot(args)
    
    # GSI & Snapshots
    
    def gsi_wipe(self, serial: Optional[str] = None) -> ProcessResult:
        """Wipe GSI installation."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["gsi", "wipe"])
        
        return self._run_fastboot(args)
    
    def gsi_disable(self, serial: Optional[str] = None) -> ProcessResult:
        """Disable GSI."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["gsi", "disable"])
        
        return self._run_fastboot(args)
    
    def gsi_status(self, serial: Optional[str] = None) -> ProcessResult:
        """Get GSI status."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["gsi", "status"])
        
        return self._run_fastboot(args)
    
    def snapshot_update_cancel(self, serial: Optional[str] = None) -> ProcessResult:
        """Cancel snapshot update."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["snapshot-update", "cancel"])
        
        return self._run_fastboot(args)
    
    def snapshot_update_merge(self, serial: Optional[str] = None) -> ProcessResult:
        """Merge snapshot update."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["snapshot-update", "merge"])
        
        return self._run_fastboot(args)
    
    def fetch(self, partition: str, output_file: Union[str, Path], serial: Optional[str] = None) -> ProcessResult:
        """Fetch partition to file."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["fetch", partition, str(output_file)])
        
        return self._run_fastboot(args)
    
    # Android Things
    
    def stage(self, input_file: Union[str, Path], serial: Optional[str] = None) -> ProcessResult:
        """Stage file for flashing."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["stage", str(input_file)])
        
        return self._run_fastboot(args)
    
    def get_staged(self, output_file: Union[str, Path], serial: Optional[str] = None) -> ProcessResult:
        """Get staged file."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["get_staged", str(output_file)])
        
        return self._run_fastboot(args)
    
    # Utility Methods
    
    def get_device_info(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive device information."""
        info = {}
        
        # Important variables to query
        variables = [
            "product", "variant", "secure", "unlocked", "charge-state",
            "battery-voltage", "serialno", "version-bootloader", "version-baseband",
            "hw-revision", "max-download-size", "partition-type", "partition-size",
            "current-slot", "slot-count", "has-slot", "slot-successful",
            "slot-unbootable", "slot-retry-count"
        ]
        
        for var in variables:
            value = self.getvar(var, serial)
            if value:
                info[var] = value
        
        # Get partition list
        partitions_result = self._run_fastboot(["-s", serial] if serial else [] + ["getvar", "all"])
        if partitions_result.success:
            partitions = []
            for line in partitions_result.stderr.split('\n'):
                if "partition-type:" in line:
                    partition_name = line.split(':')[0].replace("partition-type", "").strip()
                    if partition_name:
                        partitions.append(partition_name)
            info['partitions'] = partitions
        
        return info
    
    def is_critical_partition(self, partition: str) -> bool:
        """Check if partition is critical (can brick device if corrupted)."""
        critical_partitions = {
            'bootloader', 'boot', 'recovery', 'system', 'vendor',
            'aboot', 'sbl1', 'sbl2', 'sbl3', 'rpm', 'tz', 'hyp',
            'modem', 'dsp', 'persist', 'misc', 'metadata'
        }
        return partition.lower() in critical_partitions
    
    def is_available(self) -> bool:
        """Check if Fastboot is available and working."""
        return self._fastboot_path is not None and self._fastboot_path.exists()
    
    def get_binary_path(self) -> Optional[Path]:
        """Get path to Fastboot binary."""
        return self._fastboot_path
    
    def validate_device_compatibility(self, serial: str, operation: str) -> Tuple[bool, str]:
        """
        Validate device compatibility for dangerous operations.
        
        Returns:
            (is_safe, warning_message)
        """
        info = self.get_device_info(serial)
        warnings = []
        
        # Check if device is unlocked for flash operations
        if operation in ["flash", "erase", "format"] and info.get("unlocked") != "yes":
            warnings.append("Device bootloader is locked - operation may fail")
        
        # Check battery level for critical operations
        if operation in ["flashing unlock", "flashing lock", "flashall", "update"]:
            battery_voltage = info.get("battery-voltage")
            if battery_voltage:
                try:
                    voltage = int(battery_voltage)
                    if voltage < 3700:  # Rough low battery threshold
                        warnings.append("Low battery detected - charge device before proceeding")
                except ValueError:
                    pass
        
        # Check for A/B slot issues
        if operation == "set_active":
            current_slot = info.get("current-slot")
            slot_successful = info.get(f"slot-successful:{current_slot}")
            if slot_successful == "no":
                warnings.append("Current slot marked as unsuccessful - switching may cause boot issues")
        
        is_safe = len(warnings) == 0
        warning_message = "\n".join(warnings) if warnings else ""
        
        return is_safe, warning_message
