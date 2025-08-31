"""
Logcat viewer and log management.
"""

import logging
import re
from typing import Optional, List, Dict, Any, Callable
from PyQt6.QtCore import QObject, QThread, pyqtSignal, QTimer
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from adb_tools.adb import ADBWrapper


class LogLevel(Enum):
    """Android log levels."""
    VERBOSE = "V"
    DEBUG = "D"
    INFO = "I"
    WARN = "W"
    ERROR = "E"
    FATAL = "F"
    SILENT = "S"


@dataclass
class LogEntry:
    """Represents a single log entry."""
    timestamp: datetime
    pid: int
    tid: int
    level: LogLevel
    tag: str
    message: str
    raw_line: str


class LogcatManager(QObject):
    """Manages logcat monitoring and filtering."""
    
    log_entry_received = pyqtSignal(object)  # LogEntry
    logcat_started = pyqtSignal()
    logcat_stopped = pyqtSignal()
    logcat_error = pyqtSignal(str)  # error_message
    
    def __init__(self, adb_wrapper: ADBWrapper):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.logcat_thread: Optional[LogcatThread] = None
        self.is_running = False
        
        # Filtering options
        self.filter_level: Optional[LogLevel] = None
        self.filter_tags: List[str] = []
        self.filter_text: Optional[str] = None
        self.max_entries = 10000
        
        # Log storage
        self.log_entries: List[LogEntry] = []
    
    def start_logcat(
        self,
        device_serial: str,
        clear_first: bool = True,
        buffer: Optional[str] = None,
        format_type: str = "threadtime"
    ):
        """Start logcat monitoring."""
        if self.is_running:
            self.stop_logcat()
        
        # Build logcat arguments
        args = []
        if clear_first:
            args.append("-c")  # Clear log first
        
        if buffer:
            args.extend(["-b", buffer])
        
        args.extend(["-v", format_type])
        
        # Start logcat thread
        self.logcat_thread = LogcatThread(self.adb_wrapper, device_serial, args)
        self.logcat_thread.log_line_received.connect(self._process_log_line)
        self.logcat_thread.logcat_error.connect(self.logcat_error.emit)
        self.logcat_thread.start()
        
        self.is_running = True
        self.logcat_started.emit()
        self.logger.info(f"Logcat started for device {device_serial}")
    
    def stop_logcat(self):
        """Stop logcat monitoring."""
        if self.logcat_thread and self.logcat_thread.isRunning():
            self.logcat_thread.stop()
            self.logcat_thread.wait(3000)  # Wait up to 3 seconds
            if self.logcat_thread.isRunning():
                self.logcat_thread.terminate()
        
        self.is_running = False
        self.logcat_stopped.emit()
        self.logger.info("Logcat stopped")
    
    def clear_logs(self):
        """Clear stored log entries."""
        self.log_entries.clear()
        self.logger.debug("Log entries cleared")
    
    def set_filters(
        self,
        level: Optional[LogLevel] = None,
        tags: Optional[List[str]] = None,
        text: Optional[str] = None
    ):
        """Set log filtering options."""
        self.filter_level = level
        self.filter_tags = tags or []
        self.filter_text = text
        self.logger.debug(f"Filters updated: level={level}, tags={tags}, text={text}")
    
    def _process_log_line(self, line: str):
        """Process incoming log line."""
        try:
            log_entry = self._parse_log_line(line)
            if log_entry and self._should_include_entry(log_entry):
                self.log_entries.append(log_entry)
                
                # Limit stored entries
                if len(self.log_entries) > self.max_entries:
                    self.log_entries = self.log_entries[-self.max_entries:]
                
                self.log_entry_received.emit(log_entry)
                
        except Exception as e:
            self.logger.error(f"Failed to process log line: {e}")
    
    def _parse_log_line(self, line: str) -> Optional[LogEntry]:
        """Parse logcat line into LogEntry."""
        # Threadtime format: MM-DD HH:MM:SS.mmm PID TID LEVEL TAG: MESSAGE
        pattern = r'(\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEFS])\s+([^:]+):\s*(.*)'
        
        match = re.match(pattern, line)
        if match:
            try:
                timestamp_str, pid_str, tid_str, level_str, tag, message = match.groups()
                
                # Parse timestamp (assuming current year)
                timestamp = datetime.strptime(f"2024-{timestamp_str}", "%Y-%m-%d %H:%M:%S.%f")
                
                return LogEntry(
                    timestamp=timestamp,
                    pid=int(pid_str),
                    tid=int(tid_str),
                    level=LogLevel(level_str),
                    tag=tag.strip(),
                    message=message,
                    raw_line=line
                )
            except (ValueError, KeyError) as e:
                self.logger.debug(f"Failed to parse log line: {e}")
        
        return None
    
    def _should_include_entry(self, entry: LogEntry) -> bool:
        """Check if log entry should be included based on filters."""
        # Level filter
        if self.filter_level:
            level_priority = {
                LogLevel.VERBOSE: 0, LogLevel.DEBUG: 1, LogLevel.INFO: 2,
                LogLevel.WARN: 3, LogLevel.ERROR: 4, LogLevel.FATAL: 5
            }
            if level_priority.get(entry.level, 0) < level_priority.get(self.filter_level, 0):
                return False
        
        # Tag filter
        if self.filter_tags and entry.tag not in self.filter_tags:
            return False
        
        # Text filter
        if self.filter_text:
            search_text = self.filter_text.lower()
            if search_text not in entry.message.lower() and search_text not in entry.tag.lower():
                return False
        
        return True
    
    def export_logs(self, file_path: Path, filtered: bool = True) -> bool:
        """Export logs to file."""
        try:
            entries_to_export = self.log_entries if not filtered else [
                entry for entry in self.log_entries if self._should_include_entry(entry)
            ]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                for entry in entries_to_export:
                    f.write(f"{entry.raw_line}\n")
            
            self.logger.info(f"Exported {len(entries_to_export)} log entries to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export logs: {e}")
            return False


class LogcatThread(QThread):
    """Background thread for logcat monitoring."""
    
    log_line_received = pyqtSignal(str)
    logcat_error = pyqtSignal(str)
    
    def __init__(self, adb_wrapper: ADBWrapper, device_serial: str, args: List[str]):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.device_serial = device_serial
        self.args = args
        self.should_stop = False
    
    def run(self):
        """Run logcat monitoring."""
        try:
            def progress_callback(line: str):
                if not self.should_stop:
                    self.log_line_received.emit(line)
            
            # Run logcat with continuous output
            result = self.adb_wrapper.logcat(
                args=self.args,
                serial=self.device_serial,
                progress_callback=progress_callback
            )
            
            if not result.success and not self.should_stop:
                self.logcat_error.emit(f"Logcat failed: {result.stderr}")
                
        except Exception as e:
            if not self.should_stop:
                self.logcat_error.emit(f"Logcat error: {str(e)}")
    
    def stop(self):
        """Stop logcat monitoring."""
        self.should_stop = True
