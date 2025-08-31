"""
Developer console for direct ADB/Fastboot command execution.
"""

import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal
from dataclasses import dataclass, asdict
from datetime import datetime

from adb_tools.adb import ADBWrapper
from adb_tools.fastboot import FastbootWrapper
from utils.platform_paths import get_app_data_dir


@dataclass
class CommandHistoryEntry:
    """Command history entry."""
    timestamp: datetime
    command: str
    tool: str  # "adb" or "fastboot"
    device_serial: Optional[str]
    success: bool
    output: str
    execution_time: float


class DevConsole(QObject):
    """Developer console for advanced users."""
    
    command_executed = pyqtSignal(object)  # CommandHistoryEntry
    command_started = pyqtSignal(str)  # command
    
    def __init__(self, adb_wrapper: Optional[ADBWrapper], fastboot_wrapper: Optional[FastbootWrapper]):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.fastboot_wrapper = fastboot_wrapper
        
        # Command history
        self.history: List[CommandHistoryEntry] = []
        self.history_file = get_app_data_dir() / "command_history.json"
        self.max_history = 1000
        
        self.load_history()
    
    def execute_adb_command(self, command: str, device_serial: Optional[str] = None) -> CommandHistoryEntry:
        """Execute ADB command and record in history."""
        if not self.adb_wrapper:
            raise RuntimeError("ADB not available")
        
        self.command_started.emit(f"adb {command}")
        
        # Parse command into arguments
        args = self._parse_command(command)
        if device_serial:
            args = ["-s", device_serial] + args
        
        start_time = datetime.now()
        
        try:
            result = self.adb_wrapper._run_adb(args)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            entry = CommandHistoryEntry(
                timestamp=start_time,
                command=f"adb {command}",
                tool="adb",
                device_serial=device_serial,
                success=result.success,
                output=result.output,
                execution_time=execution_time
            )
            
            self._add_to_history(entry)
            return entry
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            entry = CommandHistoryEntry(
                timestamp=start_time,
                command=f"adb {command}",
                tool="adb",
                device_serial=device_serial,
                success=False,
                output=str(e),
                execution_time=execution_time
            )
            
            self._add_to_history(entry)
            return entry
    
    def execute_fastboot_command(self, command: str, device_serial: Optional[str] = None) -> CommandHistoryEntry:
        """Execute Fastboot command and record in history."""
        if not self.fastboot_wrapper:
            raise RuntimeError("Fastboot not available")
        
        # Check if command requires safety confirmation
        safety_info = self.fastboot_wrapper.get_safety_info(command.split()[0])
        if safety_info.tier.value != "safe":
            self.logger.warning(f"Dangerous fastboot command attempted: {command}")
            # In a real implementation, this would trigger safety dialogs
        
        self.command_started.emit(f"fastboot {command}")
        
        # Parse command into arguments
        args = self._parse_command(command)
        if device_serial:
            args = ["-s", device_serial] + args
        
        start_time = datetime.now()
        
        try:
            result = self.fastboot_wrapper._run_fastboot(args)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            entry = CommandHistoryEntry(
                timestamp=start_time,
                command=f"fastboot {command}",
                tool="fastboot",
                device_serial=device_serial,
                success=result.success,
                output=result.output,
                execution_time=execution_time
            )
            
            self._add_to_history(entry)
            return entry
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            entry = CommandHistoryEntry(
                timestamp=start_time,
                command=f"fastboot {command}",
                tool="fastboot",
                device_serial=device_serial,
                success=False,
                output=str(e),
                execution_time=execution_time
            )
            
            self._add_to_history(entry)
            return entry
    
    def _parse_command(self, command: str) -> List[str]:
        """Parse command string into arguments."""
        # Simple parsing - could be enhanced with proper shell parsing
        import shlex
        try:
            return shlex.split(command)
        except ValueError:
            # Fallback to simple split
            return command.split()
    
    def _add_to_history(self, entry: CommandHistoryEntry):
        """Add entry to command history."""
        self.history.append(entry)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        # Save to file
        self.save_history()
        
        # Emit signal
        self.command_executed.emit(entry)
    
    def get_command_suggestions(self, partial_command: str, tool: str) -> List[str]:
        """Get command suggestions based on history and common commands."""
        suggestions = []
        
        # Common ADB commands
        if tool == "adb":
            common_adb = [
                "devices", "shell", "install", "uninstall", "push", "pull",
                "logcat", "reboot", "connect", "disconnect", "tcpip", "usb",
                "forward", "reverse", "bugreport", "version", "help"
            ]
            suggestions.extend([cmd for cmd in common_adb if cmd.startswith(partial_command)])
        
        # Common Fastboot commands
        elif tool == "fastboot":
            common_fastboot = [
                "devices", "getvar", "reboot", "flash", "erase", "format",
                "flashing unlock", "flashing lock", "boot", "update", "flashall"
            ]
            suggestions.extend([cmd for cmd in common_fastboot if cmd.startswith(partial_command)])
        
        # Add from history
        for entry in reversed(self.history[-50:]):  # Last 50 commands
            if entry.tool == tool:
                cmd = entry.command.replace(f"{tool} ", "", 1)
                if cmd.startswith(partial_command) and cmd not in suggestions:
                    suggestions.append(cmd)
        
        return sorted(suggestions)[:10]  # Limit to 10 suggestions
    
    def save_history(self):
        """Save command history to file."""
        try:
            # Convert to serializable format
            history_data = []
            for entry in self.history[-100:]:  # Save last 100 entries
                data = asdict(entry)
                data['timestamp'] = entry.timestamp.isoformat()
                history_data.append(data)
            
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save command history: {e}")
    
    def load_history(self):
        """Load command history from file."""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.history.clear()
            for data in history_data:
                # Convert timestamp back
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
                data['level'] = LogLevel(data['level']) if 'level' in data else None
                
                entry = CommandHistoryEntry(**data)
                self.history.append(entry)
            
            self.logger.info(f"Loaded {len(self.history)} command history entries")
            
        except Exception as e:
            self.logger.error(f"Failed to load command history: {e}")
    
    def clear_history(self):
        """Clear command history."""
        self.history.clear()
        if self.history_file.exists():
            self.history_file.unlink()
        self.logger.info("Command history cleared")
    
    def export_session(self, file_path: Path) -> bool:
        """Export current session to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("# ADB Helper Console Session Export\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                
                for entry in self.history:
                    f.write(f"# {entry.timestamp.strftime('%H:%M:%S')} - {entry.tool.upper()}\n")
                    f.write(f"$ {entry.command}\n")
                    if entry.output:
                        for line in entry.output.split('\n'):
                            f.write(f"  {line}\n")
                    f.write(f"# Exit code: {'0' if entry.success else '1'}\n")
                    f.write(f"# Execution time: {entry.execution_time:.2f}s\n\n")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export session: {e}")
            return False
