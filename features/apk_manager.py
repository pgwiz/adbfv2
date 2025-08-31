"""
APK installation and management.
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from PyQt6.QtCore import QObject, QThread, pyqtSignal
from dataclasses import dataclass
from enum import Enum

from adb_tools.adb import ADBWrapper


class InstallStatus(Enum):
    """APK installation status."""
    PENDING = "pending"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class APKInfo:
    """Information about an APK file."""
    file_path: Path
    package_name: Optional[str] = None
    version_name: Optional[str] = None
    version_code: Optional[int] = None
    app_name: Optional[str] = None
    size: Optional[int] = None
    permissions: Optional[List[str]] = None


@dataclass
class InstallJob:
    """APK installation job."""
    id: str
    apk_info: APKInfo
    device_serial: str
    status: InstallStatus = InstallStatus.PENDING
    progress: int = 0
    error_message: Optional[str] = None
    options: Dict[str, Any] = None


class APKManager(QObject):
    """Manages APK installation and app management."""
    
    install_started = pyqtSignal(str)  # job_id
    install_progress = pyqtSignal(str, int)  # job_id, progress_percent
    install_completed = pyqtSignal(str, bool, str)  # job_id, success, message
    
    def __init__(self, adb_wrapper: ADBWrapper):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.adb_wrapper = adb_wrapper
        self.install_jobs: List[InstallJob] = []
    
    def analyze_apk(self, apk_path: Union[str, Path]) -> APKInfo:
        """Analyze APK file and extract information."""
        apk_path = Path(apk_path)
        
        apk_info = APKInfo(
            file_path=apk_path,
            size=apk_path.stat().st_size if apk_path.exists() else None
        )
        
        # TODO: Use aapt or python-adb to extract APK metadata
        # For now, just return basic info
        apk_info.package_name = apk_path.stem  # Placeholder
        
        return apk_info
    
    def install_apk(
        self,
        apk_path: Union[str, Path],
        device_serial: str,
        replace: bool = False,
        test: bool = False,
        downgrade: bool = False,
        grant_permissions: bool = False,
        streaming: Optional[bool] = None
    ) -> str:
        """
        Install APK to device.
        
        Returns:
            Installation job ID
        """
        job_id = f"install_{len(self.install_jobs)}"
        apk_info = self.analyze_apk(apk_path)
        
        job = InstallJob(
            id=job_id,
            apk_info=apk_info,
            device_serial=device_serial,
            options={
                'replace': replace,
                'test': test,
                'downgrade': downgrade,
                'grant_permissions': grant_permissions,
                'streaming': streaming
            }
        )
        
        self.install_jobs.append(job)
        
        # Start installation in background
        thread = APKInstallThread(self.adb_wrapper, job)
        thread.progress_updated.connect(lambda progress: self.install_progress.emit(job_id, progress))
        thread.install_completed.connect(lambda success, message: self._on_install_completed(job_id, success, message))
        thread.start()
        
        self.install_started.emit(job_id)
        return job_id
    
    def install_multiple_apks(
        self,
        apk_paths: List[Union[str, Path]],
        device_serial: str,
        **options
    ) -> str:
        """Install multiple APKs as a single operation."""
        job_id = f"install_multi_{len(self.install_jobs)}"
        
        # Analyze all APKs
        apk_infos = [self.analyze_apk(path) for path in apk_paths]
        
        # Create combined job
        job = InstallJob(
            id=job_id,
            apk_info=apk_infos[0],  # Primary APK
            device_serial=device_serial,
            options=options
        )
        job.options['multiple_apks'] = apk_paths
        
        self.install_jobs.append(job)
        
        # Start installation
        thread = APKInstallThread(self.adb_wrapper, job)
        thread.progress_updated.connect(lambda progress: self.install_progress.emit(job_id, progress))
        thread.install_completed.connect(lambda success, message: self._on_install_completed(job_id, success, message))
        thread.start()
        
        self.install_started.emit(job_id)
        return job_id
    
    def uninstall_package(self, package_name: str, device_serial: str, keep_data: bool = False) -> bool:
        """Uninstall package from device."""
        try:
            result = self.adb_wrapper.uninstall(package_name, device_serial, keep_data)
            return result.success
        except Exception as e:
            self.logger.error(f"Uninstall failed: {e}")
            return False
    
    def get_installed_packages(self, device_serial: str) -> List[str]:
        """Get list of installed packages on device."""
        try:
            result = self.adb_wrapper.shell("pm list packages", serial=device_serial)
            if result.success:
                packages = []
                for line in result.stdout.split('\n'):
                    if line.startswith('package:'):
                        package_name = line.replace('package:', '').strip()
                        packages.append(package_name)
                return packages
        except Exception as e:
            self.logger.error(f"Failed to get packages: {e}")
        
        return []
    
    def _on_install_completed(self, job_id: str, success: bool, message: str):
        """Handle installation completion."""
        for job in self.install_jobs:
            if job.id == job_id:
                job.status = InstallStatus.COMPLETED if success else InstallStatus.FAILED
                job.error_message = None if success else message
                break
        
        self.install_completed.emit(job_id, success, message)
    
    def get_job_status(self, job_id: str) -> Optional[InstallJob]:
        """Get status of installation job."""
        for job in self.install_jobs:
            if job.id == job_id:
                return job
        return None


class APKInstallThread(QThread):
    """Background thread for APK installation."""
    
    progress_updated = pyqtSignal(int)  # progress_percent
    install_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, adb_wrapper: ADBWrapper, job: InstallJob):
        super().__init__()
        self.adb_wrapper = adb_wrapper
        self.job = job
    
    def run(self):
        """Execute APK installation."""
        try:
            def progress_callback(line: str):
                # Parse installation progress
                if 'Streaming:' in line or 'Installing:' in line:
                    # Extract progress if available
                    self.progress_updated.emit(50)  # Rough progress
            
            options = self.job.options or {}
            
            if 'multiple_apks' in options:
                # Multiple APK installation
                result = self.adb_wrapper.install_multiple(
                    options['multiple_apks'],
                    serial=self.job.device_serial,
                    replace=options.get('replace', False),
                    test=options.get('test', False),
                    downgrade=options.get('downgrade', False),
                    grant_permissions=options.get('grant_permissions', False),
                    progress_callback=progress_callback
                )
            else:
                # Single APK installation
                result = self.adb_wrapper.install(
                    self.job.apk_info.file_path,
                    serial=self.job.device_serial,
                    replace=options.get('replace', False),
                    test=options.get('test', False),
                    downgrade=options.get('downgrade', False),
                    grant_permissions=options.get('grant_permissions', False),
                    streaming=options.get('streaming'),
                    progress_callback=progress_callback
                )
            
            self.progress_updated.emit(100)
            
            if result.success:
                self.install_completed.emit(True, "Installation completed successfully")
            else:
                error_msg = self._parse_install_error(result.stderr)
                self.install_completed.emit(False, error_msg)
                
        except Exception as e:
            self.install_completed.emit(False, str(e))
    
    def _parse_install_error(self, stderr: str) -> str:
        """Parse installation error and provide user-friendly message."""
        if "INSTALL_FAILED_ALREADY_EXISTS" in stderr:
            return "App already installed. Enable 'Replace existing' to update."
        elif "INSTALL_FAILED_INSUFFICIENT_STORAGE" in stderr:
            return "Insufficient storage space on device."
        elif "INSTALL_FAILED_INVALID_APK" in stderr:
            return "Invalid APK file or corrupted package."
        elif "INSTALL_FAILED_VERSION_DOWNGRADE" in stderr:
            return "Cannot downgrade app version. Enable 'Allow downgrade' if needed."
        elif "INSTALL_FAILED_PERMISSION_MODEL" in stderr:
            return "Permission model mismatch. Try enabling 'Grant permissions'."
        else:
            return stderr.strip() or "Installation failed for unknown reason"
