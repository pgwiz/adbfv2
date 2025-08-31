"""
ADB (Android Debug Bridge) wrapper with complete v1.0.41 command support.
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


class ADBState(Enum):
    """ADB device states."""
    DEVICE = "device"
    OFFLINE = "offline"
    BOOTLOADER = "bootloader"
    RECOVERY = "recovery"
    SIDELOAD = "sideload"
    UNAUTHORIZED = "unauthorized"
    CONNECTING = "connecting"
    AUTHORIZING = "authorizing"


@dataclass
class ADBDevice:
    """Represents an ADB device."""
    serial: str
    state: ADBState
    transport_id: Optional[str] = None
    product: Optional[str] = None
    model: Optional[str] = None
    device: Optional[str] = None
    transport: Optional[str] = None


class ADBWrapper:
    """Comprehensive ADB wrapper based on v1.0.41 functionality."""
    
    def __init__(self, adb_path: Optional[str] = None, timeout: int = 30):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self.process_runner = ProcessRunner(timeout)
        self._adb_path: Optional[Path] = None
        
        if adb_path:
            self._adb_path = Path(adb_path)
        else:
            self._adb_path = self.find_binary()
    
    def find_binary(self) -> Optional[Path]:
        """Find ADB binary in common locations."""
        # Check if already found
        if self._adb_path and self._adb_path.exists():
            return self._adb_path
        
        binary_name = "adb.exe" if sys.platform == "win32" else "adb"
        
        # Check PATH
        adb_in_path = shutil.which("adb")
        if adb_in_path:
            self._adb_path = Path(adb_in_path)
            self.logger.info(f"Found ADB in PATH: {self._adb_path}")
            return self._adb_path
        
        # Check platform-tools directory
        platform_tools = find_platform_tools()
        if platform_tools:
            adb_path = platform_tools / binary_name
            if adb_path.exists():
                self._adb_path = adb_path
                self.logger.info(f"Found ADB in platform-tools: {self._adb_path}")
                return self._adb_path
        
        self.logger.warning("ADB binary not found")
        return None
    
    def _run_adb(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        input_data: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """Run ADB command with given arguments."""
        if not self._adb_path:
            raise RuntimeError("ADB binary not found. Please install Android SDK Platform Tools.")
        
        command = [str(self._adb_path)] + args
        return self.process_runner.run(
            command=command,
            timeout=timeout or self.timeout,
            input_data=input_data,
            progress_callback=progress_callback
        )
    
    # Core Commands
    
    def version(self) -> Optional[str]:
        """Get ADB version information."""
        result = self._run_adb(["version"])
        if result.success:
            return result.stdout.strip()
        return None
    
    def help(self) -> Optional[str]:
        """Get ADB help text."""
        result = self._run_adb(["help"])
        if result.success:
            return result.stdout
        return None
    
    def devices(self, long_output: bool = False) -> List[ADBDevice]:
        """
        List connected devices.
        
        Args:
            long_output: Include additional device information
        
        Returns:
            List of ADBDevice objects
        """
        args = ["devices"]
        if long_output:
            args.append("-l")
        
        result = self._run_adb(args)
        devices = []
        
        if result.success:
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state_str = parts[1]
                    
                    try:
                        state = ADBState(state_str)
                    except ValueError:
                        state = ADBState.OFFLINE
                    
                    device = ADBDevice(serial=serial, state=state)
                    
                    # Parse additional info for long output
                    if long_output and len(parts) > 2:
                        for part in parts[2:]:
                            if ':' in part:
                                key, value = part.split(':', 1)
                                if key == "product":
                                    device.product = value
                                elif key == "model":
                                    device.model = value
                                elif key == "device":
                                    device.device = value
                                elif key == "transport":
                                    device.transport = value
                                elif key == "transport_id":
                                    device.transport_id = value
                    
                    devices.append(device)
        
        return devices
    
    def get_state(self, serial: Optional[str] = None) -> Optional[ADBState]:
        """Get device state."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("get-state")
        
        result = self._run_adb(args)
        if result.success:
            try:
                return ADBState(result.stdout.strip())
            except ValueError:
                return None
        return None
    
    def get_serialno(self, serial: Optional[str] = None) -> Optional[str]:
        """Get device serial number."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("get-serialno")
        
        result = self._run_adb(args)
        if result.success:
            return result.stdout.strip()
        return None
    
    def get_devpath(self, serial: Optional[str] = None) -> Optional[str]:
        """Get device path."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("get-devpath")
        
        result = self._run_adb(args)
        if result.success:
            return result.stdout.strip()
        return None
    
    # Networking Commands
    
    def connect(self, host: str, port: int = 5555, serial: Optional[str] = None) -> ProcessResult:
        """Connect to device over TCP/IP."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["connect", f"{host}:{port}"])
        
        return self._run_adb(args)
    
    def disconnect(self, host: Optional[str] = None, port: int = 5555, serial: Optional[str] = None) -> ProcessResult:
        """Disconnect from TCP/IP device."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        if host:
            args.extend(["disconnect", f"{host}:{port}"])
        else:
            args.append("disconnect")
        
        return self._run_adb(args)
    
    def pair(self, host: str, port: int, pairing_code: Optional[str] = None, serial: Optional[str] = None) -> ProcessResult:
        """Pair with device using pairing code."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        if pairing_code:
            args.extend(["pair", f"{host}:{port}", pairing_code])
        else:
            args.extend(["pair", f"{host}:{port}"])
        
        return self._run_adb(args)
    
    def tcpip(self, port: int = 5555, serial: Optional[str] = None) -> ProcessResult:
        """Restart ADB server in TCP/IP mode."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["tcpip", str(port)])
        
        return self._run_adb(args)
    
    def usb(self, serial: Optional[str] = None) -> ProcessResult:
        """Restart ADB server in USB mode."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("usb")
        
        return self._run_adb(args)
    
    def forward(
        self,
        local: str,
        remote: str,
        serial: Optional[str] = None,
        no_rebind: bool = False,
        list_forwards: bool = False,
        remove: bool = False,
        remove_all: bool = False
    ) -> ProcessResult:
        """Manage port forwarding."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("forward")
        
        if list_forwards:
            args.append("--list")
        elif remove_all:
            args.append("--remove-all")
        elif remove:
            args.extend(["--remove", local])
        else:
            if no_rebind:
                args.append("--no-rebind")
            args.extend([local, remote])
        
        return self._run_adb(args)
    
    def reverse(
        self,
        remote: str,
        local: str,
        serial: Optional[str] = None,
        no_rebind: bool = False,
        list_reverses: bool = False,
        remove: bool = False,
        remove_all: bool = False
    ) -> ProcessResult:
        """Manage reverse port forwarding."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("reverse")
        
        if list_reverses:
            args.append("--list")
        elif remove_all:
            args.append("--remove-all")
        elif remove:
            args.extend(["--remove", remote])
        else:
            if no_rebind:
                args.append("--no-rebind")
            args.extend([remote, local])
        
        return self._run_adb(args)
    
    def mdns_check(self, serial: Optional[str] = None) -> ProcessResult:
        """Check mDNS registration."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["mdns", "check"])
        
        return self._run_adb(args)
    
    def mdns_services(self, serial: Optional[str] = None) -> ProcessResult:
        """List mDNS services."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["mdns", "services"])
        
        return self._run_adb(args)
    
    # File Transfer Commands
    
    def push(
        self,
        local: Union[str, Path],
        remote: str,
        serial: Optional[str] = None,
        sync: bool = False,
        compression: Optional[str] = None,
        dry_run: bool = False,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """
        Push file/directory to device.
        
        Args:
            local: Local file or directory path
            remote: Remote path on device
            serial: Device serial number
            sync: Only push files that are newer on host
            compression: Compression algorithm (none, any, brotli, lz4, zstd)
            dry_run: Show what would be pushed without actually pushing
            progress_callback: Callback for progress updates
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("push")
        
        if sync:
            args.append("--sync")
        if compression:
            args.extend(["-z", compression])
        if dry_run:
            args.append("-n")
        
        args.extend([str(local), remote])
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def pull(
        self,
        remote: str,
        local: Union[str, Path],
        serial: Optional[str] = None,
        preserve_timestamp: bool = False,
        compression: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """
        Pull file/directory from device.
        
        Args:
            remote: Remote path on device
            local: Local destination path
            serial: Device serial number
            preserve_timestamp: Preserve file timestamps
            compression: Compression algorithm
            progress_callback: Callback for progress updates
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("pull")
        
        if preserve_timestamp:
            args.append("-a")
        if compression:
            args.extend(["-z", compression])
        
        args.extend([remote, str(local)])
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def sync(
        self,
        partition: str = "all",
        serial: Optional[str] = None,
        list_only: bool = False,
        compression: Optional[str] = None
    ) -> ProcessResult:
        """
        Sync files to device.
        
        Args:
            partition: Partition to sync (system, vendor, oem, data, all)
            serial: Device serial number
            list_only: List files that would be synced
            compression: Compression algorithm
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("sync")
        
        if list_only:
            args.append("-l")
        if compression:
            args.extend(["-z", compression])
        
        if partition != "all":
            args.append(partition)
        
        return self._run_adb(args)
    
    # App Management Commands
    
    def install(
        self,
        apk_path: Union[str, Path],
        serial: Optional[str] = None,
        replace: bool = False,
        test: bool = False,
        downgrade: bool = False,
        grant_permissions: bool = False,
        streaming: Optional[bool] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """
        Install APK to device.
        
        Args:
            apk_path: Path to APK file
            serial: Device serial number
            replace: Replace existing application
            test: Install as test package
            downgrade: Allow version code downgrade
            grant_permissions: Grant all runtime permissions
            streaming: Enable/disable streaming install
            progress_callback: Callback for progress updates
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("install")
        
        if replace:
            args.append("-r")
        if test:
            args.append("-t")
        if downgrade:
            args.append("-d")
        if grant_permissions:
            args.append("-g")
        if streaming is True:
            args.append("--streaming")
        elif streaming is False:
            args.append("--no-streaming")
        
        args.append(str(apk_path))
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def install_multiple(
        self,
        apk_paths: List[Union[str, Path]],
        serial: Optional[str] = None,
        replace: bool = False,
        test: bool = False,
        downgrade: bool = False,
        grant_permissions: bool = False,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """Install multiple APKs."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("install-multiple")
        
        if replace:
            args.append("-r")
        if test:
            args.append("-t")
        if downgrade:
            args.append("-d")
        if grant_permissions:
            args.append("-g")
        
        args.extend([str(path) for path in apk_paths])
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def install_multi_package(
        self,
        apk_paths: List[Union[str, Path]],
        serial: Optional[str] = None,
        replace: bool = False,
        test: bool = False,
        downgrade: bool = False,
        grant_permissions: bool = False,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """Install multi-package APK."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("install-multi-package")
        
        if replace:
            args.append("-r")
        if test:
            args.append("-t")
        if downgrade:
            args.append("-d")
        if grant_permissions:
            args.append("-g")
        
        args.extend([str(path) for path in apk_paths])
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def uninstall(
        self,
        package: str,
        serial: Optional[str] = None,
        keep_data: bool = False
    ) -> ProcessResult:
        """
        Uninstall package from device.
        
        Args:
            package: Package name to uninstall
            serial: Device serial number
            keep_data: Keep app data and cache directories
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("uninstall")
        
        if keep_data:
            args.append("-k")
        
        args.append(package)
        
        return self._run_adb(args)
    
    # Shell and Debugging Commands
    
    def shell(
        self,
        command: Optional[str] = None,
        serial: Optional[str] = None,
        escape_char: str = '~',
        disable_pty: bool = False,
        timeout: Optional[int] = None
    ) -> ProcessResult:
        """
        Run shell command on device.
        
        Args:
            command: Shell command to run (None for interactive shell)
            serial: Device serial number
            escape_char: Escape character for interactive shell
            disable_pty: Disable PTY allocation
            timeout: Command timeout
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("shell")
        
        if escape_char != '~':
            args.extend(["-e", escape_char])
        if disable_pty:
            args.append("-T")
        
        if command:
            args.append(command)
        
        return self._run_adb(args, timeout=timeout)
    
    def logcat(
        self,
        args: Optional[List[str]] = None,
        serial: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """
        View device log output.
        
        Args:
            args: Additional logcat arguments
            serial: Device serial number
            progress_callback: Callback for real-time log output
        """
        cmd_args = []
        if serial:
            cmd_args.extend(["-s", serial])
        
        cmd_args.append("logcat")
        
        if args:
            cmd_args.extend(args)
        
        return self._run_adb(cmd_args, progress_callback=progress_callback)
    
    def bugreport(
        self,
        path: Optional[Union[str, Path]] = None,
        serial: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> ProcessResult:
        """Generate bug report."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("bugreport")
        
        if path:
            args.append(str(path))
        
        return self._run_adb(args, progress_callback=progress_callback)
    
    def screencap(self, output_path: Optional[Union[str, Path]] = None, serial: Optional[str] = None) -> ProcessResult:
        """Take screenshot."""
        if output_path:
            command = f"screencap -p > {output_path}"
        else:
            command = "screencap -p"
        
        return self.shell(command, serial=serial)
    
    def screenrecord(
        self,
        output_path: str,
        serial: Optional[str] = None,
        time_limit: Optional[int] = None,
        bit_rate: Optional[int] = None,
        size: Optional[str] = None,
        rotate: bool = False
    ) -> ProcessResult:
        """Record screen."""
        command = "screenrecord"
        
        if time_limit:
            command += f" --time-limit {time_limit}"
        if bit_rate:
            command += f" --bit-rate {bit_rate}"
        if size:
            command += f" --size {size}"
        if rotate:
            command += " --rotate"
        
        command += f" {output_path}"
        
        return self.shell(command, serial=serial)
    
    # System Control Commands
    
    def reboot(self, mode: Optional[str] = None, serial: Optional[str] = None) -> ProcessResult:
        """
        Reboot device.
        
        Args:
            mode: Reboot mode (bootloader, recovery, sideload, sideload-auto-reboot)
            serial: Device serial number
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("reboot")
        
        if mode:
            args.append(mode)
        
        return self._run_adb(args)
    
    def root(self, serial: Optional[str] = None) -> ProcessResult:
        """Restart ADB daemon with root permissions."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("root")
        
        return self._run_adb(args)
    
    def unroot(self, serial: Optional[str] = None) -> ProcessResult:
        """Restart ADB daemon without root permissions."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.append("unroot")
        
        return self._run_adb(args)
    
    def remount(self, auto_reboot: bool = False, serial: Optional[str] = None) -> ProcessResult:
        """Remount partitions read-write."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.append("remount")
        
        if auto_reboot:
            args.append("-R")
        
        return self._run_adb(args)
    
    def sideload(self, ota_package: Union[str, Path], serial: Optional[str] = None) -> ProcessResult:
        """Sideload OTA package."""
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["sideload", str(ota_package)])
        
        return self._run_adb(args)
    
    # Advanced Commands
    
    def wait_for_state(
        self,
        state: str,
        transport: str = "any",
        serial: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> ProcessResult:
        """
        Wait for device to reach specified state.
        
        Args:
            state: Target state (device, recovery, rescue, sideload, bootloader, disconnect)
            transport: Transport type (usb, local, any)
            serial: Device serial number
            timeout: Wait timeout
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["wait-for", f"{transport}-{state}"])
        
        return self._run_adb(args, timeout=timeout)
    
    def disable_verity(self, serial: Optional[str] = None) -> ProcessResult:
        """Disable dm-verity checking."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["disable-verity"])
        
        return self._run_adb(args)
    
    def enable_verity(self, serial: Optional[str] = None) -> ProcessResult:
        """Enable dm-verity checking."""
        args = []
        if serial:
            args.extend(["-s", serial])
        args.extend(["enable-verity"])
        
        return self._run_adb(args)
    
    def keygen(self, filepath: Union[str, Path]) -> ProcessResult:
        """Generate ADB key pair."""
        args = ["keygen", str(filepath)]
        return self._run_adb(args)
    
    # Server Management
    
    def start_server(self) -> ProcessResult:
        """Start ADB server."""
        return self._run_adb(["start-server"])
    
    def kill_server(self) -> ProcessResult:
        """Kill ADB server."""
        return self._run_adb(["kill-server"])
    
    def reconnect(self, mode: str = "device", serial: Optional[str] = None) -> ProcessResult:
        """
        Reconnect to device.
        
        Args:
            mode: Reconnect mode (device, recovery, sideload)
            serial: Device serial number
        """
        args = []
        if serial:
            args.extend(["-s", serial])
        
        args.extend(["reconnect", mode])
        
        return self._run_adb(args)
    
    # Utility Methods
    
    def get_device_info(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive device information."""
        info = {}
        
        # Basic properties
        properties = [
            "ro.product.model",
            "ro.product.manufacturer", 
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.product.cpu.abi",
            "ro.build.version.security_patch",
            "ro.serialno",
            "ro.product.name",
            "ro.build.display.id"
        ]
        
        for prop in properties:
            result = self.shell(f"getprop {prop}", serial=serial)
            if result.success:
                info[prop] = result.stdout.strip()
        
        # Battery info
        battery_result = self.shell("dumpsys battery", serial=serial)
        if battery_result.success:
            battery_info = {}
            for line in battery_result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ['level', 'temperature', 'voltage', 'status', 'health']:
                        battery_info[key] = value
            info['battery'] = battery_info
        
        # Network info
        ip_result = self.shell("ip route get 1.1.1.1", serial=serial)
        if ip_result.success:
            # Extract IP from route output
            for line in ip_result.stdout.split('\n'):
                if 'src' in line:
                    parts = line.split()
                    try:
                        src_idx = parts.index('src')
                        if src_idx + 1 < len(parts):
                            info['ip_address'] = parts[src_idx + 1]
                    except (ValueError, IndexError):
                        pass
        
        return info
    
    def is_available(self) -> bool:
        """Check if ADB is available and working."""
        return self._adb_path is not None and self._adb_path.exists()
    
    def get_binary_path(self) -> Optional[Path]:
        """Get path to ADB binary."""
        return self._adb_path
