"""
Process execution utilities for ADB and Fastboot commands.
"""

import subprocess
import logging
import threading
import time
from typing import Optional, List, Tuple, Callable, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProcessResult:
    """Result of a process execution."""
    returncode: int
    stdout: str
    stderr: str
    command: List[str]
    execution_time: float
    
    @property
    def success(self) -> bool:
        """Check if process executed successfully."""
        return self.returncode == 0
    
    @property
    def output(self) -> str:
        """Get combined output (stdout + stderr)."""
        return f"{self.stdout}\n{self.stderr}".strip()


class ProcessRunner:
    """Utility class for running ADB/Fastboot processes with timeout and cancellation."""
    
    def __init__(self, timeout: int = 30):
        self.logger = logging.getLogger(__name__)
        self.timeout = timeout
        self._active_processes: List[subprocess.Popen] = []
        self._lock = threading.Lock()
    
    def run(
        self,
        command: List[str],
        timeout: Optional[int] = None,
        cwd: Optional[Path] = None,
        env: Optional[dict] = None,
        input_data: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> ProcessResult:
        """
        Run a command and return the result.
        
        Args:
            command: Command and arguments to execute
            timeout: Timeout in seconds (uses instance default if None)
            cwd: Working directory
            env: Environment variables
            input_data: Data to send to stdin
            progress_callback: Callback for real-time output
        
        Returns:
            ProcessResult with execution details
        """
        if timeout is None:
            timeout = self.timeout
        
        start_time = time.time()
        
        self.logger.debug(f"Executing: {' '.join(command)}")
        
        try:
            # Start process
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE if input_data else None,
                text=True,
                cwd=cwd,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            # Track active process
            with self._lock:
                self._active_processes.append(process)
            
            try:
                if progress_callback:
                    # Real-time output monitoring
                    stdout_lines = []
                    stderr_lines = []
                    
                    def read_output(pipe, lines, is_stderr=False):
                        for line in iter(pipe.readline, ''):
                            if line:
                                lines.append(line.rstrip())
                                if progress_callback:
                                    progress_callback(line.rstrip())
                    
                    # Start output reading threads
                    stdout_thread = threading.Thread(
                        target=read_output,
                        args=(process.stdout, stdout_lines)
                    )
                    stderr_thread = threading.Thread(
                        target=read_output,
                        args=(process.stderr, stderr_lines, True)
                    )
                    
                    stdout_thread.start()
                    stderr_thread.start()
                    
                    # Wait for process completion
                    process.wait(timeout=timeout)
                    
                    # Wait for output threads
                    stdout_thread.join(timeout=1)
                    stderr_thread.join(timeout=1)
                    
                    stdout = '\n'.join(stdout_lines)
                    stderr = '\n'.join(stderr_lines)
                else:
                    # Simple execution
                    stdout, stderr = process.communicate(
                        input=input_data,
                        timeout=timeout
                    )
                
                execution_time = time.time() - start_time
                
                result = ProcessResult(
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    command=command,
                    execution_time=execution_time
                )
                
                if result.success:
                    self.logger.debug(f"Command completed successfully in {execution_time:.2f}s")
                else:
                    self.logger.warning(f"Command failed with code {result.returncode}: {stderr}")
                
                return result
                
            finally:
                # Remove from active processes
                with self._lock:
                    if process in self._active_processes:
                        self._active_processes.remove(process)
        
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timed out after {timeout}s")
            process.kill()
            process.wait()
            
            return ProcessResult(
                returncode=-1,
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                command=command,
                execution_time=time.time() - start_time
            )
        
        except Exception as e:
            self.logger.error(f"Process execution failed: {e}")
            
            return ProcessResult(
                returncode=-2,
                stdout="",
                stderr=f"Process execution failed: {str(e)}",
                command=command,
                execution_time=time.time() - start_time
            )
    
    def cancel_all(self) -> None:
        """Cancel all active processes."""
        with self._lock:
            for process in self._active_processes[:]:
                try:
                    process.terminate()
                    # Give process time to terminate gracefully
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                except Exception as e:
                    self.logger.error(f"Failed to cancel process: {e}")
            
            self._active_processes.clear()
        
        self.logger.info("All active processes cancelled")
    
    def get_active_count(self) -> int:
        """Get number of active processes."""
        with self._lock:
            return len(self._active_processes)
