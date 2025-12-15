"""Process manager for running subprocesses without blocking the UI."""
import subprocess
import threading
from enum import Enum
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal


class ProcessState(Enum):
    """Enumeration of process states."""

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"  # Not all processes support pause
    ERROR = "error"


class ManagedProcess(QObject):
    """A managed subprocess with signals for state changes and output."""

    # Signals
    output_received = pyqtSignal(str)  # stdout/stderr line
    state_changed = pyqtSignal(ProcessState)
    finished = pyqtSignal(int)  # return code

    def __init__(self, name: str, parent: Optional[QObject] = None):
        """Initialize a managed process.

        Args:
            name: Human-readable name for this process.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.name = name
        self._process: Optional[subprocess.Popen] = None
        self._state = ProcessState.STOPPED
        self._output_thread: Optional[threading.Thread] = None
        self._stop_requested = False

    @property
    def state(self) -> ProcessState:
        """Get the current process state."""
        return self._state

    @state.setter
    def state(self, value: ProcessState) -> None:
        """Set the process state and emit signal."""
        if self._state != value:
            self._state = value
            self.state_changed.emit(value)

    def start(
        self,
        command: list[str],
        cwd: Optional[str] = None,
        env: Optional[dict] = None,
    ) -> bool:
        """Start the subprocess.

        Args:
            command: Command and arguments to run.
            cwd: Working directory for the process.
            env: Environment variables for the process.

        Returns:
            True if started successfully, False otherwise.
        """
        if self._process is not None and self._process.poll() is None:
            self.output_received.emit(f"[{self.name}] Process already running")
            return False

        try:
            self._stop_requested = False
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=cwd,
                env=env,
                text=True,
                bufsize=1,
            )
            self.state = ProcessState.RUNNING
            self.output_received.emit(
                f"[{self.name}] Started: {' '.join(command)}"
            )

            # Start output reader thread
            self._output_thread = threading.Thread(
                target=self._read_output, daemon=True
            )
            self._output_thread.start()

            return True
        except Exception as e:
            self.state = ProcessState.ERROR
            self.output_received.emit(f"[{self.name}] Error starting: {e}")
            return False

    def stop(self) -> None:
        """Stop the subprocess."""
        self._stop_requested = True
        if self._process is not None and self._process.poll() is None:
            self.output_received.emit(f"[{self.name}] Stopping...")
            try:
                self._process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            except Exception as e:
                self.output_received.emit(f"[{self.name}] Error stopping: {e}")
            finally:
                self.state = ProcessState.STOPPED
                self.output_received.emit(f"[{self.name}] Stopped")

    def is_running(self) -> bool:
        """Check if the process is currently running."""
        return (
            self._process is not None
            and self._process.poll() is None
        )

    def _read_output(self) -> None:
        """Read output from the process (runs in a separate thread)."""
        if self._process is None or self._process.stdout is None:
            return

        try:
            for line in iter(self._process.stdout.readline, ""):
                if self._stop_requested:
                    break
                if line:
                    self.output_received.emit(line.rstrip("\n"))

            # Process finished
            return_code = self._process.wait()
            if not self._stop_requested:
                self.state = ProcessState.STOPPED
                self.finished.emit(return_code)
                self.output_received.emit(
                    f"[{self.name}] Finished with code {return_code}"
                )
        except Exception as e:
            self.state = ProcessState.ERROR
            self.output_received.emit(f"[{self.name}] Output error: {e}")


class ProcessManager(QObject):
    """Manages multiple subprocesses."""

    def __init__(self, parent: Optional[QObject] = None):
        """Initialize the process manager.

        Args:
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._processes: dict[str, ManagedProcess] = {}

    def create_process(self, name: str) -> ManagedProcess:
        """Create or get a managed process.

        Args:
            name: Unique name for the process.

        Returns:
            The ManagedProcess instance.
        """
        if name not in self._processes:
            self._processes[name] = ManagedProcess(name, self)
        return self._processes[name]

    def get_process(self, name: str) -> Optional[ManagedProcess]:
        """Get a managed process by name.

        Args:
            name: Name of the process.

        Returns:
            The ManagedProcess instance or None.
        """
        return self._processes.get(name)

    def stop_all(self) -> None:
        """Stop all running processes."""
        for process in self._processes.values():
            if process.is_running():
                process.stop()

    def get_running_processes(self) -> list[str]:
        """Get names of all running processes.

        Returns:
            List of process names that are currently running.
        """
        return [
            name
            for name, process in self._processes.items()
            if process.is_running()
        ]
