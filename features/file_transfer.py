"""
File transfer management for ADB operations.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Callable, Union
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from dataclasses import dataclass
from enum import Enum

from adb_tools.adb import ADBWrapper


class TransferDirection(Enum):
    """File transfer direction."""
    PUSH = "push"  # Local to device
    PULL = "pull"  # Device to local


@dataclass
class TransferJob:
    """Represents a file transfer operation."""
    id: str
    direction: TransferDirection
    local_path: Path
    remote_path: str
    device_serial: str
    total_size: Optional[int] = None
    transferred: int = 0
    status: str = "pending"
    error_message: Optional[str] = None


class FileTransferManager(QObject):
    """Manages file transfers between device and computer."""
    
    transfer_started = pyqtSignal(str)  # job_id
    transfer_progress = pyqtSignal(str, int, int)  # job_id, transferred, total
    transfer_completed = pyqtSignal(str, bool, str)  # job_id, success, message
    
    def __init__(self, adb_wrapper: ADBWrapper):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.active_transfers: List[TransferJob] = []
    
    def push_file(
        self,
        local_path: Union[str, Path],
        remote_path: str,
        device_serial: str,
        sync: bool = False,
        compression: Optional[str] = None
    ) -> str:
        """
        Push file to device.
        
        Returns:
            Transfer job ID
        """
        job_id = f"push_{len(self.active_transfers)}"
        local_path = Path(local_path)
        
        # Calculate file size
        total_size = None
        if local_path.is_file():
            total_size = local_path.stat().st_size
        elif local_path.is_dir():
            total_size = sum(f.stat().st_size for f in local_path.rglob('*') if f.is_file())
        
        job = TransferJob(
            id=job_id,
            direction=TransferDirection.PUSH,
            local_path=local_path,
            remote_path=remote_path,
            device_serial=device_serial,
            total_size=total_size
        )
        
        self.active_transfers.append(job)
        
        # Start transfer in background thread
        thread = FileTransferThread(self.adb_wrapper, job, sync, compression)
        thread.progress_updated.connect(lambda transferred, total: self.transfer_progress.emit(job_id, transferred, total))
        thread.transfer_completed.connect(lambda success, message: self._on_transfer_completed(job_id, success, message))
        thread.start()
        
        self.transfer_started.emit(job_id)
        return job_id
    
    def pull_file(
        self,
        remote_path: str,
        local_path: Union[str, Path],
        device_serial: str,
        preserve_timestamp: bool = False,
        compression: Optional[str] = None
    ) -> str:
        """
        Pull file from device.
        
        Returns:
            Transfer job ID
        """
        job_id = f"pull_{len(self.active_transfers)}"
        
        job = TransferJob(
            id=job_id,
            direction=TransferDirection.PULL,
            local_path=Path(local_path),
            remote_path=remote_path,
            device_serial=device_serial
        )
        
        self.active_transfers.append(job)
        
        # Start transfer in background thread
        thread = FileTransferThread(self.adb_wrapper, job, preserve_timestamp, compression)
        thread.progress_updated.connect(lambda transferred, total: self.transfer_progress.emit(job_id, transferred, total))
        thread.transfer_completed.connect(lambda success, message: self._on_transfer_completed(job_id, success, message))
        thread.start()
        
        self.transfer_started.emit(job_id)
        return job_id
    
    def _on_transfer_completed(self, job_id: str, success: bool, message: str):
        """Handle transfer completion."""
        # Update job status
        for job in self.active_transfers:
            if job.id == job_id:
                job.status = "completed" if success else "failed"
                job.error_message = None if success else message
                break
        
        self.transfer_completed.emit(job_id, success, message)
    
    def cancel_transfer(self, job_id: str) -> bool:
        """Cancel active transfer."""
        # TODO: Implement transfer cancellation
        for job in self.active_transfers:
            if job.id == job_id and job.status == "pending":
                job.status = "cancelled"
                return True
        return False
    
    def get_transfer_status(self, job_id: str) -> Optional[TransferJob]:
        """Get status of transfer job."""
        for job in self.active_transfers:
            if job.id == job_id:
                return job
        return None


class FileTransferThread(QThread):
    """Background thread for file transfer operations."""
    
    progress_updated = pyqtSignal(int, int)  # transferred, total
    transfer_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, adb_wrapper: ADBWrapper, job: TransferJob, *args):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.job = job
        self.args = args
    
    def run(self):
        """Execute file transfer."""
        try:
            def progress_callback(line: str):
                # Parse ADB progress output
                # Example: "[100%] /data/local/tmp/file.txt"
                if '%]' in line:
                    try:
                        percent_str = line.split('%]')[0].split('[')[1]
                        percent = int(percent_str)
                        if self.job.total_size:
                            transferred = (percent * self.job.total_size) // 100
                            self.progress_updated.emit(transferred, self.job.total_size)
                    except (ValueError, IndexError):
                        pass
            
            if self.job.direction == TransferDirection.PUSH:
                result = self.adb_wrapper.push(
                    self.job.local_path,
                    self.job.remote_path,
                    serial=self.job.device_serial,
                    sync=self.args[0] if len(self.args) > 0 else False,
                    compression=self.args[1] if len(self.args) > 1 else None,
                    progress_callback=progress_callback
                )
            else:  # PULL
                result = self.adb_wrapper.pull(
                    self.job.remote_path,
                    self.job.local_path,
                    serial=self.job.device_serial,
                    preserve_timestamp=self.args[0] if len(self.args) > 0 else False,
                    compression=self.args[1] if len(self.args) > 1 else None,
                    progress_callback=progress_callback
                )
            
            if result.success:
                self.transfer_completed.emit(True, "Transfer completed successfully")
            else:
                self.transfer_completed.emit(False, result.stderr)
                
        except Exception as e:
            self.transfer_completed.emit(False, str(e))
